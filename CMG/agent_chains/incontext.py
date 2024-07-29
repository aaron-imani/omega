import openai
from langchain.prompts import ChatPromptTemplate

from common.model_loader import is_instruction_tuned
from common.model_loader import model as llm

# Original template
# tmpl = """A git diff lists each changed (or added or deleted) Java source code file information in the following format:
# * `--- a/file.java\n+++ b/file.java`: indicating that in the following code lines, lines prefixed with `---` are lines that only occur in the old version `a/file.java`,
# i.e. are deleted in the new version `b/file.java`, and lines prefixed with `+++` are lines that only occur in the new version `b/file.java`,
# i.e. are added to the new version `b/file.java`. Code lines that are not prefixed with `---` or `+++` are lines that occur in both versions, i.e. are unchanged and only listed for better understanding.
# * The code changes are then shown as a list of hunks, where each hunk consists of:
#   * `@@ -5,8 +5,9 @@`: a hunk header that states that the hunk covers the code lines 5 to 5 + 8 in the old version and code lines 5 to 5 + 9 in the new version.
#   * then those code lines are listed with the prefix `---` for deleted lines, `+++` for added lines, and no prefix for unchanged lines, as described above.

# You are an AI model that specializes in generating high quality commit messages. You will be given contextual information about a commit, and your task is to generate a commit message of high quality for it.

# ANSWERING FORMAT AND INSTRUCTIONS
# Your commit message should be in the following format:

# ```json
# {{
#     "type": "the type of the commit",
#     "subject": "the subject of the commit message",
#     "body": "the body of the commit message"
# }}

# - The subject must be at most 72 characters. It should contain a brief summary of the changes introduced by the commit. You must use **imperative mood** to write the subject. Do not repeat the type in the subject.
# - The body is optional and can be used to provide additional relevant contextual information and/or justifications/motivations behind the commit. If you do not provide a body, you should use an empty string for its value. You are strongly encouraged to provide a body based on all the provided context.
# - Body should not include code blocks or snippets.
# - Do not write generic/uniformative/useless sentences in body. Provide only important and relevant information.
# - The type is the software maintenance activity type of the commit that should be determined based on the commit changes, commit message body and subject. The type must be exactly one of the following: feat, fix, style, refactor.  No other values are acceptable. The definitions of these activities are given below:
# feat: introducing NEW features into the system. (feat is short for feature)
# fix: FIXING faults or software bugs.
# style: code FORMAT changes such as fixing redundant white-space, adding missing semi-colons, and similar changes.
# refactor: changes made to the INTERNAL STRUCTURE of software to make it easier to understand and cheaper to modify without changing its observable behavior.
# - Type should not be repeated in the subject. Remember, type should be determined based on the commit changes, commit message body and subject.
# """

# good_cm_criteria = (
#     "1. Rationality: reflects whether the commit message provides a logical explanation for the code change (Why information), and provides the commit type information.\n"
#     "2. Comprehensiveness: reflects whether the message describes a summary of what has been changed (What information) and also covers details (i.e., whether the commit message fails relevant imports to describe the code changes in a changed file.)\n"
#     "3. Conciseness: indicates whether the message conveys information succinctly, ensuring readability and quick comprehension.\n"
#     "4. Expressiveness: reflects whether the message content is grammatically correct and fluent.\n\n"
# )
# human_eval_criteria = (
#     "Overall, a good commit message must satisfy the following quality criteria:\n"
#     "1. Rationality: reflects whether the commit message provides a logical explanation behind the changes (reasons/motivations/justifications), and provides a correct software maintenance activity type.\n"
#     "2. Comprehensiveness: reflects whether the message describes a summary of all the changes and also covers details.\n"
#     "3. Conciseness: indicates whether the message conveys information concisely, ensuring readability and quick comprehension.\n"
#     "4. Expressiveness: reflects whether the message content is grammatically correct and fluently written.\n\n"
# )

# Original - Used For Survey
# answering_instructions = """ANSWERING FORMAT AND INSTRUCTIONS
# Your commit message should be in the following format:

# ```json
# {{
#     "type": "the type of the commit",
#     "subject": "the subject of the commit message",
#     "body": "the body of the commit message"
# }}

