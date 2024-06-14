import json
import re

import json_repair
from langchain.memory import ChatMessageHistory

import MAD_based.prompts.what_why_generate as prompts
from MAD_based.debate.player import Player
from MAD_based.utils.information_card import InformationCard, Trustworthiness

# from OMG_based.get_changed_java_files import get_changed_java_files
# from OMG_based.utils import format_output

selected_answer_regex = re.compile(
    r"## Selected Answer For Round \d+\s*(.+)", re.DOTALL | re.IGNORECASE
)


class Debate:
    def __init__(
        self,
        num_players: int,
        use_information_card=False,
        small_players=False,
        use_role_reversal=False,
        use_persona=False,
    ):
        self.use_role_reversal = use_role_reversal
        self.use_persona = use_persona
        self.store = {}
        players = []
        player_system_prompt = prompts.get_players_initial_system_prompt(
            use_information_card,
            use_persona=use_persona,
            role_reversal=use_role_reversal,
        )

        if small_players:
            player_model_kwargs = {
                "base_url": "http://128.195.42.241:49999",
                "model_name": "codeqwen:v1.5-chat",
                "server_type": "ollama",
            }
        else:
            player_model_kwargs = None

        for i in range(num_players):
            player_num = i + 1

            player_prompt = player_system_prompt.format(
                player_name=f"Participant {player_num}", num_debators=num_players - 1
            )
            player = Player(
                player_prompt,
                f"Participant {player_num}",
                self.get_by_session_id,
                model_kwargs=player_model_kwargs,
                # temperature=1 - i % 2,
            )
            players.append(player)

        self.players = players
        self.moderator = Player(
            prompts.moderator_system_prompt, "Moderator", self.get_by_session_id
        )
        self.use_information_card = use_information_card

    def get_by_session_id(self, session_id: str) -> ChatMessageHistory:
        if session_id not in self.store:
            self.store[session_id] = ChatMessageHistory()
        return self.store[session_id]

    def prepare_context(self, commit_context):
        use_information_card = self.use_information_card
        diff = commit_context["git_diff"]
        if use_information_card:
            diff_card = InformationCard(
                "Git Diff",
                diff,
                learning_instructions="By following the reading instructions, you will learn what files have been modified and what lines have been added and/or removed.",
                usage_instructions="You must use this information when writing a descriptive report of changes in the commit. This report will then be useful when writing a commit message for the changes.",
                reading_instructions=prompts.diff_reading_instruction,
                trustworthiness=Trustworthiness.HIGH,
                heading_level=3,
            )
            diff = diff_card

        changed_method_summaries = commit_context["changed_method_summaries"]
        if use_information_card:
            changed_method_summaries_card = InformationCard(
                "Changed Method(s) Summaries",
                changed_method_summaries,
                learning_instructions="From the changed method(s) summaries, you will learn if the commit has affected the functionality of any method(s) in the codebase and if so, how.",
                usage_instructions="Use this information to understand any changes made to the methods in the codebase.",
                reading_instructions="The reading instructions is included in the content if this card.",
                trustworthiness=Trustworthiness.MEDIUM,
                heading_level=3,
            )
            changed_method_summaries = changed_method_summaries_card

        changed_class_functionality_summary = commit_context[
            "changed_class_functionality_summary"
        ]
        if use_information_card:
            changed_class_functionality_summary_card = InformationCard(
                "Changed Class(es) Functionality Summary",
                changed_class_functionality_summary,
                learning_instructions="By correctly reading this information, you can infer if the changes introduced in the commit are changing the functionality of a class or not.",
                usage_instructions="Learning the changes made to classes (if any) in a commit helps you understand the impact of the changes on the functionality of codebase on a class-level.",
                reading_instructions="Reading this information should be done purely comperatively. You should focus on finding any difference between class summaries before and after the commit.",
                trustworthiness=Trustworthiness.LOW,
                heading_level=3,
            )
            changed_class_functionality_summary = (
                changed_class_functionality_summary_card
            )

        changed_files_importance = commit_context["changed_files_importance"]
        if use_information_card:
            changed_files_importance_card = InformationCard(
                "Changed Files Relative Importance",
                changed_files_importance,
                learning_instructions="By following the reading instructions, you will learn the relative importance of each modified file in the commit.",
                usage_instructions="The relative importance of affected files in a commit must be considered when writing the body of a commit message. The changes in the most important files should be described first in the body of the commit message.",
                reading_instructions="You should read the numbered list of affected files by the commit from 1 to the last that are sorted from most important to least important.",
                trustworthiness=Trustworthiness.HIGH,
                heading_level=3,
            )
            changed_files_importance = changed_files_importance_card

        associated_issues = commit_context["associated_issues"]
        if use_information_card:
            associated_issues_card = InformationCard(
                "Linked Issues",
                associated_issues,
                learning_instructions="From this information, you will learn the potential external factors motivating the changes introduced in the commit.",
                usage_instructions="Understanding the issues associated with a commit helps you understand potential bugs, feature requests, or other tasks that are being addressed by the commit.",
                reading_instructions="You should read the numbered list of issues from 1 to the last that are linked to the commit.",
                trustworthiness=Trustworthiness.HIGH,
                heading_level=3,
            )
            associated_issues = associated_issues_card

        associated_pull_requests = commit_context["associated_pull_requests"]
        if use_information_card:
            associated_pull_requests_card = InformationCard(
                "Linked Pull Requests",
                associated_pull_requests,
                learning_instructions="From the associated pull requests, you will learn if the commit is addressing a specific pull request. If so, you will learn the motivation and reasoning behind the changes introduced in the commit based on the linked pull request.",
                usage_instructions="Understanding the pull requests associated with a commit helps you understand the context in which the commit was made.",
                reading_instructions="You should read the numbered list of pull requests from 1 to the last that are linked to the commit.",
                trustworthiness=Trustworthiness.HIGH,
                heading_level=3,
            )
            associated_pull_requests = associated_pull_requests_card

        self.commit_context = {
            "git_diff": diff,
            "changed_files_importance": changed_files_importance,
            "changed_method_summaries": changed_method_summaries,
            "changed_class_functionality_summary": changed_class_functionality_summary,
            "associated_issues": associated_issues,
            "associated_pull_requests": associated_pull_requests,
        }

    def _reset(self):
        for player in self.players:
            player.reset_history()
        self.moderator.reset_history()

    # Json
    # def _get_moderator_response(self, query):
    #     moderator_response = self.moderator.ask(query)
    #     json_loaded = False
    #     while not json_loaded:
    #         try:
    #             parsed_mod_response = json.loads(moderator_response)
    #             json_loaded = True
    #         except json.decoder.JSONDecodeError as e:
    #             moderator_response = self.moderator.ask(
    #                 e.msg
    #                 + " It seems like your response is not a correct JSON blob. Please provide a valid JSON blob."
    #             )
    #     return moderator_response, parsed_mod_response

    # Markdown-based
    def _get_moderator_response(self, query):
        moderator_response = self.moderator.ask(query)

        selected_answer = selected_answer_regex.search(moderator_response)
        while not selected_answer:
            moderator_response = self.moderator.ask(
                "You forgot to mention the selected answer in your evaluation. Please provide the selected answer."
            )
            selected_answer = selected_answer_regex.search(moderator_response)

        # rendered = mistletoe.markdown(moderator_response, renderer=ASTRenderer)

        return moderator_response, selected_answer.group(1).strip('" `')

    def _reverse_role(self, prev_role):
        if prev_role == "senior":
            return "junior"
        return "senior"

    def _what_round(self):
        what_context = {
            "diff": self.commit_context["git_diff"],
            "changed_method_summaries": self.commit_context["changed_method_summaries"],
            "changed_class_functionality_summary": self.commit_context[
                "changed_class_functionality_summary"
            ],
        }
        what_context = prompts.make_context(self.use_information_card, **what_context)

        if self.use_role_reversal:
            round_prompt = prompts.get_what_prompt(self.use_information_card).format(
                context=what_context.replace("{", "{{").replace("}", "}}")
            )
        else:
            round_prompt = prompts.get_what_prompt(self.use_information_card).format(
                context=what_context
            )

        round_debate = []
        prev_role = "senior"
        for p in self.players:
            if self.use_role_reversal:
                current_role = self._reverse_role(prev_role)
                player_query = round_prompt.format(
                    role=prompts.roles_instructions[current_role]
                )
            else:
                player_query = round_prompt

            prev_answers = "\n".join(round_debate)
            player_query += f"\n\n{prev_answers}"
            response = p.ask(player_query)
            round_debate.append(f'{p.name} argues: "{response}"')
            prev_role = current_role

        moderator_prompt = prompts.moderator_prompt.format(
            round_num=1,
            topic="Understanding *what* changes have been made in the commit",
            context=what_context,
            evaluation_criteria=prompts.what_criteria,
            debate="\n".join(round_debate),
        )
        moderator_response, parsed_mod_response = self._get_moderator_response(
            moderator_prompt
        )

        what = parsed_mod_response
        # what = parsed_mod_response["selected_answer_value"]
        if self.use_information_card:
            round_result = InformationCard(
                "Commit Changes Report",
                what,
                learning_instructions="By following the reading instructions, you will learn the changes introduced in the commit.",
                usage_instructions="Use this information to write the body of the commit message.",
                reading_instructions="You should read the report to understand the changes introduced in the commit.",
                trustworthiness=Trustworthiness.HIGH,
                heading_level=3,
            )
        else:
            round_result = what

        return moderator_response, round_result, round_debate

    def _why_round(self, moderator_response, what_debate):
        # for p in self.players:
        #     p.switch_temperature()

        why_context = {
            "associated_issues": self.commit_context["associated_issues"],
            "associated_pull_requests": self.commit_context["associated_pull_requests"],
        }
        why_context = prompts.make_context(self.use_information_card, **why_context)
        round_prompt = prompts.why_round_prompt.format(context=why_context)

        round_debate = []
        prev_role = "junior"
        for i in range(len(self.players)):
            if self.use_role_reversal:
                current_role = self._reverse_role(prev_role)
                player_query = round_prompt.format(
                    role=prompts.roles_instructions[current_role]
                )
            else:
                player_query = round_prompt

            p = self.players[i]
            p_query = ""
            for j in range(i + 1, len(what_debate)):
                p_query += f"{what_debate[j]}\n"
            p_query += (
                f"Round #1 is finished with the following conclusion by the moderator:\n\n{moderator_response}\n\n"
                f"Now, it is time to move on to the next round. \n\n{player_query}"
            ) + "\n\n"
            p_query += "\n".join(round_debate)
            response = p.ask(p_query.strip())
            p_argument = f'{p.name} argues: "{response}"'
            round_debate.append(p_argument)
            prev_role = current_role

        moderator_prompt = prompts.moderator_prompt.format(
            round_num=2,
            topic="Understanding potential external factors motivating the changes introduced in the commit",
            context=why_context,
            evaluation_criteria="Are the learnings from the context correct and accurate based on the provided information cards? Are the reasons behind the changes in the commit comprehensively understood? Is there any hallucination or vagueness in the report?",
            debate="\n".join(round_debate),
        )

        mod_response, parsed_mod_response = self._get_moderator_response(
            moderator_prompt
        )

        why = parsed_mod_response
        # why = parsed_mod_response["selected_answer_value"]
        if self.use_information_card:
            round_result = InformationCard(
                "External Factors",
                why,
                learning_instructions="By following the reading instructions, you will learn any external factors behind the changes introduced in the commit.",
                usage_instructions="Use this information to write the body of the commit message.",
                reading_instructions="You should read the report to understand any external reasons behind the changes introduced in the commit.",
                trustworthiness=Trustworthiness.HIGH,
                heading_level=3,
            )
        else:
            round_result = why

        return mod_response, round_result, round_debate

    def _generate_round(self, why_debate, moderator_response, what_card, why_card):
        # for p in self.players:
        #     p.switch_temperature()

        generate_context = {
            "changed_files_importance": self.commit_context["changed_files_importance"],
            "what": what_card,
            "why": why_card,
            "git_diff": self.commit_context["git_diff"],
        }
        generate_context = prompts.make_context(
            self.use_information_card, **generate_context
        )
        round_prompt = prompts.generation_round.format(
            context=generate_context.replace("{", "{{").replace("}", "}}")
        )

        round_debate = []
        prev_role = "senior"
        for i in range(len(self.players)):
            if self.use_role_reversal:
                current_role = self._reverse_role(prev_role)
                player_query = round_prompt.format(
                    role=prompts.roles_instructions[current_role]
                )
            else:
                player_query = round_prompt
            p = self.players[i]
            p_query = ""
            for j in range(i + 1, len(why_debate)):
                p_query += f"{why_debate[j]}\n"
            p_query += (
                f"Round #2 is finished with the following conclusion by the moderator:\n\n{moderator_response}\n\n"
                f"Now, it is time to move on to the next round. \n\n{player_query}"
            ) + "\n\n"
            p_query += "\n".join(round_debate)
            response = p.ask(p_query.strip())
            p_argument = f'{p.name} argues: "{response}"'
            round_debate.append(p_argument)
            prev_role = current_role

        moderator_prompt = prompts.moderator_prompt.format(
            round_num=3,
            topic="Generating a commit message based on the provided context",
            context=generate_context,
            evaluation_criteria=prompts.good_cm
            + "You must ensure all these criteria are met in the generated commit message.\n\n",
            debate="\n".join(round_debate),
        )

        _, parsed_mod_response = self._get_moderator_response(moderator_prompt)

        cm = json_repair.loads(parsed_mod_response)
        if isinstance(cm, list):
            cm = cm[0]
        print(cm)
        cm = f"{cm['type']}: {cm['subject']}\n{cm['body']}".strip()

        return cm

    def run(self):

        # What
        # what_context = {
        #     "diff": self.commit_context["git_diff"],
        #     "changed_method_summaries": self.commit_context["changed_method_summaries"],
        #     "changed_class_functionality_summary": self.commit_context[
        #         "changed_class_functionality_summary"
        #     ],
        #     # "changed_files_importance": self.commit_context["changed_files_importance"],
        # }
        # what_context = prompts.make_context(self.use_information_card, **what_context)

        # # changed_java_files = get_changed_java_files(commit_url)
        # # what_context = ""
        # # for changed_file in changed_java_files:
        # #     file, old, new = changed_file
        # #     what_context += f"### Changed File\n\n{file}\n\n### Old Content\n{old}\n\n### New Content\n\n{new}\n\n"
        # # what_context = what_context.strip()

        # round_prompt = prompts.get_what_prompt(self.use_information_card).format(
        #     context=what_context
        # )
        # p1_response = self.players[0].ask(round_prompt)
        # p2_response = self.players[1].ask(
        #     round_prompt
        #     + f'\n\n{self.players[0].name} argues: "{p1_response}"'
        #     # + f"\n You disagree with the argument by {self.players[0].name}. Please provide your response and reasoning based on the round's evaluation criteria."
        # )

        # round_debate = f"{self.players[0].name}: {p1_response}\n{self.players[1].name}: {p2_response}"
        # moderator_prompt = prompts.moderator_prompt.format(
        #     round_num=1,
        #     topic="Understanding *what* changes have been made in the commit",
        #     context=what_context,
        #     evaluation_criteria="Are the learnings from the context correct and accurate based on the provided information cards? Are the changes in the commit comprehensively understood? Is there any hallucination or vagueness in the report?",
        #     debate=round_debate,
        # )
        # moderator_response, parsed_mod_response = self._get_moderator_response(
        #     moderator_prompt
        # )

        # what = parsed_mod_response
        # # what = parsed_mod_response["selected_answer_value"]
        # if self.use_information_card:
        #     what_card = InformationCard(
        #         "Commit Changes Report",
        #         what,
        #         learning_instructions="By following the reading instructions, you will learn the changes introduced in the commit.",
        #         usage_instructions="Use this information to write the body of the commit message.",
        #         reading_instructions="You should read the report to understand the changes introduced in the commit.",
        #         trustworthiness=Trustworthiness.HIGH,
        #         heading_level=3,
        #     )
        # else:
        #     what_card = what
        moderator_response, what_card, what_debate = self._what_round()
        # print(what_card)
        # Why
        # for p in self.players:
        #     p.switch_temperature()

        # why_context = {
        #     "associated_issues": self.commit_context["associated_issues"],
        #     "associated_pull_requests": self.commit_context["associated_pull_requests"],
        # }
        # why_context = prompts.make_context(self.use_information_card, **why_context)
        # round_prompt = prompts.why_round_prompt.format(context=why_context)
        # p1_query = f'{self.players[1].name} argues: "{p2_response}"\n\nRound 1 is finished with the following conclusion by the moderator:\n\n{moderator_response}\n\nNow, it is time to move on to the next round. \n\n{round_prompt}'
        # p1_response = self.players[0].ask(p1_query)

        # p2_query = f'Round 1 is finished with the following conclusion by the moderator:\n\n{moderator_response}\n\nNow, it is time to move on to the next round. \n\n{round_prompt}\n\n{self.players[0].name} argues: "{p1_response}"'
        # p2_response = self.players[1].ask(p2_query)

        # round_debate = f"{self.players[0].name}: {p1_response}\n{self.players[1].name}: {p2_response}"
        # moderator_prompt = prompts.moderator_prompt.format(
        #     round_num=2,
        #     topic="Understanding potential external factors motivating the changes introduced in the commit",
        #     context=why_context,
        #     evaluation_criteria="Are the learnings from the context correct and accurate based on the provided information cards? Are the reasons behind the changes in the commit comprehensively understood? Is there any hallucination or vagueness in the report?",
        #     debate=round_debate,
        # )

        # moderator_response, parsed_mod_response = self._get_moderator_response(
        #     moderator_prompt
        # )

        # why = parsed_mod_response
        # # why = parsed_mod_response["selected_answer_value"]
        # if self.use_information_card:
        #     why_card = InformationCard(
        #         "External Factors",
        #         why,
        #         learning_instructions="By following the reading instructions, you will learn any external factors behind the changes introduced in the commit.",
        #         usage_instructions="Use this information to write the body of the commit message.",
        #         reading_instructions="You should read the report to understand any external reasons behind the changes introduced in the commit.",
        #         trustworthiness=Trustworthiness.HIGH,
        #         heading_level=3,
        #     )
        # else:
        #     why_card = why
        moderator_response, why_card, why_debate = self._why_round(
            moderator_response, what_debate
        )

        # Generate
        # for p in self.players:
        #     p.switch_temperature()

        # generate_context = {
        #     "changed_files_importance": self.commit_context["changed_files_importance"],
        #     "what": what_card,
        #     "why": why_card,
        #     "git_diff": self.commit_context["git_diff"],
        # }
        # generate_context = prompts.make_context(
        #     self.use_information_card, **generate_context
        # )
        # round_prompt = prompts.generation_round.format(context=generate_context)
        # p1_query = f'{self.players[1].name} argues: "{p2_response}"\n\nRound 2 is finished with the following conclusion by the moderator:\n\n{moderator_response}\n\nNow, it is time to move on to the next round. \n\n{round_prompt}'
        # p1_response = self.players[0].ask(p1_query)

        # p2_query = f'Round 2 is finished with the following conclusion by the moderator:\n\n{moderator_response}\n\nNow, it is time to move on to the next round. \n\n{round_prompt}\n\n{self.players[0].name} argues: "{p1_response}"'
        # p2_response = self.players[1].ask(p2_query)

        # round_debate = f"{self.players[0].name}: {p1_response}\n{self.players[1].name}: {p2_response}"
        # moderator_prompt = prompts.moderator_prompt.format(
        #     round_num=3,
        #     topic="Generating a commit message based on the provided context",
        #     context=generate_context,
        #     evaluation_criteria=prompts.good_cm
        #     + "You must ensure all these criteria are met in the generated commit message.\n\n",
        #     debate=round_debate,
        # )

        # moderator_response, parsed_mod_response = self._get_moderator_response(
        #     moderator_prompt
        # )

        # cm = json_repair.loads(parsed_mod_response)
        # cm = f"{cm['type']}: {cm['subject']}\n{cm['body']}".strip()
        cm = self._generate_round(why_debate, moderator_response, what_card, why_card)

        # cm = parsed_mod_response["selected_answer_value"]
        # json_loaded = False
        # while not json_loaded:
        #     try:
        #         cm = json.loads(cm)
        #         json_loaded = True
        #     except json.decoder.JSONDecodeError:
        #         moderator_response, parsed_mod_response = self._get_moderator_response(
        #             moderator_prompt
        #         )

        #         cm = parsed_mod_response
        # cm = parsed_mod_response["selected_answer_value"]

        # cm = format_output(cm)
        self._reset()
        return cm
        # print(cm)
