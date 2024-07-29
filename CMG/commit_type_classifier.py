from langchain_core.prompts import ChatPromptTemplate

import CMG.cache_manager as cache_manager
from common.model_loader import is_instruction_tuned, model

# from langchain.llms.ollama import Ollama

instruction = """You should classify the git diff (code change) into one of the following four software maintenance activities: feat, fix, style, and refactor. The definitions of these activities are given below:

feat: introducing new features into the system.
fix: fixing faults or software bugs.
style: code format changes such as fixing redundant white-space, adding missing semi-colons etc.
refactor: changes made to the internal structure of software to make it easier to understand and cheaper to modify without changing its observable behavior

The git diff lists each changed (or added or deleted) Java source code file information in the following format:
* `--- a/file.java\n+++ b/file.java`: indicating that in the following code lines, lines prefixed with `---` are lines that only occur in the old version `a/file.java`,
i.e. are deleted in the new version `b/file.java`, and lines prefixed with `+++` are lines that only occur in the new version `b/file.java`,
i.e. are added to the new version `b/file.java`. Code lines that are not prefixed with `---` or `+++` are lines that occur in both versions, i.e. are unchanged and only listed for better understanding.
* The code changes are then shown as a list of hunks, where each hunk consists of:
* `@@ -5,8 +5,9 @@`: a hunk header that states that the hunk covers the code lines 5 to 5 + 8 in the old version and code lines 5 to 5 + 9 in the new version.
* then those code lines are listed with the prefix `---` for deleted lines, `+++` for added lines, and no prefix for unchanged lines, as described above.
         
Answering format: 
Software maintenance activity type: $TYPE 

$TYPE must be exactly one of "feat", "fix", "style", "refactor" based on their definitions. Do not include any other information in your answer. Only one type should be the answer. Use the one that best fits the changes in the git diff.
"""

if is_instruction_tuned:
    classifier_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", instruction),
            (
                "human",
                "Git diff:\n{git_diff}\n\nYour Answer: ",
            ),
        ]
    )
else:
    classifier_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "human",
                f"{instruction}\n\n" "Git diff:\n{git_diff}\n\nYour Answer: ",
            ),
        ]
    )


classifier = classifier_prompt | model.bind(max_tokens=20)


def classify_commit_type(commit_url):
    # if re.match(r"https?://github\.com/[^/]+/[^/]+/commit/[a-f0-9]+", git_diff_collector_output):
    #     return "The tool failed to work.\nReason: Commit URL is an invalid input for this tool. Please use this tool again by using a git diff with ```diff ...``` format as input parameter."
    # elif not re.search(r"File\s*:\s.+[\n\\n]Status\s*:\s*.+[\n\\n](.*[\n\\n]*)*", git_diff_collector_output):
    #     return f"\nInvalid Action Input: Please use this Action again and directly provide the entire value you got from GitDiffCollector instead of a placeholder like '{git_diff_collector_output}' as Action Input. The Action Input should match this format: 'File: ...\\nStatus: ...\\n```diff\\n...\\n```'. Use this Action again and correct your Action Input.\n"
    # elif not git_diff_collector_output.startswith('diff --git'):
    #     return f"Invalid Action Input: Please use this Action again and directly provide the entire value you got from the Git diff collector tool instead of a placeholder like '{git_diff_collector_output}' as Action Input. The Action Input should match this format: 'diff --git ...'.\n"
    # elif re.match(r'<.+>', git_diff_collector_output):
    #     return f"\nInvalid Action Input: Please use this tool again and provide the value you got from the Git diff collector tool instead of a placeholder like '{git_diff_collector_output}'. Use this Action again and correct your Action Input. Do not forget to use this tool in case you need to use Git diff collector again.\n"

    cached_diff = cache_manager.get_commit_data(commit_url, "git_diff")
    if not cached_diff:
        return "It seems like you have not observed the Git diff for this commit URL yet. Please use the Git diff collector tool to observe the Git diff for this commit URL first."
        # cached_class_sum += "\n\nNow, proceed to the next step by using other tools if needed. If you are done, you can proceed to generate the Final Answer."
        # return cached_class_sum

    # classifier_prompt_template = PromptTemplate(
    #     input_variables=["git_diff"], template=classifier_prompt
    # )
    # if os.getenv("USE_OPEN_SOURCE") == "0":
    #     tested_llm = ChatOpenAI(model=GPT_MODEL, temperature=0)
    #     cm_type = tested_llm.invoke([classifier_prompt_template.format(git_diff=cached_diff)]).content.strip()
    #     return cm_type
    #     # if cm_type == "invalid":
    #     #     return f"\nInvalid Action Input: Please use this Action again and directly provide the entire value you got from the Git diff collector tool instead of a placeholder like '{cached_diff}' as Action Input. The Action Input should match this format: 'diff --git ...'. Use this Action again and correct your Action Input.\n"

    #     # return f"\nThe software maintenance activity type of the commit is: '{cm_type}'. Remember to use this to write the type field of your final answer. Now, proceed with collecting other information that you need.\n"
    # else:
    #     tested_llm = ChatOllama(
    #         model=os.getenv("MODEL_NAME"), temperature=0, base_url=base_url
    #     )
    cached_type = cache_manager.get_execution_value(commit_url, "classify_commit_type")
    if cached_type:
        return cached_type

    cm_type = classifier.invoke({"git_diff": cached_diff})
    cm_type = cm_type.content.strip()
    cache_manager.store_execution_value(commit_url, "classify_commit_type", cm_type)
    # if cm_type == "invalid":
    #     return f"\nInvalid Action Input: Please use this Action again and directly provide the entire value you got from the Git diff collector tool instead of a placeholder like '{cached_diff}' as Action Input. The Action Input should match this format: 'diff --git ...'. Use this Action again and correct your Action Input.\n"
    return cm_type
    # return f"\nThe software maintenance activity type of the commit is: '{cm_type}'. Remember to use this to write the type field of your final answer. Now, proceed with collecting other information that you need.\n"
    # commit = get_commit_from_github(commit_url)
    # git_diff = get_patches(commit)


# git_diff_type_classifier = Tool(
#     name = "The classifier of git diff into software maintenance activities (commit type)",
#     func = classify_commit_type,
#     description = "useful when you need to identify the commit type (software maintenance activity) for a git diff. Input should be a git diff"
# )
if __name__ == "__main__":
    from Agent_tools import get_git_diff_from_commit_url

    commit_url = input("Enter commit URL here:\n")
    get_git_diff_from_commit_url(commit_url)
    print(classify_commit_type(commit_url))
