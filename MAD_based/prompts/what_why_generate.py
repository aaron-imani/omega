from MAD_based.utils.information_card import InformationCard

senior_persona = "You are a senior Java developer with strong debate skills."
inexperinced_persona = (
    "You are a junior Java developer with limited knowledge and high confidence."
)

# round_instructions = {
#     "senior": (
#         # "In any round, if other participants have proposed their answer sooner than you, you should first reflect on their answers and then propose your answer and reasoning."
#         "In any round, if other participants have proposed their answer sooner than you, you should first find out if their response meets the round's evaluation criteria, "
#         "then propose an alternative answer based on the potential defficiences in their answer. "
#     ),
#     "inexperienced": (
#         "In any round, whatever the topic and context you are given, you will answer incorrectly with small errors that cannot easily be caught by the other participants. Remember, no one should know that you are intentionally answering incorrectly. "
#     ),
# }

roles_instructions = {
    "junior": (
        "In this round of debate, you play the role of a junior developer. Here are your roles' properties:\n"
        "1. You do not follow the evaluation criteria. Your learnings from the round's context are incorrect and you answer based on your incorrect learnings.\n"
        "2. Your must make some relevant mistakes in your answers as the result of incorrect interpretation of the round's context. Your answer must not be correct based on the round's context.\n"
        "2.1. Your answer must include some hallucination about the round's context.\n"
        "3. You are confident about your answer you try to convince other participants that your answer is correct by reasoning."
    ),
    "senior": (
        "In this round of debate, you play the role of a senior developer. Here are your roles' properties:\n"
        "1. You are faithful to the evaluation criteria. You will try to answer the questions based on the evaluation criteria.\n"
        "2. You will try to catch the errors in the other participants' answers and correct them by reasoning.\n"
        "3. You are confident about your answer you try to correct other participants' mistakes in your answers."
    ),
}


def get_players_initial_system_prompt(use_information_card):
    extra_information = (
        (
            f"The context will be presented as information cards. {InformationCard.get_strucuture()}"
            "Information cards are separated by horizontal lines.\n"
        )
        if use_information_card
        else "\n"
    )

    # player_initial_system_prompt = (
    #     "{persona} "
    #     "Hello and welcome to the debate. "
    #     'In this debate, your name is "{player_name}" and there are {num_debators} other participants in this debate. '
    #     "In each of round debate, you will be given the following items:\n"
    #     "\t- Topic: The topic you will debate in the round\n"
    #     f"\t- Round's context: The context you have in the round. {extra_information}"
    #     "\t- Evaluation criteria: The criteria you should consider while debating about the topic\n\n"
    #     "Hence, your task is to debate with other participants about the current topic by providing your perspective and reasoning based on the evaluation criteria. "
    #     "You are allowed to use and cite current and previous rounds' context and discussions to support your reasoning. \n {round_instructions}"
    #     # "- You will be given contextual information about a commit, and in each round of the discussion, you will be given a topic and a round's task."
    #     # "In each round of debate, your task is to debate with the other participants about the current topic by providing your perspective and reasoning. "
    # )

    player_initial_system_prompt = (
        "You are an experienced Java developer hired to participate in an educational debate. "
        'In this debate, your name is "{player_name}" and there are {num_debators} other participants in this debate. '
        "The goal of the debate is to make an insightful debate around the commit message generation process. "
        "The debate will then be used as a learning material for junior developers to learn what are common mistakes in commit message generation and how to correctly do the commit message generation process. "
        "To make the debate insightful, in each round, you will be assigned a role that you should play in the debate. The purpose of roleplaying is to make the debate more engaging and introduce common mistakes in commit message generation. "
        "The debate will be conducted on a round-by-round basis, with each round focusing on a specific topic and task. "
        "In each of round debate, you will be given the following items:\n"
        "\t- Role: Your role description in the debate. You should play this role in that round of debate.\n"
        "\t- Topic: The topic you will debate in the round\n"
        f"\t- Round's context: The context you have in the round. {extra_information}"
        "\t- Evaluation criteria: The criteria you should consider while debating about the topic\n\n"
        # "In each round of the debate, you will be given "
        "Hence, your task is to play your role in each round and debate with other participants about the current topic by providing your perspective and reasoning based on the evaluation criteria. "
        "You are allowed to use and cite current and previous rounds' context and discussions to support your reasoning. "
        "In any round, if other participants have proposed their answer sooner than you, you should first find out if their response meets the round's evaluation criteria, "
        "then propose an alternative answer based on the potential defficiences in their answer. \n\n"
        "Remember, your roleplaying is crucial for this debate to be instructive for junior developers."
        # "- You will be given contextual information about a commit, and in each round of the discussion, you will be given a topic and a round's task."
        # "In each round of debate, your task is to debate with the other participants about the current topic by providing your perspective and reasoning. "
    )
    return player_initial_system_prompt


