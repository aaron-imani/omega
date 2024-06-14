# Basic
# evaluation_criteria = (
#     "A good commit message is structured as below:\n\n<type>: <subject>\n<body>\n\n"
#     "<subject> must be at most 72 characters. It should contain a brief summary of the changes introduced by the commit. You must use **imperative mood** to write it.\n"
#     "<body> is optional but strongly recommended. It should be used to provide additional relevant contextual information and/or justifications/motivations behind the commit.\n"
#     "<type> must be one of the following four software maintenance activities: feat, fix, style, and refactor. The definitions of these activities are given below:\n"
#     "\tfeat: introducing new features into the system.\n"
#     "\tfix: fixing faults or software bugs.\n"
#     "\tstyle: code format changes such as fixing redundant white-space, adding missing semi-colons, etc.\n"
#     "\trefactor: changes made to the internal structure of software to make it easier to understand and cheaper to modify without changing its observable behavior.\n"
#     "The commit message should be in the format of a JSON blob with the following keys: type, subject, and body. The value of each key should be a string. Empty value is allowed for the body key."
# )

# Enhanced
evaluation_criteria = (
    "A good commit message is structured as below:\n\n<type>: <subject>\n<body>\n\n"
    "<type> must be one of the following four software maintenance activities: feat, fix, style, and refactor. The definitions of these activities are given below:\n"
    "\tfeat: introducing new features into the system.\n"
    "\tfix: fixing faults or software bugs.\n"
    "\tstyle: code format changes such as fixing redundant white-space, adding missing semi-colons, etc.\n"
    "\trefactor: changes made to the internal structure of software to make it easier to understand and cheaper to modify without changing its observable behavior.\n"
    "<subject> must be roughly at most 72 characters. It should contain a brief summary of the changes introduced by the commit. You must use **imperative mood** to write it.\n"
    "<body> is optional but strongly recommended. It should elaborately provide additional relevant contextual information about all the changes made and/or justifications/motivations behind them.\n"
    "Overall, a good commit message must satisfy the following quality criteria:\n"
    "Rationality: reflects whether the commit message provides a logical explanation for the change (Why information), and provides the commit type information. The explanation should be correct, precise, and factual based on all the available context about the commit, especially the diff.\n"
    "Comprehensiveness: reflects whether the message describes a summary of what has been changed (What information) and also covers details. No important details about the changes can be missed.\n"
    "Conciseness: indicates whether the message conveys information succinctly, ensuring readability and quick comprehension.\n"
    "Expressiveness: reflects whether the message content is grammatically correct and fluent.\n\n"
    "The commit message should be in the format of a JSON blob with the following keys: type, subject, and body. The value of each key should be a string. Empty value is allowed for the body key."
)


base_prompt = (
    "{evaluation_criteria}\n\nGenerate a good commit message for the following commit:\n\n**START OF COMMIT CONTEXT**\n{{context}}\n\n**END OF COMMIT CONTEXT**\n\n"
    "\n* Only output the commit message without any additional content."
).format(evaluation_criteria=evaluation_criteria)

player_system_prompt = (
    "You are a senior Java developer. Hello and welcome to the commit message generation competition, which will be conducted in a debate format. "
    "In this competition, your name is '{{debater_name}}'. "
    "It is not necessary to fully agree with other players' perspectives, as the objective is to find a good commit message.\n"
    "The competition will be conducted in as many rounds as necessary until the moderator concludes the debate. "
    "At the end of each round, the moderator will review the debate and evaluate the candidate commit messages based on the following definition of a good commit message:\n\n{evaluation_criteria}\n\n"
    "The moderator will then reflect on the debate if the debate shall continue to the next round. The moderator will provide constructive feedback to the players based on the evaluation criteria."
    "\n\nThe debate topic is stated as follows: Given the following context available for a commit, what is a good commit message for it?\n\n{{context}}"
).format(evaluation_criteria=evaluation_criteria)

moderator_system_prompt = (
    "You are a moderator. There will be {{num_debators}} debaters involved in a commit message generation competition that is held on a round-based debate. "
    "In each round, the players will propose their commit messages and discuss their perspectives on a good commit message for the following commit:"
    "\n\n**START OF COMMIT CONTEXT**\n{{context}}\n\n**END OF COMMIT CONTEXT**\n\n"
    "{evaluation_criteria}\n\n"
    "At the end of each round, you, as the moderator, will evaluate debaters' proposed commit message parts, i.e., type, subject, and body. "
    "For each part, you will determine if there a debater's answer that fully satisfies the requirements of that part in a good commit message. "
    "This per-part decision should be structured as a JSON blob ($part_decision) in the following format, where $part is the name of commit message part being decided:\n"
    '{{{{$PART: {{{{"concluded": "Yes/No based on the candidate answers\' adherence to the requirements for that part of a good commit message", '
    '"supported_debator": "Name of the supported debater (pick only one), if the part is concluded from the previous round of the debate",'
    '"reason": "You must provide reasons for your decision based on the requirements of a good commit message.", '
    '"selected_debator_response": "the selected value for $PART"}}}}}}}}\n\n'
    "Lastly, you will output one JSON blob called $round_conclusion structured as follows:\n"
    '{{{{"reflection": "Your reflection on the previous round of debate must include: 1) what commit messages parts are included, what is the chosen value for the concluded parts, and why the value is chosen 2) what commit message parts are the topic of the next round of debate 3) how the debaters should improve their discussion on the next round (This should be written in imperative mood and will be broadcasted to the players)", '
    '"part_decisions": "A list of $part_decision JSON blobs for each part of the commit message."}}}}'
).format(evaluation_criteria=evaluation_criteria)

