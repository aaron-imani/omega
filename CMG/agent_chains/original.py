from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate

from common.model_loader import completion_model

from .active_tools import tools

template_prefix = """You are given an input as a commit url, and you should generate a commit message of high quality for the git diff (code change) in it.
You should use a tool to collect the git diff in this commit url.

The git diff lists each changed (or added or deleted) Java source code file information in the following format:
* `--- a/file.java\\n+++ b/file.java`: indicating that in the following code lines, lines prefixed with `---` are lines that only occur in the old version `a/file.java`,
i.e. are deleted in the new version `b/file.java`, and lines prefixed with `+++` are lines that only occur in the new version `b/file.java`,
i.e. are added to the new version `b/file.java`. Code lines that are not prefixed with `---` or `+++` are lines that occur in both versions, i.e. are unchanged and only listed for better understanding.
* The code changes are then shown as a list of hunks, where each hunk consists of:
  * `@@ -5,8 +5,9 @@`: a hunk header that states that the hunk covers the code lines 5 to 5 + 8 in the old version and code lines 5 to 5 + 9 in the new version.
  * then those code lines are listed with the prefix `---` for deleted lines, `+++` for added lines, and no prefix for unchanged lines, as described above.

A commit message consists of a header (commit type, and subject) and a body in the following structure:

<type>: <description>
<body>

The type and subject in the header are mandatory.
The body is optional.

You should use a tool to identify the commit type.

The description (72 characters max) contains succinct summary of the git diff. Please use the imperative mood to write the subject in present tense.

The body may be provided after the description, providing additional contextual information and/or justifications/motivations behind the git diff.

You should use a tool to collect the summaries that summarize the methods that are changed by the git diff, which may be helpful for generating description and body.

If you need the functionality summaries of the changed classes to get a bigger picture of the program context, you should use a tool to collect such information.

You should use a tool to identify if there is any associated issues.
The identified issue should be considered when generating description and body.

You should use a tool to identify associated pull requests, if any.
The identified pull request should be considered when generating description and body.

Think step-by-step about the git diff and the implicit context that can be deduced.

You have access to the following tools:
{tools}
"""

template_body = """

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question
"""

template_suffix = """

Begin!

Question: Can you generate a commit message of high quality for the following commit URL?
Commit URL: {input}

{agent_scratchpad}"""

tmpl = template_prefix + template_body + template_suffix
prompt = PromptTemplate(input_variables=["input", "agent_scratchpad"], template=tmpl)
agent = create_react_agent(
    completion_model,
    tools,
    prompt,
    # output_parser=RobustReActSingleInputOutputParser()
)


def get_agent_chain(verbose):
    return AgentExecutor(
        agent=agent, tools=tools, handle_parsing_errors=True, verbose=verbose
    )