moderator_system_prompt = (
    "You are a strict moderator in a debate. "
    "The debate will be conducted on a round-by-round basis, with each round focusing on a specific topic and task. "
    "In each round of the debate, you will be given the topic, the context, the participants' debate, and some evaluation criteria. "
    "When a debate round is finished, you must carefully evaluate the participants' responses based on all the evaluation criteria and decide if the round can be concluded or not. "
)

moderator_prompt = (
    "Round #{round_num} of the debate has ended. Here is the round's information:\n\n"
    "## Topic\n{topic}\n\n"
    "## Round Context\n{context}\n\n"
    "## Evaluation Criteria\n{evaluation_criteria}\n\n"
    "## Participants' Debate\n{debate}\n\n"
    "Based on the evaluation criteria, carefully evaluate the participants' responses and structure your evaluation like below:\n"
    "```\n"
    "# Round {round_num} Evaluation\n"
    "## Indiviual Evaluations\n\n"
    "Participant 1 Evaluation: (your evaluation of participant 1's debate)\n"
    "Participant 2 Evaluation: (your evaluation of participant 2's debate)\n"
    "## Round Conclusion\n\n"
    "If the round can be concluded or not (yes/no). Round can be concluded if all the evaluation criteria are met by at least one participant.\n"
    "## Winner\n\n"
    "If the round is concluded, then which participant's answer is preferred. Pick one.\n"
    "## Winner Selection Rationale\n\n"
    "The reason for the preferred participant's answer based on each and all evaluation criteria.\n"
    "## Selected Answer For Round {round_num}\n\n"
    "The value of selected answer if the round is concluded. "
    "Directly quote the answer of the preferred participant in this field. "
    "If the answer is a JSON blob, do not wrap it in quotes. "
    "Be faithful to the answer and do not add or remove any content.\n"
    "```\n"
    # '{{"is_concluded": "If the round can be concluded or not (yes/no). Round can be concluded if all the evaluation criteria are met by at least one participant.", '
    # '"conclusion": "if is_concluded is yes, then which participant\'s answer is preferred. Pick one.", '
    # '"reason": "The reason for the preferred participant\'s answer based on each and all evaluation criteria", '
    # '"selected_answer_value": "The value of selected answer if the round is concluded. Directly quote the answer of the preferred participant in this field. Be faithful to the answer and do not add or remove any content."}}'
    # "\n```\n"
    # "Based on the evaluation criteria, please evaluate the participants' debate and structure your evaluation as a JSON blob like below:\n"
    # "```json\n"
    # '{{"is_concluded": "If the round can be concluded or not (yes/no). Round can be concluded if all the evaluation criteria are met by at least one participant.", '
    # '"conclusion": "if is_concluded is yes, then which participant\'s answer is preferred. Pick one.", '
    # '"reason": "The reason for the preferred participant\'s answer based on each and all evaluation criteria", '
    # '"selected_answer_value": "The value of selected answer if the round is concluded. Directly quote the answer of the preferred participant in this field. Be faithful to the answer and do not add or remove any content."}}'
    # "\n```\n"
    # "Please strictly output in JSON format, do not output irrelevant content."
)

what_criteria = (
    "Detail: The extent to which the participant's report provides detailed information about the changes in the commit. This means how detailed the changes have been explained without hallucination.\n"
    "Precision: The extent to which the participant's report is *factual* and *accurate* in explaining the changes in the commit. This means any claimed change, should be directly evident from the round's context.\n"
    "Recall: The extent to which the participant's report recalls all the changes in the commit. This means the report does not miss any changes in the commit.\n\n"
)


