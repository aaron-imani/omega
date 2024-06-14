# Enhanced
evaluation_criteria = (
    "A good commit message is structured as below:\n\n<type>: <subject>\n<body>\n\n"
    "<type> must be one of the following four software maintenance activities: feat, fix, style, and refactor. The definitions of these activities are given below:\n"
    "\tfeat: introducing new features into the system.\n"
    "\tfix: fixing faults or software bugs.\n"
    "\tstyle: code format changes such as fixing redundant white-space, adding missing semi-colons, etc.\n"
    "\trefactor: changes made to the internal structure of software to make it easier to understand and cheaper to modify without changing its observable behavior.\n"
    "<subject> must be roughly at most 72 characters. It should contain a brief summary of the changes introduced by the commit. You must use **imperative mood** to write it.\n"
    "<body> is optional but strongly recommended. It should comprehensively provide additional relevant contextual information about **all** the changes made and/or justifications/motivations behind them. <body> must be written as detailed as possible.\n"
    "Overall, a good commit message must satisfy the following quality criteria:\n"
    "1. Rationality: reflects whether the commit message provides a logical explanation for the code change (Why information), and provides the commit type information.\n"
    "2. Comprehensiveness: reflects whether the message describes a summary of what has been changed (What information) and also covers details (i.e., whether the commit message fails relevant imports to describe the code changes in a changed file.)\n"
    "3. Conciseness: indicates whether the message conveys information succinctly, ensuring readability and quick comprehension.\n"
    "4. Expressiveness: reflects whether the message content is grammatically correct and fluent.\n\n"
    "The commit message should be in the format of a JSON blob with the following keys: type, subject, and body. The value of each key should be a string. Empty value is allowed for the body key."
)

base_prompt = (
    "{evaluation_criteria}\n\nYou are given a partial commit message written as below:\n{{partial_cm}}\n\nGenerate the <{{cm_part}}> part of it for the following commit:\n\nSTART OF COMMIT CONTEXT{{context}}\n\nEND OF COMMIT CONTEXT\n\n"
    "\n* Only output the <{{cm_part}}> part without any irrelevant content."
).format(evaluation_criteria=evaluation_criteria)

player_system_prompt = (
    "You are a debater. Hello and welcome to the commit message generation competition, which will be conducted in a debate format. "
    "It is not necessary to fully agree with each other's perspectives, as the objective is to write the <{{cm_part}}> part of a good commit message.\n"
    "{evaluation_criteria}\nThe debate topic is stated as follows:\nGiven the partial commit message and the commit information, "
    "what should be written for the <{{cm_part}}> part of the commit message?\n\n"
    "Partial Commit Message:\n{{partial_cm}}\n\nSTART OF COMMIT CONTEXT{{context}}\n\nEND OF COMMIT CONTEXT\n\n"
).format(evaluation_criteria=evaluation_criteria)

moderator_system_prompt = (
    "You are a moderator. There will be {{num_debators}} debaters involved in a competition to properly complete a partial commit message. "
    "They will propose their answers and discuss their perspectives on the proper value for the <{{cm_part}}> part of the partial commit message "
    "that has been written for the following commit.\n\n"
    "Partial Commit Message:\n{{partial_cm}}\n\nSTART OF COMMIT CONTEXT\n\n{{context}}\n\nEND OF COMMIT CONTEXT\n\n"
    "At the end of each round, you will evaluate the candidate answers based on the following definition a good commit message:\n\n{evaluation_criteria}"
).format(evaluation_criteria=evaluation_criteria)

moderator_prompt = (
    "The {round_num} round of debate for both sides has ended. Below is the conversation between the debaters:\n\n{conversation}\n\n"
    "You, as the moderator, will evaluate both sides' answers and determine if there is a clear preference for the {cm_part} of the partial commit message. "
    "If there is, please summarize your reasons for supporting affirmative/negative side and select the final commit message accordingly. "
    "If not, the debate will continue to the next round. Now please output your decision in json format, with the format as follows: "
    '{{"Whether there is a preference": "Yes or No", "Supported Debator": "Name of the supported debater", "Reason": "Rigorous raesons based on the definition of a good commit message.", "selected_{cm_part}": ""}}.'
    "\n\nIMPORTANT: Please strictly output in JSON format, do not output irrelevant content."
)

affirmitive_prompt = 'You agree with {debater_name} which is: "{base_cm}". Restate the <{cm_part}> based on the initial guidelines of a good commit message and provide your reasons.'
negative_prompt = "{affirmitive_side_answer}\n\nYou disagree with my proposed <{cm_part}>. Provide your own <{cm_part}> and reasons."
debate_prompt = "{opponent_answer}\n\nDo you agree with my perspective? Please provide your reasons and a suggested <{cm_part}>."

judge_prompt_1 = (
    "Consider the following conversations in the current debate round:\n\n{conversation}\n\n"
    "What candidate <{cm_part}>s do we have? Present them without reasons."
)
judge_prompt_2 = (
    "Therefore, what should be written for the <{{cm_part}}> part of the commit message?\n\n"
    "Partial Commit Message:\n{{partial_cm}}\n\nSTART OF COMMIT CONTEXT{{context}}\n\nEND OF COMMIT CONTEXT\n\n"
    "Please summarize your reasons based on the good commit message guidelines and give the final <{{cm_part}}> that you think is suitable. "
    'Please output your answer in json format, with the format as follows: {{"Reason": "Rigorous reasons based on the evaluation criteria", "debate_{{cm_part}}": ""}}.\n\n'
    "IMPORTANT: Please strictly output in JSON format, do not output irrelevant content."
)

# git_diff = (
#     "```\n{diff}\n```\n"
#     "The git diff above lists each changed/added/deleted Java file information in the following format:\n"
#     "* `diff --git a/file.java\\n+++ b/file.java`: indicating that in the following lines, lines prefixed with `---` are lines that only occur in the old version `a/file.java`,"
#     "i.e. are deleted in the new version `b/file.java`, and lines prefixed with `+++` are lines that only occur in the new version `b/file.java`,"
#     "i.e. are added to the new version `b/file.java`. Code lines that are not prefixed with `---` or `+++` are lines that occur in both versions, i.e. are unchanged and only listed for better context."
#     "* The code changes are then shown as a list of hunks, where each hunk consists of:\n"
#     "* `@@ -5,8 +5,9 @@`: a hunk header that states that the hunk covers the lines 5 to 5 + 8 in the old version and code lines 5 to 5 + 9 in the new version.\n"
#     "* then those lines are listed with the prefix `---` for deleted lines, `+++` for added lines, and no prefix for unchanged lines, as described previously.\n"
#     "Java comment lines start with `//` and Javadocs start with `/*` and end with `*/`. You must be careful about this to differentiate the changes to the code from the changes to documentation."
# )

git_diff = "```\n{diff}\n```\n\n{summary}"


def get_partial_cm(cm_type=None, cm_subject=None):
    if cm_type and cm_subject:
        return f"{cm_type}: {cm_subject}\n<body>"
    elif cm_type:
        return f"{cm_type}: <subject>\n<body>"
    return "<type>: <subject>\n<body>"


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
