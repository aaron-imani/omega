"""
MAD: Multi-Agent Debate with Large Language Models
Copyright (C) 2023  The MAD Team

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import argparse
import json
import os
import sys
from time import time

sys.path.extend(["..", "../OMG_based"])
from datetime import datetime

from tqdm import tqdm

# from langcodes import Language
from utils.agent import Agent

from evaluation.evaluate_cm import evaluate_machine_generated_text
from MAD_based.prompts import basic
from OMG_based.Agent_tools import *
from OMG_based.utils import format_output

issue_collecting_tool = IssueCollectingTool()
pull_request_collecting_tool = PullRequestCollectingTool()
important_files_tool = ImportantFileTool()

# tools = [
#     git_diff_tool,
#     commit_type_classifier_tool,
#     code_summarization_tool,
#     code_understanding_tool,
#     important_files_tool,
#     issue_collecting_tool,
#     pull_request_collecting_tool,
# ]

# NAME_LIST=[
#     "Affirmative side",
#     "Negative side",
#     "Moderator",
# ]

NAME_LIST = [
    "Debater 1",
    "Debater 2",
    # "Debater 3",
    "Moderator",
]


class DebatePlayer(Agent):
    def __init__(self, name: str, temperature: float, verbose: bool) -> None:
        """Create a player in the debate

        Args:
            model_name(str): model name
            name (str): name of this player
            temperature (float): higher values make the output more random, while lower values make it more focused and deterministic
            openai_api_key (str): As the parameter name suggests
            sleep_time (float): sleep because of rate limits
        """
        super(DebatePlayer, self).__init__(name, temperature, verbose)


class Debate:
    def __init__(
        self,
        temperature: float = 0,
        num_players: int = 3,
        save_file_dir: str = None,
        openai_api_key: str = None,
        max_round: int = 5,
        verbose: bool = False,
    ) -> None:
        """Create a debate

        Args:
            model_name (str): openai model name
            temperature (float): higher values make the output more random, while lower values make it more focused and deterministic
            num_players (int): num of players
            save_file_dir (str): dir path to json file
            openai_api_key (str): As the parameter name suggests
            max_round (int): maximum Rounds of Debate
            sleep_time (float): sleep because of rate limits
        """
        self.verbose = verbose
        self.temperature = temperature
        self.num_players = num_players
        self.save_file_dir = save_file_dir
        self.openai_api_key = openai_api_key
        self.max_round = max_round
        self.players = []

    def init_debate(self, prompts, diff: str, contexts: dict):
        assert "judge" in contexts, "Judge context is missing"
        assert len(contexts) == self.num_players, "Context size mismatch players count."

        self.cm = {"type": "", "subject": "", "body": ""}

        # init save file
        now = datetime.now()
        current_time = now.strftime("%Y-%m-%d_%H:%M:%S")
        self.save_file = {
            "start_time": current_time,
            "end_time": "",
            "temperature": self.temperature,
            "num_players": self.num_players,
            "success": False,
            "base_commit_message": "",
            "debate_commit_message": "",
            "Reason": "",
            "Supported Side": "",
            "players": {},
        }
        self.save_file.update(prompts)
        self.init_prompt(contexts)

        if self.save_file["base_commit_message"] == "":
            self.create_base(contexts["judge"])

        # creat&init agents
        self.create_agents()
        self.init_agents(contexts)

    def init_prompt(self, contexts):
        self.player_system_prompt = {
            player: basic.player_system_prompt.format(
                evaluation_criteria=basic.evaluation_criteria,
                context=contexts[player],
                debater_name=player,
            )
            for player in NAME_LIST[:-1]
        }
        self.moderator_system_prompt = basic.moderator_system_prompt.format(
            num_debators=len(NAME_LIST), context=contexts["judge"]
        )
        self.judge_prompt_last2 = basic.judge_prompt_2.format(context=contexts["judge"])

        # def prompt_replace(key):
        #     self.save_file[key] = self.save_file[key].replace("##diff##", self.save_file["diff"])\
        #     .replace("##base_commit_message##", self.save_file["base_commit_message"])\
        #     .replace("##evaluation_criteria##", self.save_file["evaluation_criteria"])
        # prompt_replace("base_prompt")
        # prompt_replace("player_meta_prompt")
        # prompt_replace("moderator_meta_prompt")
        # prompt_replace("judge_prompt_last2")

    def create_base(self, context):
        base_prompt = basic.base_prompt.format(context=context)
        # if self.verbose:
        #     print(f"\n===== Commit Message Generation Task =====\n\n{base_prompt}\n")

        agent = DebatePlayer(
            name="Baseline", temperature=self.temperature, verbose=self.verbose
        )
        agent.add_event(base_prompt)
        base_commit_message = agent.ask()
        agent.add_memory(base_commit_message)
        self.save_file["base_commit_message"] = base_commit_message
        # self.affirmative_prompt = prompts.affirmitive_prompt.format(
        #     base_cm=base_commit_message
        # )
        # self.save_file['affirmative_prompt'] = self.save_file['affirmative_prompt'].replace("##base_commit_message##", base_commit_message)
        self.save_file["players"][agent.name] = agent.memory_lst

    def create_agents(self):
        # creates players
        if not self.players:
            self.players = [
                DebatePlayer(
                    name=name, temperature=self.temperature, verbose=self.verbose
                )
                for name in NAME_LIST
            ]
            # self.affirmative = self.players[0]
            # self.negative = self.players[1]
            self.moderator = self.players[-1]
        else:
            for p in self.players:
                p.reset()

    def init_agents(self, contexts: dict):
        # start: set meta prompt
        for p in self.players[:-1]:
            p.set_meta_prompt(
                basic.player_system_prompt.format(
                    context=contexts[p.name], debater_name=p.name
                )
            )

        self.moderator.set_meta_prompt(self.moderator_system_prompt)
        # self.affirmative.set_meta_prompt(self.save_file['player_meta_prompt'])
        # self.negative.set_meta_prompt(self.save_file['player_meta_prompt'])
        # self.moderator.set_meta_prompt(self.save_file['moderator_meta_prompt'])

        # start: first round debate, state opinions
        if self.verbose:
            print(f"===== Debate Round-1 =====\n")

        prev_answers = []
        conversation = []
        base_cm = self.save_file["base_commit_message"]
        conversation.append("START OF CONVERSATION")
        debater_name = "Baseline"
        for i, p in enumerate(self.players[:-1]):
            if i % 2 == 0:
                prompt = basic.affirmitive_prompt.format(
                    base_cm=base_cm, debater_name=debater_name
                )
            else:
                prompt = basic.negative_prompt.format(
                    affirmitive_side_answer="\n".join(prev_answers),
                    debater_name=debater_name,
                )

            debater_name = p.name
            p.add_event(prompt)
            prev_answer = p.ask()
            p.add_memory(prev_answer)
            prev_answers.append(prev_answer)
            conversation.append(f'{p.name} arguing: "{prev_answer}"')
            base_cm = prev_answer

        self.last_message = conversation[-1]
        conversation.append("END OF CONVERSATION")
        conversation = "\n\n".join(conversation)
        moderator_prompt = basic.moderator_prompt.format(
            round_num="first", conversation=conversation
        )
        self.moderator.add_event(moderator_prompt)
        self.mod_ans = self.moderator.ask()
        self.moderator.add_memory(self.mod_ans)
        # self.mod_ans = json.loads(self.mod_ans)
        self.round = 1
        # self.affirmative.add_event(self.save_file['affirmative_prompt'])
        # self.aff_ans = self.affirmative.ask()
        # self.affirmative.add_memory(self.aff_ans)

        # self.negative.add_event(self.save_file['negative_prompt'].replace('##aff_ans##', self.aff_ans))
        # self.neg_ans = self.negative.ask()
        # self.negative.add_memory(self.neg_ans)

        # self.moderator.add_event(self.save_file['moderator_prompt'].replace('##aff_ans##', self.aff_ans).replace('##neg_ans##', self.neg_ans).replace('##round##', 'first'))
        # self.mod_ans = self.moderator.ask()
        # self.moderator.add_memory(self.mod_ans)
        # self.mod_ans = eval(self.mod_ans)

    def round_dct(self, num: int):
        dct = {
            1: "first",
            2: "second",
            3: "third",
            4: "fourth",
            5: "fifth",
            6: "sixth",
            7: "seventh",
            8: "eighth",
            9: "ninth",
            10: "tenth",
        }
        return dct[num]

    def save_file_to_json(self, id):
        now = datetime.now()
        current_time = now.strftime("%Y-%m-%d_%H:%M:%S")
        save_file_path = os.path.join(self.save_file_dir, f"{id}.json")

        self.save_file["end_time"] = current_time
        json_str = json.dumps(self.save_file, ensure_ascii=False, indent=4)
        with open(save_file_path, "w") as f:
            f.write(json_str)

    def broadcast(self, msg: str):
        """Broadcast a message to all players.
        Typical use is for the host to announce public information

        Args:
            msg (str): the message
        """
        for player in self.players:
            player.add_event(msg)

    def speak(self, speaker: str, msg: str):
        """The speaker broadcast a message to all other players.

        Args:
            speaker (str): name of the speaker
            msg (str): the message
        """
        if not msg.startswith(f"{speaker}: "):
            msg = f"{speaker}: {msg}"

        for player in self.players:
            if player.name != speaker:
                player.add_event(msg)

    def ask_and_speak(self, player: DebatePlayer):
        ans = player.ask()
        player.add_memory(ans)
        self.speak(player.name, ans)

    def parse_moderator_response(self):
        prev_round_comments = []
        mod_response = self.mod_ans
        json_found = re.search(r"({(.*)})", mod_response, re.DOTALL)
        if json_found:
            json_str = re.sub(r"\s+", r" ", json_found.group(1))
            try:
                mod_response = json.loads(json_str)
            except json.JSONDecodeError:
                self.moderator.add_event(
                    f"You did not provide a valid decodable JSON blob. Please correct your answer and send it again."
                )
                self.mod_ans = self.moderator.ask()
                self.moderator.add_memory(self.mod_ans)
                return self.parse_moderator_response()
        else:
            self.moderator.add_event(
                f"You did not provide a correct JSON blob. Please correct your answer and send it again."
            )
            self.mod_ans = self.moderator.ask()
            self.moderator.add_memory(self.mod_ans)
            return self.parse_moderator_response()

        reflection = mod_response["reflection"]

        for part in mod_response["part_decisions"]:
            part_type = list(part.keys())[0]
            part = part[part_type]

            if part["concluded"] == "No":
                if "reason" not in part:
                    self.moderator.add_event(
                        f'You forgot to provide the reason for the part "{part_type}". Please correct your answer and send it again.'
                    )
                    self.mod_ans = self.moderator.ask()
                    self.moderator.add_memory(self.mod_ans)
                    return self.parse_moderator_response()
                else:
                    prev_round_comments.append(part["reason"])

            elif part["concluded"] == "Yes" and self.cm[part_type] == "":
                if "selected_debator_response" not in part:
                    self.moderator.add_event(
                        f'You forgot to provide the selected_debator_response for the part "{part_type}". Please correct your answer and send it again.'
                    )
                    self.mod_ans = self.moderator.ask()
                    self.moderator.add_memory(self.mod_ans)
                    return self.parse_moderator_response()
                else:
                    self.cm[part_type] = part["selected_debator_response"]

        return reflection
        # topics = []

        # for part in self.mod_ans:
        #     if self.mod_ans[part]["Concluded"] == "Yes" and self.cm[part] == "":
        #         if "Selected Debator Response" not in self.mod_ans[part]:
        #             self.moderator.add_event(
        #                 f'You forgot to provide the selected debator response for the part "{part}". Please correct your answer and send it again.'
        #             )
        #             self.mod_ans = self.moderator.ask()
        #             self.moderator.add_memory(self.mod_ans)
        #             self.mod_ans = json.loads(self.mod_ans)
        #             return self.parse_moderator_response()
        #         else:
        #             self.cm[part] = self.mod_ans[part]["Selected Debator Response"]

        #     elif self.mod_ans[part]["Concluded"] == "No":
        #         if "Reason" not in self.mod_ans[part]:
        #             self.moderator.add_event(
        #                 f'You forgot to provide the reason for the part "{part}". Please correct your answer and send it again.'
        #             )
        #             self.mod_ans = self.moderator.ask()
        #             self.moderator.add_memory(self.mod_ans)
        #             self.mod_ans = json.loads(self.mod_ans)
        #             return self.parse_moderator_response()
        #         else:
        #             prev_round_comments.append(self.mod_ans[part]["Reason"])
        #             topics.append(part)

        # return prev_round_comments, topics

    def run(self):
        for round in range(self.max_round - 1):

            # prev_round_comments, topics = self.validate_moderator_response()

            # if prev_round_comments:
            #     prev_round_comments.insert(
            #         0,
            #         "The previous round ended but it did not reach a conclusion. Here are the reasons:",
            #     )
            #     prev_round_comments.append(
            #         f'\nThe topic for this round of debate is centered only the following parts of the commit message: {", ".join(topics)}\n'
            #         "\n Do not discuss the parts that have already been concluded."
            #     )
            #     prev_round_comments = "\n".join(prev_round_comments)
            #     for p in self.players[:-1]:
            #         p.set_meta_prompt(prev_round_comments)
            # p.add_memory(
            #     "Sure, I will consider this in the next round when debating with other players."
            # )
            reflection = self.parse_moderator_response()
            if reflection:
                self.speak("Moderator", reflection)

            # if "selected\_commit\_message" in self.mod_ans:
            #     cm_key = "selected\_commit\_message"
            # elif "selected_commit_message" in self.mod_ans:
            #     cm_key = "selected_commit_message"
            if all(self.cm.values()):
                break
            # if self.mod_ans[cm_key] != "":
            #     break
            else:
                if self.verbose:
                    print(f"===== Debate Round-{round+2} =====\n")

                self.round += 1

                conversation = []
                for p in self.players[:-1]:
                    prompt = basic.debate_prompt.format(
                        opponent_answer=self.last_message
                    )
                    p.add_event(prompt)
                    last_message = p.ask()
                    p.add_memory(last_message)
                    self.last_message = f'{p.name} arguing: "{last_message}"'
                    conversation.append(self.last_message)

                conversation = "\n\n".join(conversation)
                moderator_prompt = basic.moderator_prompt.format(
                    round_num=self.round_dct(round + 2), conversation=conversation
                )
                self.moderator.add_event(moderator_prompt)
                self.mod_ans = self.moderator.ask()
                self.moderator.add_memory(self.mod_ans)
                # self.mod_ans = json.loads(self.mod_ans)

                # self.affirmative.add_event(self.save_file['debate_prompt'].replace('##oppo_ans##', self.neg_ans))
                # self.aff_ans = self.affirmative.ask()
                # self.affirmative.add_memory(self.aff_ans)

                # self.negative.add_event(self.save_file['debate_prompt'].replace('##oppo_ans##', self.aff_ans))
                # self.neg_ans = self.negative.ask()
                # self.negative.add_memory(self.neg_ans)

                # self.moderator.add_event(self.save_file['moderator_prompt'].replace('##aff_ans##', self.aff_ans).replace('##neg_ans##', self.neg_ans).replace('##round##', self.round_dct(round+2)))
                # self.mod_ans = self.moderator.ask()
                # self.moderator.add_memory(self.mod_ans)
                # self.mod_ans = eval(self.mod_ans)

        if all(self.cm.values()):
            # self.save_file.update(self.mod_ans)
            self.save_file["success"] = True
            self.total_tokens = sum([p.used_tokens for p in self.players])

        # ultimate deadly technique.
        else:
            judge_player = DebatePlayer(
                name="Judge", temperature=self.temperature, verbose=self.verbose
            )
            # aff_ans = self.affirmative.memory_lst[2]['content']
            # neg_ans = self.negative.memory_lst[2]['content']

            # judge_player.set_meta_prompt(self.save_file['moderator_meta_prompt'])
            judge_player.set_meta_prompt(self.players[-1].memory_lst[0]["content"])

            prompt = basic.judge_prompt_1.format(conversation=conversation)
            judge_player.add_event(prompt)
            ans = judge_player.ask()
            judge_player.add_memory(ans)

            judge_player.add_event(self.judge_prompt_last2)
            ans = judge_player.ask()
            judge_player.add_memory(ans)

            # extract answer candidates
            # judge_player.add_event(self.save_file['judge_prompt_last1'].replace('##aff_ans##', aff_ans).replace('##neg_ans##', neg_ans))
            # ans = judge_player.ask()
            # judge_player.add_memory(ans)

            # select one from the candidates
            # judge_player.add_event(self.save_file['judge_prompt_last2'])
            # ans = judge_player.ask()
            # judge_player.add_memory(ans)

            ans = eval(ans)
            if "debate_commit_message" in ans and ans["debate_commit_message"] != "":
                self.save_file["success"] = True
                # save file
            elif (
                "debate\_commit\_message" in ans
                and ans["debate\_commit\_message"] != ""
            ):
                self.save_file["success"] = True
                # save file

            self.save_file.update(ans)
            self.players.append(judge_player)

        for player in self.players:
            self.save_file["players"][player.name] = player.memory_lst


def parse_args():
    parser = argparse.ArgumentParser(
        "", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("input_file", type=str, help="Input file path")
    parser.add_argument("output_dir", type=str, help="Output file dir")
    parser.add_argument("-n", "--csv-name", type=str, help="CSV file name")

    parser.add_argument(
        "-m",
        "--model-name",
        type=str,
        default="codellama:13b-instruct",
        help="Model name",
    )
    parser.add_argument(
        "-t", "--temperature", type=float, default=0, help="Sampling temperature"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose mode")
    parser.add_argument("-r", "--random-row", action="store_true", help="Random mode")

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    current_script_path = os.path.abspath(__file__)

    config = json.load(open("utils/config4cm.json", "r"))

    save_file_dir = args.output_dir
    if not os.path.exists(save_file_dir):
        os.mkdir(save_file_dir)
    prompts_path = f"{save_file_dir}/config.json"

    if args.input_file.endswith(".txt"):
        input = open(args.input_file, "r").read()
        config["diff"] = input
        # config['evaluation_criteria'] = instructions

        # with open(prompts_path, 'w') as file:
        #     json.dump(config, file, ensure_ascii=False, indent=4)
        context = {name: basic.make_context(input) for name in NAME_LIST}
        context["judge"] = basic.make_context(input)

        debate = Debate(
            save_file_dir=save_file_dir, num_players=3, temperature=0, verbose=True
        )
        debate.init_debate(config, input, context)
        debate.run()
        debate.save_file_to_json("output")

    elif args.input_file.endswith("xlsx") or args.input_file.endswith("csv"):
        import pandas as pd
        from termcolor import colored

        # from OMG_based import cache_manager
        from tqdm.auto import tqdm

        if args.input_file.endswith("xlsx"):
            df = pd.read_excel(args.input_file)
        else:
            df = pd.read_csv(args.input_file)

        debate = Debate(
            save_file_dir=save_file_dir,
            num_players=3,
            temperature=0,
            verbose=args.verbose,
        )

        if args.random_row:
            row = df.sample(1).iloc[0]
            commit_url = f'https://github.com/{row["project"]}/commit/{row["commit"]}'
            diff = basic.git_diff.format(diff=git_diff_tool.invoke(commit_url))

            # config['diff'] = diff
            # config['evaluation_criteria'] = instructions

            # with open(prompts_path, 'w') as file:
            #     json.dump(config, file, ensure_ascii=False, indent=4)
            complete_context = basic.make_context(
                diff,
                changed_files_importance=important_files_tool.invoke(commit_url),
                associated_issues=issue_collecting_tool.invoke(commit_url),
                associated_pull_requests=pull_request_collecting_tool.invoke(
                    commit_url
                ),
                changed_method_summaries=code_summarization_tool.invoke(commit_url),
                changed_class_functionality_summary=code_understanding_tool.invoke(
                    commit_url
                ),
            )
            # context = {
            #     "Debater 1": prompts.make_context(
            #         diff,
            #         changed_files_importance=important_files_tool.invoke(
            #             commit_url
            #         ),
            #     ),
            #     "Debater 2": prompts.make_context(
            #         diff,
            #         associated_issues=issue_collecting_tool.invoke(commit_url),
            #         associated_pull_requests=pull_request_collecting_tool.invoke(
            #             commit_url
            #         ),
            #     ),
            #     "Debater 3": prompts.make_context(
            #         diff,
            #         changed_method_summaries=code_summarization_tool.invoke(commit_url),
            #         changed_class_functionality_summary=code_understanding_tool.invoke(
            #             commit_url
            #         ),
            #     ),
            #     "judge": complete_context,
            # }
            context = {
                "Debater 1": complete_context,
                "Debater 2": complete_context,
                # "Debater 3": complete_context,
                "judge": complete_context,
            }
            debate.init_debate(config, diff, context)
            debate.run()
            # cm = format_output(debate.save_file["selected_commit_message"]).strip()
            cm = f'{debate.cm["type"]}: {debate.cm["subject"]}\n{debate.cm["body"]}'
            print("Commit URL:", colored(commit_url, "light_blue"))
            print("Commit Message:", colored(cm, "light_green"), sep="\n")
        else:
            save_file_path = os.path.join(save_file_dir, args.csv_name)
            if os.path.exists(save_file_path):
                df = pd.read_csv(save_file_path)
                df = df.fillna("")
            else:
                df["MAD"] = ""

            if "CMG" in df.columns:
                df = df.rename(columns={"CMG": "OMG"})

            try:
                for i, row in tqdm(
                    df.iterrows(), desc="Generating commit messages", total=len(df)
                ):
                    if row["MAD"] != "":
                        continue

                    commit_url = (
                        f'https://github.com/{row["project"]}/commit/{row["commit"]}'
                    )
                    diff = basic.git_diff.format(diff=git_diff_tool.invoke(commit_url))
                    # config['diff'] = diff
                    # config['evaluation_criteria'] = instructions

                    # with open(prompts_path, 'w') as file:
                    #     json.dump(config, file, ensure_ascii=False, indent=4)
                    complete_context = basic.make_context(
                        diff,
                        changed_files_importance=important_files_tool.invoke(
                            commit_url
                        ),
                        associated_issues=issue_collecting_tool.invoke(commit_url),
                        associated_pull_requests=pull_request_collecting_tool.invoke(
                            commit_url
                        ),
                        changed_method_summaries=code_summarization_tool.invoke(
                            commit_url
                        ),
                        changed_class_functionality_summary=code_understanding_tool.invoke(
                            commit_url
                        ),
                    )
                    # context = {
                    #     "Debater 1": prompts.make_context(
                    #         diff,
                    #         changed_files_importance=important_files_tool.invoke(
                    #             commit_url
                    #         ),
                    #     ),
                    #     "Debater 2": prompts.make_context(
                    #         diff,
                    #         associated_issues=issue_collecting_tool.invoke(commit_url),
                    #         associated_pull_requests=pull_request_collecting_tool.invoke(
                    #             commit_url
                    #         ),
                    #     ),
                    #     "Debater 3": prompts.make_context(
                    #         diff,
                    #         changed_method_summaries=code_summarization_tool.invoke(commit_url),
                    #         changed_class_functionality_summary=code_understanding_tool.invoke(
                    #             commit_url
                    #         ),
                    #     ),
                    #     "judge": complete_context,
                    # }
                    context = {
                        "Debater 1": complete_context,
                        "Debater 2": complete_context,
                        # "Debater 3": complete_context,
                        "judge": complete_context,
                    }
                    t1 = time()
                    debate.init_debate(config, diff, context)
                    debate.run()
                    t2 = time()
                    # cm = format_output(
                    #     debate.save_file["selected_commit_message"]
                    # ).strip()
                    cm_type = debate.cm["type"].strip("\"'")
                    cm_subject = debate.cm["subject"].strip("\"'")
                    cm_body = debate.cm["body"].strip("\"'")
                    cm = f"{cm_type}: {cm_subject}\n{cm_body}"

                    df.at[i, "MAD"] = cm
                    df.at[i, "MAD_duration"] = t2 - t1
                    df.at[i, "Rounds"] = debate.round
                    df.at[i, "Total Tokens"] = debate.total_tokens
                    print("Time taken:", t2 - t1)
                    print("Commit URL:", commit_url)
                    print("Commit Message:", colored(cm, "yellow"), sep="\n")
                    print(colored("--" * 40, "light_green"))
            except KeyboardInterrupt:
                print("Stopping generation...")
            except Exception as e:
                print(e)
                print("Stopping due to exception...")

            df = df[
                [
                    "project",
                    "commit",
                    "OMG",
                    "AMG",
                    "MAD",
                    "MAD_duration",
                    "Rounds",
                    "Total Tokens",
                ]
            ]
            df.to_csv(save_file_path, index=False)
            df = df[df["MAD"] != ""]
            print("--" * 15, "MAD VS OMG", "--" * 15)
            evaluate_machine_generated_text(df["OMG"], df["MAD"], print_results=True)

    # for id, input in enumerate(tqdm(inputs)):
    # files = os.listdir(save_file_dir)
    # if f"{id}.json" in files:
    #     continue