def get_what_prompt(use_information_card):

    report_instructions = (
        (
            "(Your learnings from each information card about the commit. "
            "It should include how you read each card and what you learned from each in the context of the commit. "
            "The learnings must be detailed. Information cards' metadata must be followed accurately to write this part of the answer.)"
        )
        if use_information_card
        else "(Your learnings from the context of the commit. It should include how you read the context and what you learned from each part of it in the context of the commit.)"
    )

    what_round_prompt = (
        "# Round 1\n"
        "## Your Role\n\n{{role}}\n\n"
        "## Topic\n\nIn this round, your task is to understand *what* changes have been made in the commit. "
        "You must not discuss why the changes were made or what are the implications of the changes. "
        "You should carefully read the provided round's context and provide your perspective on the changes made in the commit. "
        "You must be truthful and accurate in your responses and provide detailed reasoning based on the evaluation criteria.\n"
        "You should properly use the provided contextual information about the commit to correctly and completely understand the changes made in the commit. "
        "Answers in this round must be structured as below:\n\n```\n"
        "# Reflection\n\n(You must reflect on other participants' arguments in this round. If you are the first one to answer, you can skip this part.)\n\n"
        f"# Learnings\n\n{report_instructions}\n\n"
        "# Changed files\n\n(The files that have been changed)\n\n"
        "# Changed methods\n\n(The methods which bodies have been changed, if any)\n\n"
        "# Changed class(es)\n\n(The classes which bodies that have been changed, if any)\n\n"
        "# Report\n\n(A descriptive report of the changes occurred in the commit. The report must mention all the changes in detail (what has changed where) so that a developer without access to the diff can fully understand the changes in depth with reading your report.)\n```\n"
        "## Context{context}"
        # "## Context\n\n{context}\n\n"
        # "## Evaluation Criteria\n\nFor all the changes you claim to have occurred in the commit, you should directly cite the part of context you used to derive that change and provide a detailed explanation of how you have derived the change from that part of the context. "
        # "If that part of the context does not exist in the round's context, your answer will be invalid.\n"
        f"## Evaluation Criteria\n\n{what_criteria}"
        "Remember your role when writing your answers."
        # "Factuality: The extent to which the participant's learnings are accurate and truthful based on the round's context. Hallucination or vagueness in the report will be considered as a lack of factuality.\n"
        # "Comprehensiveness: The extent to which the participant's report covers all the changes in the commit.\n"
        # "For all the changes you claim in the commit, you should directly cite the part of context you used to derive that change and provide a detailed explanation of how you have derived the change from that part of the context. "
        # "Your answer will be invalid if the explanation does not justify the change you are claiming based on the context or the context part is made up and does not exist in the round's context.\n"
    )
    return what_round_prompt


why_round_prompt = (
    "# Round 2\n"
    "## Your Role\n\n{{role}}\n\n"
    "## Topic\n\nIn this round, the topic is to understand the reasons/motivation/rationale behind the changes made in the commit. "
    "Answers in this round must be structured as below:\n\n```\n"
    "# Reflection\n\n(You must reflect on other participants' arguments in this round. If you are the first one to answer in the current round of debate, you must skip this part.)\n\n"
    f"# Learnings\n\n(What you learned from the context\n\n"
    "# Changes Rationale\n\n(Reasons/motivation/rationale behind the changes made in the commit. You must provide a direct quote from the context to justify each reason you claim. "
    "\n```\n\n"
    # "If no evidence is found in the context, you, as the developer, should make an educated guess based on all the context from previous round. "
    "## Context{context}"
    "## Evaluation Criteria\n\n"
    "Any identified reasons/motivation/rationale must be directly related to one of the changes in the commit and must be a direct quote from a round's context."
    # "For all the changes understood in the commit, you should cite the context and provide a detailed explanation of why the change was made. "
    # "Your answer will be invalid if the explanation does not justify the reason behind the change you are claiming based on the context.\n"
)

good_cm = (
    "A good commit message must be structured as below:\n\n<type>: <subject>\n<body>\n\n"
    "<type> must be one of the following four software maintenance activities: feat, fix, style, and refactor. The definitions of these activities are given below:\n"
    "\tfeat: introducing new features into the system.\n"
    "\tfix: fixing faults or software bugs.\n"
    "\tstyle: code format changes such as fixing redundant white-space, adding missing semi-colons, etc.\n"
    "\trefactor: changes made to the internal structure of software to make it easier to understand and cheaper to modify without changing its observable behavior.\n"
    "<subject> must be roughly at most 72 characters. It should contain a brief summary of the changes introduced by the commit. You must use **imperative mood** to write it.\n"
    "<body> is optional but strongly recommended. "
    "\t<body> should comprehensively provide additional relevant contextual information about **all** the changes made and/or justifications/motivations behind them. \n"
    "\tThe changes related to the most important files must be mentioned first in the <body>. \n"
    "\tIf you are uncertain about why certain changes are introduced, do not mention the reason in the <body>.\n"
    "\t<body> must not mention things that have not been changed in the commit and should only focus on the changes.\n"
    "\t<body> must not be verbose with too much details that are not informative for other developers.\n"
    "The commit message should be in the format of a JSON blob with the following keys: type, subject, and body. The value of each key should be a string. Empty value is allowed for the body key."
)

