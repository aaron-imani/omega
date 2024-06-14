import sys

from langchain.memory import ChatMessageHistory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from termcolor import colored

if ".." not in sys.path:
    sys.path.append("..")

from common.model_loader import model
from OMG_based.Agent_tools import *

issue_collecting_tool = IssueCollectingTool()
pull_request_collecting_tool = PullRequestCollectingTool()
important_files_tool = ImportantFileTool()

tmpl = (
    "You are a senior Java developer with extensive experience in Git."
    "You will be given contextual information about a commit, and your task is to answer questions you will be asked."
)

commit_info = (
    "START OF COMMIT CONTEXT\n\n"
    "The Git diff:\n{git_diff}\n\n"
    # "Changed files relative importance:\n{changed_files_importance}\n\n"
    # "This is the changed method(s) summaries:\n{changed_method_summaries}\n\n"
    # "Here is the changed class(es) functionality summary:\n{changed_class_functionality_summary}\n\n"
    # "Here is the associated issue(s):\n{associated_issues}\n\n"
    # "Here is the associated pull request(s):\n{associated_pull_requests}\n\n"
    "END OF COMMIT CONTEXT\n\n"
    "Now, I will start asking questions about this commit."
)


user_prompt = "Question: {question}"

commit_url = (
    "https://github.com/apache/ant/commit/5e099552e5af434568a4294cf7bcebb732cd3bfa"
)
# commit_url = (
#     "https://github.com/apache/ant/commit/cfa604fd9941bf59641e989306c4356dab156015"
# )
commit_context = {
    "git_diff": git_diff_tool.invoke(commit_url),
    # "changed_files_importance": important_files_tool.invoke(commit_url),
    # "changed_method_summaries": code_summarization_tool.invoke(commit_url),
    # "changed_class_functionality_summary": code_understanding_tool.invoke(commit_url),
    # "associated_issues": issue_collecting_tool.invoke(commit_url),
    # "associated_pull_requests": pull_request_collecting_tool.invoke(commit_url),
}

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", tmpl),
        ("human", commit_info),
        (
            "ai",
            "Sure, I can help you with that. Please go ahead and ask your question.",
        ),
        MessagesPlaceholder("chat_history"),
        ("human", user_prompt),
    ]
)
history = ChatMessageHistory()

chain = prompt | model
chain_with_message_history = RunnableWithMessageHistory(
    chain,
    lambda session_id: history,
    input_messages_key="question",
    history_messages_key="chat_history",
)
# history.add_user_message(
#     (
#         "ADDITIONAL COMMIT CONTEXT\n\n"
#         # "The Git diff:\n{git_diff}\n\n"
#         f"Changed files relative importance:\n{important_files_tool.invoke(commit_url)}\n\n"
#         f"Changed method(s) summaries:\n{code_summarization_tool.invoke(commit_url)}\n\n"
#         f"Changed class(es) functionality summary:\n{code_understanding_tool.invoke(commit_url)}\n\n"
#         f"Associated issue(s):\n{issue_collecting_tool.invoke(commit_url)}\n\n"
#         f"Associated pull request(s):\n{pull_request_collecting_tool.invoke(commit_url)}\n\n"
#         # "END OF COMMIT CONTEXT\n\n"
#         "Consider these in your future answers."
#     )
# )
# history.add_ai_message("I will!")

q = input(colored("Ask a question: ", "light_yellow"))
while q != "q":
    commit_context.update({"question": q})
    # response = agent.predict(**commit_context)
    response = chain_with_message_history.invoke(
        commit_context, {"configurable": {"session_id": "unused"}}
    )
    # print(history.messages)
    print(colored("Answer:", "green"), response.content)
    q = input(colored("Ask a question: ", "light_yellow"))