# - The subject must be at most 72 characters. It should contain a brief summary of the changes introduced by the commit. You must use **imperative mood** to write the subject. Do not repeat the type in the subject.
# - The body is optional and can be used to provide additional relevant contextual information and/or justifications/motivations behind the commit. If you do not provide a body, you should use an empty string for its value. You are strongly encouraged to provide a body based on all the provided context.
# - Body should not include code blocks or snippets.
# - Do not write generic/uniformative/useless sentences in body. Provide only important and relevant information.
# - The type is the software maintenance activity type of the commit that should be determined based on the commit changes, commit message body and subject. The type must be exactly one of the following: feat, fix, style, refactor.  No other values are acceptable. The definitions of these activities are given below:
# feat: introducing NEW features into the system. (feat is short for feature)
# fix: FIXING faults or software bugs.
# style: code FORMAT changes such as fixing redundant white-space, adding missing semi-colons, and similar changes.
# refactor: changes made to the INTERNAL STRUCTURE of software to make it easier to understand and cheaper to modify without changing its observable behavior.
# - Type should not be repeated in the subject. Remember, type should be determined based on the commit changes, commit message body and subject."""

# Modified - Used After Survey to make it more comprehensive
answering_instructions = """ANSWERING FORMAT AND INSTRUCTIONS
Your commit message must be in the following format:

```json
{{
    "type": "the type of the commit",
    "subject": "the subject of the commit message",
    "body": "the body of the commit message"
}}
```

- The subject must be at most 72 characters. It should contain a brief summary of the changes introduced by the commit. You must use **imperative mood** to write the subject in the present tense. Do not repeat the type in the subject.
- The body is optional but strongly recommended. It should comprehensively provide additional relevant contextual information about **all** the changes made and/or justifications/motivations behind them. It must be written as detailed as possible. If you do not provide a body, you should use an empty string for its value. You are strongly encouraged to provide a body based on all the provided context.
- Body should not include code blocks or snippets.
- Do not write generic/uniformative/useless sentences in body. Provide only important and relevant information.
- The type is the software maintenance activity type of the commit that should be determined based on the commit changes, commit message body and subject. The type must be exactly one of the following: feat, fix, style, refactor.  No other values are acceptable. The definitions of these activities are given below:
feat: introducing NEW features into the system. (feat is short for feature)
fix: FIXING faults or software bugs.
style: code FORMAT changes such as fixing redundant white-space, adding missing semi-colons, and similar changes.
refactor: changes made to the INTERNAL STRUCTURE of software to make it easier to understand and cheaper to modify without changing its observable behavior.
- Type should not be repeated in the subject. Remember, type should be determined based on the commit changes, commit message body and subject.
"""

# answering_instructions = good_cm

if is_instruction_tuned:
    system_msg = (
        "You are an AI model that specializes in generating high quality commit messages. "
        "You will be given contextual information about a commit, and your task is to generate a commit message of high quality for it.\n\n"
        f"{answering_instructions}"
    )
    user_prompt = (
        "START OF COMMIT CONTEXT\n\n"
        "The Git diff:\n{git_diff}\n\n"
        "Changed files relative importance:\n{changed_files_importance}\n\n"
        "This is the changed method(s) summaries:\n{changed_method_summaries}\n\n"
        "Here is the changed class(es) functionality summary:\n{changed_class_functionality_summary}\n\n"
        "Here is the associated issue(s):\n{associated_issues}\n\n"
        "Here is the associated pull request(s):\n{associated_pull_requests}\n\n"
        # f"{answering_instructions}\n\n"
        "END OF COMMIT CONTEXT\n\nYour commit message: "
    )
    prompt = ChatPromptTemplate.from_messages(
        [("system", system_msg), ("human", user_prompt)]
    )
    roles = ["system", "human"]

else:
    system_msg = "You are an AI model that specializes in generating high quality commit messages. "
    user_prompt = (
        "START OF COMMIT CONTEXT\n\n"
        "The Git diff:\n{git_diff}\n\n"
        "Changed files relative importance:\n{changed_files_importance}\n\n"
        "This is the changed method(s) summaries:\n{changed_method_summaries}\n\n"
        "Here is the changed class(es) functionality summary:\n{changed_class_functionality_summary}\n\n"
        "Here is the associated issue(s):\n{associated_issues}\n\n"
        "Here is the associated pull request(s):\n{associated_pull_requests}\n\n"
        f"{answering_instructions}\n\n"
        "END OF COMMIT CONTEXT\n\nYour commit message: "
    )
    roles = ["human", "ai", "human"]
    prompt = ChatPromptTemplate.from_messages(
        [
            ("human", system_msg),
            (
                "ai",
                "Please send the commit context and I will write a high quality commit message for you.",
            ),
            ("human", user_prompt),
        ]
    )


def get_agent_chain():
    # Uncomment for CodeQwen
    # agent_chain = prompt | llm.bind(max_tokens=200, frequency_penalty=0.5)
    agent_chain = prompt | llm.bind(max_tokens=500)
    return agent_chain