cm_eval_criteria = (
    "Overall, a good commit message must satisfy all the following quality criteria:\n"
    "1. Rationality: reflects whether the commit message provides the *reason/rationale/motivation* behind the changes.\n"
    "2. Comprehensiveness: reflects whether the message summarizes *all* the changes occurred in the commit.\n"
    "3. Conciseness: indicates whether the commit message is to the point and avoids unnecessary sentences that are general and not informative for other developers.\n"
    "4. Expressiveness: reflects whether the message content is fluent and grammatically correct.\n\n"
)


# generation_round = (
#     "# Round 3\n"
#     f"## Topic\n\nIn this round, your task is to generate a commit message for the given commit. {good_cm}"
#     "You should use the provided contextual information about the commit to generate a commit message that satisfies the evaluation criteria.\n\n"
#     "## Round Context{context}"
#     "## Evaluation Criteria\n\n"
#     f"{cm_eval_criteria}"
# )

generation_round = (
    "# Round 3\n"
    "## Your Role\n\n{{role}}\n\n"
    f"## Topic\n\nIn this round, your task is to write a commit message for the given commit."
    "You should use all the provided contextual information about the commit in previous rounds and this round to write a commit message that satisfies the evaluation criteria.\n\n"
    "## Round Context{context}"
    "## Evaluation Criteria\n\n"
    f"{good_cm}\n\n{cm_eval_criteria}\n\n"
    "Lastly, the only context you are allowed to cite/mention in your commit message is any associated issue or pull request. If there is no associated issue or pull request, you should not say anything about it in the commit message. "
    "All other context parts must be used to derive the changes and reasons behind the changes in the commit message and not directly mentioned in the commit message."
)

# Enhanced
# evaluation_criteria = (
#     "A good commit message is structured as below:\n\n<type>: <subject>\n<body>\n\n"
#     "<type> must be one of the following four software maintenance activities: feat, fix, style, and refactor. The definitions of these activities are given below:\n"
#     "\tfeat: introducing new features into the system.\n"
#     "\tfix: fixing faults or software bugs.\n"
#     "\tstyle: code format changes such as fixing redundant white-space, adding missing semi-colons, etc.\n"
#     "\trefactor: changes made to the internal structure of software to make it easier to understand and cheaper to modify without changing its observable behavior.\n"
#     "<subject> must be roughly at most 72 characters. It should contain a brief summary of the changes introduced by the commit. You must use **imperative mood** to write it.\n"
#     "<body> is optional but strongly recommended. It should comprehensively provide additional relevant contextual information about **all** the changes made and/or justifications/motivations behind them. <body> must be written as detailed as possible.\n"
#     "Overall, a good commit message must satisfy the following quality criteria:\n"
#     "1. Rationality: reflects whether the commit message provides a logical explanation for the code change (Why information), and provides the commit type information.\n"
#     "2. Comprehensiveness: reflects whether the message describes a summary of what has been changed (What information) and also covers details (i.e., whether the commit message fails relevant imports to describe the code changes in a changed file.)\n"
#     "3. Conciseness: indicates whether the message conveys information succinctly, ensuring readability and quick comprehension.\n"
#     "4. Expressiveness: reflects whether the message content is grammatically correct and fluent.\n\n"
#     "The commit message should be in the format of a JSON blob with the following keys: type, subject, and body. The value of each key should be a string. Empty value is allowed for the body key."
# )


# base_prompt = (
#     "{evaluation_criteria}\n\nYou are given a partial commit message written as below:\n{{partial_cm}}\n\nGenerate the <{{cm_part}}> part of it for the following commit:\n\nSTART OF COMMIT CONTEXT{{context}}\n\nEND OF COMMIT CONTEXT\n\n"
#     "\n* Only output the <{{cm_part}}> part without any irrelevant content."
# ).format(evaluation_criteria=evaluation_criteria)

# player_system_prompt = (
#     "You are a debater. Hello and welcome to the commit message generation competition, which will be conducted in a debate format. "
#     "It is not necessary to fully agree with each other's perspectives, as the objective is to write the <{{cm_part}}> part of a good commit message.\n"
#     "{evaluation_criteria}\nThe debate topic is stated as follows:\nGiven the partial commit message and the commit information, "
#     "what should be written for the <{{cm_part}}> part of the commit message?\n\n"
#     "Partial Commit Message:\n{{partial_cm}}\n\nSTART OF COMMIT CONTEXT{{context}}\n\nEND OF COMMIT CONTEXT\n\n"
# ).format(evaluation_criteria=evaluation_criteria)

