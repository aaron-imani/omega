from langchain.agents import AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from output_parsers import RobustJSONReACTParser

from common.model_loader import model as llm

from .active_tools import tools
from .json_chat_agent import create_json_chat_agent

system_msg = """You are an instruction-following assisstant. Answer my questions as best you can. To answer them, you only have access to the following tools:

{tools}

The way you use the tools is by specifying a json blob.
Specifically, this json should have a `action` key (with the name of the tool to use) and a `action_input` key (with the input to the tool going here). It also has a `thought` key, where you should write your thoughts on what you learned from the last observation(s) and how they would be useful in writing the final answer.

The only values that should be in the "action" field are: {tool_names}
Note that tool names are case sensitive. As such, you should use the tools with the exact same spelling and capitalization.
Once you have used a tool, you should never use that tool again. Remember your observation from each tool instead of using them again.
Once you are done with using tools, you should move on to the "Final Answer" section to generate the final answer.

The $JSON_BLOB should only contain a SINGLE action, do NOT return a list of multiple actions. Here is an example of a valid $JSON_BLOB:

```
{{
  "thought": (you should always think about what to do),
  "action": $TOOL_NAME,
  "action_input": $INPUT
}}
```

ALWAYS use one the following formats:

Option 1
----------------
Usecase: Use this option as many times as you need to gather enough information.
Template:
```
$JSON_BLOB
```
----------------

Option 2
----------------
Usecase: use this option when you know the final answer
Template:

Final Answer: the final answer is a commit message formatted as a json blob structured as below:

```
{{
    "report": $REPORT,
    "type": $SOFTWARE_MAINTENANCE_ACTIVITY_TYPE,
    "subject": $SUBJECT,
    "body": $BODY
}}
```

- $REPORT should contain a brief summary of how you arrived at the final answer. It should contain two information: what you learned from your last observation(s) + how they satisfy the requirements of the final answer + how they are used in writing different parts of the final answer.
- $SOFTWARE_MAINTENANCE_ACTIVITY_TYPE is the software maintenance activity type of the commit that must be determined by using the "Software maintenance activity type classifier tool". Any other values are unacceptable.
- $SUBJECT must be at most 72 characters. It should contain a brief summary of the changes introduced by the commit. You must use **imperative mood** to write the subject. Do not repeat the $SOFTWARE_MAINTENANCE_ACTIVITY_TYPE in the $SUBJECT.
- $BODY is optional (but stronly encouraged) and should be used to provide additional important contextual information and/or justifications/motivations behind the commit. If you do not provide a body, you should use an empty string for its value. 
"""

# Enhanced ReACT system message
# system_msg = """You are given an input as a commit url, and you should generate a commit message of high quality for the git diff (code change) in it.
# You should use a tool to collect the git diff in this commit url.

# The git diff lists each changed (or added or deleted) Java source code file information in the following format:
# * `--- a/file.java\\n+++ b/file.java`: indicating that in the following code lines, lines prefixed with `---` are lines that only occur in the old version `a/file.java`,
# i.e. are deleted in the new version `b/file.java`, and lines prefixed with `+++` are lines that only occur in the new version `b/file.java`,
# i.e. are added to the new version `b/file.java`. Code lines that are not prefixed with `---` or `+++` are lines that occur in both versions, i.e. are unchanged and only listed for better understanding.
# * The code changes are then shown as a list of hunks, where each hunk consists of:
#   * `@@ -5,8 +5,9 @@`: a hunk header that states that the hunk covers the code lines 5 to 5 + 8 in the old version and code lines 5 to 5 + 9 in the new version.
#   * then those code lines are listed with the prefix `---` for deleted lines, `+++` for added lines, and no prefix for unchanged lines, as described above.

# A commit message consists of a header (commit type, and subject) and a body in the following structure:

# <type>: <description>
# <body>

# The type and subject in the header are mandatory.
# The body is optional.

# You should use a tool to identify the commit type.

# The description (72 characters max) contains succinct summary of the git diff. Please use the imperative mood to write the subject in present tense.

# The body may be provided after the description, providing additional contextual information and/or justifications/motivations behind the git diff.

# You should use a tool to collect the summaries that summarize the methods that are changed by the git diff, which may be helpful for generating description and body.

# If you need the functionality summaries of the changed classes to get a bigger picture of the program context, you should use a tool to collect such information.

# You should use a tool to identify if there is any associated issues.
# The identified issue should be considered when generating description and body.

# You should use a tool to identify associated pull requests, if any.
# The identified pull request should be considered when generating description and body.

# Think step-by-step about the git diff and the implicit context that can be deduced.

# You have access to the following tools:
# {tools}

# The way you use the tools is by specifying a json blob.
# Specifically, this json should have a `action` key (with the name of the tool to use) and a `action_input` key (with the input to the tool going here). It also has a `thought` key, where you should write your thoughts on what you learned from the last observation(s) and how they would be useful in writing the final answer.

# The only values that should be in the "action" field are: {tool_names}
# Note that tool names are case sensitive. As such, you should use the tools with the exact same spelling and capitalization.
# Once you have used a tool, you should never use that tool again. Remember your observation from each tool instead of using them again.
# Once you are done with using tools, you should move on to the "Final Answer" section to generate the final answer.

# The $JSON_BLOB should only contain a SINGLE action, do NOT return a list of multiple actions. Here is an example of a valid $JSON_BLOB:

# ```
# {{
#   "action": "$TOOL_NAME",
#   "action_input": "$INPUT"
# }}
# ```

# ALWAYS use one the following formats:

# Option 1
# ----------------
# Usecase: Use this option as many times as you need to gather enough information.
# Template:
# ```
# Thought: (you should always think about what to do)
# $JSON_BLOB
# ```
# Expected output:
# Observation: <the action's output>
# ----------------

# Option 2
# ----------------
# Usecase: use this option when you know the final answer
# Template:
# Final Answer:
# ```
# {{
#   "thought": "I now know the final answer",
#   "action": "Final Answer",
#   "action_input": "Your final answer"
# }}
# ```

# """
human_msg = """
Question: Can you generate a high-quality commit message for this commit URL {input}?

Begin! Reminder to always use the `Final Answer` section when generating the final answer.
"""

# memory = ConversationBufferMemory()
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_msg),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", human_msg),
        MessagesPlaceholder("agent_scratchpad"),
    ]
)

tool_response_template = "Observation: {observation}"

agent = create_json_chat_agent(
    llm,
    tools,
    prompt,
    output_parser=RobustJSONReACTParser(),
    template_tool_response=tool_response_template,
)


def get_agent_chain(verbose):
    return AgentExecutor(
        agent=agent, tools=tools, handle_parsing_errors=True, verbose=verbose
    )
