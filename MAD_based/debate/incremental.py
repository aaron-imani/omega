import json
import os
from datetime import datetime

from debate_player import DebatePlayer

from MAD_based.prompts import incremental as prompts


class Debate:
    def __init__(
        self,
        name_list: list,
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
        self.name_list = name_list

    def init_debate(
        self, prompts, contexts: dict, cm_part: str, cm_type=None, cm_subject=None
    ):
        assert "judge" in contexts, "Judge context is missing"
        assert len(contexts) == self.num_players, "Context size mismatch players count."
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
        self.partial_cm = prompts.get_partial_cm(cm_type, cm_subject)
        self.cm_part = cm_part

        self.init_prompt(contexts)

        if self.save_file["base_commit_message"] == "":
            self.create_base(contexts["judge"])

        # creat&init agents
        self.create_agents()
        self.init_agents(contexts)

    def init_prompt(self, contexts):
        cm_part, partial_cm = self.cm_part, self.partial_cm

        self.player_system_prompt = {
            player: prompts.player_system_prompt.format(
                evaluation_criteria=prompts.evaluation_criteria,
                context=contexts[player],
                cm_part=cm_part,
                partial_cm=partial_cm,
            )
            for player in self.name_list[:-1]
        }
        self.moderator_system_prompt = prompts.moderator_system_prompt.format(
            num_debators=len(self.name_list),
            context=contexts["judge"],
            cm_part=cm_part,
            partial_cm=partial_cm,
        )
        self.judge_prompt_last2 = prompts.judge_prompt_2.format(
            context=contexts["judge"], cm_part=cm_part, partial_cm=partial_cm
        )

        # def prompt_replace(key):
        #     self.save_file[key] = self.save_file[key].replace("##diff##", self.save_file["diff"])\
        #     .replace("##base_commit_message##", self.save_file["base_commit_message"])\
        #     .replace("##evaluation_criteria##", self.save_file["evaluation_criteria"])
        # prompt_replace("base_prompt")
        # prompt_replace("player_meta_prompt")
        # prompt_replace("moderator_meta_prompt")
        # prompt_replace("judge_prompt_last2")

    def create_base(self, context):
        cm_part, partial_cm = self.cm_part, self.partial_cm

        base_prompt = prompts.base_prompt.format(
            context=context, cm_part=cm_part, partial_cm=partial_cm
        )

        # if self.verbose:
        #     print(
        #         f"\n===== Incremental Commit Message Generation Task =====\n\n{base_prompt}\n"
        #     )

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
                for name in self.name_list
            ]
            # self.affirmative = self.players[0]
            # self.negative = self.players[1]
            self.moderator = self.players[-1]
        else:
            for p in self.players:
                p.reset()

    def init_agents(self, contexts: dict):
        cm_part, partial_cm = self.cm_part, self.partial_cm

        # start: set meta prompt
        for p in self.players[:-1]:
            p.set_meta_prompt(
                prompts.player_system_prompt.format(
                    context=contexts[p.name], cm_part=cm_part, partial_cm=partial_cm
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
        debater_name = "Baseline"
        for i, p in enumerate(self.players[:-1]):
            if i % 2 == 0:
                prompt = prompts.affirmitive_prompt.format(
                    base_cm=base_cm, debater_name=debater_name, cm_part=cm_part
                )
            else:
                prompt = prompts.negative_prompt.format(
                    affirmitive_side_answer="\n".join(prev_answers), cm_part=cm_part
                )
                debater_name = p.name

            p.add_event(prompt)
            prev_answer = p.ask()
            p.add_memory(prev_answer)
            prev_answers.append(prev_answer)
            conversation.append(f'{p.name} arguing: "{prev_answer}"')
            base_cm = prev_answer

        self.last_message = conversation[-1]
        conversation = "\n\n".join(conversation)
        moderator_prompt = prompts.moderator_prompt.format(
            round_num="first", conversation=conversation, cm_part=cm_part
        )
        self.moderator.add_event(moderator_prompt)
        self.mod_ans = self.moderator.ask()
        self.moderator.add_memory(self.mod_ans)
        self.mod_ans = eval(self.mod_ans)
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
        # print(msg)
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
        # print(msg)
        for player in self.players:
            if player.name != speaker:
                player.add_event(msg)

    def ask_and_speak(self, player: DebatePlayer):
        ans = player.ask()
        player.add_memory(ans)
        self.speak(player.name, ans)

    def run(self):
        for round in range(self.max_round - 1):
            # if "selected\_commit\_message" in self.mod_ans:
            #     cm_key = "selected\_commit\_message"
            # elif "selected_commit_message" in self.mod_ans:
            #     cm_key = "selected_commit_message"
            cm_key = f"selected_{self.cm_part}"
            if self.mod_ans[cm_key] != "":
                break
            else:
                if self.verbose:
                    print(f"===== Debate Round-{round+2} =====\n")

                conversation = []
                for p in self.players[:-1]:
                    prompt = prompts.debate_prompt.format(
                        opponent_answer=self.last_message, cm_part=self.cm_part
                    )
                    p.add_event(prompt)
                    self.last_message = p.ask()
                    p.add_memory(self.last_message)
                    conversation.append(f'{p.name} arguing: "{self.last_message}"')

                conversation = "\n\n".join(conversation)
                moderator_prompt = prompts.moderator_prompt.format(
                    round_num="first", conversation=conversation, cm_part=self.cm_part
                )
                self.moderator.add_event(moderator_prompt)
                self.mod_ans = self.moderator.ask()
                self.moderator.add_memory(self.mod_ans)
                self.mod_ans = eval(self.mod_ans)
                self.round += 1
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

        if self.mod_ans[cm_key] != "":
            self.save_file.update(self.mod_ans)
            self.save_file["success"] = True
            self.total_tokens = sum([p.used_tokens for p in self.players])

        # ultimate deadly technique.
        else:
            judge_player = DebatePlayer(
                model_name=self.model_name, name="Judge", temperature=self.temperature
            )
            # aff_ans = self.affirmative.memory_lst[2]['content']
            # neg_ans = self.negative.memory_lst[2]['content']

            # judge_player.set_meta_prompt(self.save_file['moderator_meta_prompt'])
            judge_player.set_meta_prompt(self.players[-1].memory_lst[0]["content"])

            prompt = prompts.judge_prompt_1.format(conversation=conversation)
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
            debate_answer_key = f"debate_{self.cm_part}"
            if ans.get(debate_answer_key, "") != "":
                self.save_file["success"] = True

            self.save_file.update(ans)
            self.players.append(judge_player)

        for player in self.players:
            self.save_file["players"][player.name] = player.memory_lst