# moderator_system_prompt = (
#     "You are a moderator. There will be {{num_debators}} debaters involved in a competition to properly complete a partial commit message. "
#     "They will propose their answers and discuss their perspectives on the proper value for the <{{cm_part}}> part of the partial commit message "
#     "that has been written for the following commit.\n\n"
#     "Partial Commit Message:\n{{partial_cm}}\n\nSTART OF COMMIT CONTEXT\n\n{{context}}\n\nEND OF COMMIT CONTEXT\n\n"
#     "At the end of each round, you will evaluate the candidate answers based on the following definition a good commit message:\n\n{evaluation_criteria}"
# ).format(evaluation_criteria=evaluation_criteria)

# moderator_prompt = (
#     "The {round_num} round of debate for both sides has ended. Below is the conversation between the debaters:\n\n{conversation}\n\n"
#     "You, as the moderator, will evaluate both sides' answers and determine if there is a clear preference for the {cm_part} of the partial commit message. "
#     "If there is, please summarize your reasons for supporting affirmative/negative side and select the final commit message accordingly. "
#     "If not, the debate will continue to the next round. Now please output your decision in json format, with the format as follows: "
#     '{{"Whether there is a preference": "Yes or No", "Supported Debator": "Name of the supported debater", "Reason": "Rigorous raesons based on the definition of a good commit message.", "selected_{cm_part}": ""}}.'
#     "\n\nIMPORTANT: Please strictly output in JSON format, do not output irrelevant content."
# )

# affirmitive_prompt = 'You agree with {debater_name} which is: "{base_cm}". Restate the <{cm_part}> based on the initial guidelines of a good commit message and provide your reasons.'
# negative_prompt = "{affirmitive_side_answer}\n\nYou disagree with my proposed <{cm_part}>. Provide your own <{cm_part}> and reasons."
# debate_prompt = "{opponent_answer}\n\nDo you agree with my perspective? Please provide your reasons and a suggested <{cm_part}>."

# judge_prompt_1 = (
#     "Consider the following conversations in the current debate round:\n\n{conversation}\n\n"
#     "What candidate <{cm_part}>s do we have? Present them without reasons."
# )
# judge_prompt_2 = (
#     "Therefore, what should be written for the <{{cm_part}}> part of the commit message?\n\n"
#     "Partial Commit Message:\n{{partial_cm}}\n\nSTART OF COMMIT CONTEXT{{context}}\n\nEND OF COMMIT CONTEXT\n\n"
#     "Please summarize your reasons based on the good commit message guidelines and give the final <{{cm_part}}> that you think is suitable. "
#     'Please output your answer in json format, with the format as follows: {{"Reason": "Rigorous reasons based on the evaluation criteria", "debate_{{cm_part}}": ""}}.\n\n'
#     "IMPORTANT: Please strictly output in JSON format, do not output irrelevant content."
# )

diff_reading_instruction = """A git diff lists modified/added/deleted Java files information in the following format:
`--- a/file.java\\n+++ b/file.java`: indicates the files being compared, with `a/` representing the old version and `b/` the new version.
The changes to the file are then shown as a list of hunks, where each hunk consists of:
1. A hunk header like '@@ -5,8 +5,9 @@' that states that the hunk covers the lines 5 to 5 + 8 in the old version and lines 5 to 5 + 9 in the new version.
2. Changed lines are listed with:
    The prefix 'ADDED LINE': for added lines
    The prefix 'REMOVED LINE': for deleted lines
3. Unchanged lines are listed with the prefix 'UNCHANGED LINE'.
"""

# diff_reading_instruction = """A git diff highlightes the changes in the commit in the following format:
# Files: Lines starting with # FILE: indicate changed file paths.
# Hunks: Lines starting with @@ HUNK: mark the location and range of changes.
# Added Lines: Lines starting with '+++' are new.
# Removed Lines: Lines starting with '---' are deleted.
# Unchanged Lines: Any other are lines are unchanged and provide context.
# """

git_diff_formatter = (
    f"{diff_reading_instruction}\n\n"
    "Here is the Git diff for the commit:\n\n{diff}\n\n"
)


def make_title(text):
    text = text.replace("_", " ").split()
    return " ".join([word.capitalize() for word in text])


def make_context(from_information_cards, **kwargs):
    context = "\n\n"
    if from_information_cards:
        for key, value in kwargs.items():
            context += str(value)
    else:
        for key, value in kwargs.items():
            context += f"### {make_title(key)}\n\n{value}\n\n"
    return context