print("moderator_system_prompt", moderator_system_prompt)
# moderator_prompt = (
#     "The {round_num} round of debate for both sides has ended. Below is the conversation between the debaters:\n\n{conversation}\n\n"
#     "You, as the moderator, will evaluate both sides' commit messages and determine if there is a clear preference for a commit message candidate. "
#     "If there is, please summarize your reasons for supporting affirmative/negative side and select the final commit message accordingly. "
#     "If not, the debate will continue to the next round. Now please output your decision in json format, with the format as follows: "
#     '{{"Whether there is a preference": "Yes or No", "Supported Debator": "Name of the supported debater", "Reason": "Rigorous raesons based on the definition of a good commit message.", "selected_commit_message": ""}}.'
#     "\n\nIMPORTANT: Please strictly output in JSON format, do not output irrelevant content."
# )

# moderator_prompt = (
#     "The {round_num} round of debate has ended. Below is the conversation between the debaters:\n\n{conversation}\n\n"
#     "You, as the moderator, will evaluate debaters' proposed commit message parts, i.e., type, subject, and body. "
#     "For each part, you will determine if there a debater's answer that fully satisfies the requirements of that part in a good commit message. "
#     "If there is, please summarize your reasons for supporting the debater and select the commit message part that fully satisfies the definition of a good commit messages. "
#     "If not, the debate will continue to the next round. Now please output your decision as a nested JSON blob formatted as below: "
#     """"""
#     '{{"Commit Message Part (must be type, subject, or body)":'
#     '{{"Concluded":"Yes/No based on the candidate answers\' adherence to the requirements for that part of a good commit message", '
#     '"Supported Debator": "Name of the supported debater (pick only one), if the part is concluded from the {round_num} round of the debate",'
#     '"Reason": "You must provide reasons for your decision based on the requirements for that part of a good commit message. This will be reflected as a constuctive feedback to the debaters in the next round.", '
#     '"Selected Debator Response": "the winner debater\'s written value for the commit message part"}}}}.'
#     "\n\nIMPORTANT: Please strictly output a decodable JSON blob, do not output irrelevant content."
# )

moderator_prompt = (
    "The {round_num} round of the debate has ended. Below is the conversation between the debaters:\n\n{conversation}\n\n"
    "Please output $round_conclusion for this round based on the initial instructions. Do not output anything else."
)


affirmitive_prompt = "You think a good commit message is as below:\n```\n{base_cm}\n```\n\nResend the exact commit message and provide your reasoning based on the initial guidelines of a good commit message."
negative_prompt = '{debater_name} arguing: "{affirmitive_side_answer}"\n\nHowever, you disagree with his proposed commit message. Provide your own commit message and reasons.'
debate_prompt = "{opponent_answer}\n\nDo you agree with his perspective about this round's topic? Please provide your reasons and an alternative answer for the topic."

judge_prompt_1 = (
    "Consider the following conversations in the current debate round:\n\n{conversation}\n\n"
    "What candidate commit messages do we have? Present them without reasons."
)
judge_prompt_2 = (
    "Therefore, what is a good commit message for the following commit:\n"
    "*START OF COMMIT CONTEXT*\n\n{context}\n\n*END OF COMMIT CONTEXT*\n\n"
    "Please summarize your reasons based on the good commit message guidelines and give the final commit message that you think is suitable. "
    'Please output your answer in json format, with the format as follows: {{"Reason": "Rigorous reasons based on the evaluation criteria", "debate_commit_message": ""}}.\n\n'
    "IMPORTANT: Please strictly output in JSON format, do not output irrelevant content."
)

git_diff = (
    "```\n{diff}\n```\n"
    "The git diff above lists each changed/added/deleted Java file information in the following format:\n"
    "* `diff --git a/file.java\\n+++ b/file.java`: indicating that in the following lines, lines prefixed with `---` are lines that only occur in the old version `a/file.java`,"
    "i.e. are deleted in the new version `b/file.java`, and lines prefixed with `+++` are lines that only occur in the new version `b/file.java`,"
    "i.e. are added to the new version `b/file.java`. Code lines that are not prefixed with `---` or `+++` are lines that occur in both versions, i.e. are unchanged and only listed for better context."
    "* The code changes are then shown as a list of hunks, where each hunk consists of:\n"
    "* `@@ -5,8 +5,9 @@`: a hunk header that states that the hunk covers the lines 5 to 5 + 8 in the old version and code lines 5 to 5 + 9 in the new version.\n"
    "* then those lines are listed with the prefix `---` for deleted lines, `+++` for added lines, and no prefix for unchanged lines, as described previously.\n"
    "Java comment lines start with `//` and Javadocs start with `/*` and end with `*/`. You must be careful about this to differentiate the changes to the code from the changes to documentation."
)


def make_context(
    diff,
    changed_files_importance=None,
    changed_method_summaries=None,
    changed_class_functionality_summary=None,
    associated_issues=None,
    associated_pull_requests=None,
):
    str = ""
    str += f"The Git diff:\n{diff}\n\n"
    if changed_files_importance:
        str += f"Changed files relative importance:\n{changed_files_importance}\n\n"
    if changed_method_summaries:
        str += (
            f"This is the changed method(s) summaries:\n{changed_method_summaries}\n\n"
        )
    if changed_class_functionality_summary:
        str += f"Here is the changed class(es) functionality summary:\n{changed_class_functionality_summary}\n\n"
    if associated_issues:
        str += f"Here is the associated issue(s) on the repo:\n{associated_issues}\n\n"
    if associated_pull_requests:
        str += f"Here is the associated pull request(s) on the repo:\n{associated_pull_requests}\n\n"
    return str
