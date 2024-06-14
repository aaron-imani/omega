import logging
from langchain.agents.output_parsers.react_single_input import ReActSingleInputOutputParser
from langchain.agents.output_parsers.json import JSONAgentOutputParser
import re
from typing import Union

from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers.json import parse_json_markdown
from utils import format_output
logger = logging.getLogger(__name__)


FINAL_ANSWER_ACTION = "Final Answer:"
MISSING_ACTION_AFTER_THOUGHT_ERROR_MESSAGE = (
    "Invalid Format: Missing 'Action:' after 'Thought:'. Please provide an action to take according to the answering template. Strictly follow the steps in the answering template."
)
MISSING_ACTION_INPUT_AFTER_ACTION_ERROR_MESSAGE = (
    "Invalid Format: Missing 'Action Input:' after 'Action:'. You should perform the same Action again by including the Action and then an Action Input. Make sure the Action value is the exact name of one of the provided tools."
)
FINAL_ANSWER_AND_PARSABLE_ACTION_ERROR_MESSAGE = (
    "Parsing LLM output produced both a final answer and a parse-able action:"
)
ACTION_IS_NONE_ERROR_MESSAGE = (
    "Invalid Format: Action cannot be 'None' or empty. If you are ready to send the final answer, please send it."
)
HALLUCINATION_ERROR_MESSAGE = (
    "Invalid Format: Hallucination detected. You have jumpted to an observation without following the step-by-step answering template. Please generate a Thought, Action, and Action Input in order to proceed. Do not output any more steps."
)

action_regex = re.compile(r"Action\s*\d*\s*:[\s]*(.*)", re.DOTALL)
action_input_regex = re.compile(r".*Input\s*\d*\s*:[\s]*(.*)", re.DOTALL)
valid_action_regex = re.compile(r"Action\s*\d*\s*:[\s]*(.*)\n.*Input\s*\d*\s*:[\s]*(.*)", re.DOTALL)

class RobustReActSingleInputOutputParser(ReActSingleInputOutputParser):
    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        includes_answer = re.search(r'({[^}]+})', text) or FINAL_ANSWER_ACTION in text
        # regex = (
        #     r"Action\s*\d*\s*:[\s]*(.*?)[\s]*Action\s*\d*\s*Input\s*\d*\s*:[\s]*(.*)"
        # )
        action_match = valid_action_regex.search(text)
        # action_match = re.search(regex, text, re.DOTALL)
        
        if text.find("Observation") != -1:
            raise OutputParserException(
                f"Could not parse LLM output: `{text}`",
                observation=HALLUCINATION_ERROR_MESSAGE,
                llm_output=text,
                send_to_llm=True,
            )
        
        if action_match:
            # if includes_answer:
            #     raise OutputParserException(
            #         f"{FINAL_ANSWER_AND_PARSABLE_ACTION_ERROR_MESSAGE}: {text}"
            #     )
            action = action_match.group(1).strip().strip('"')
            if action.find("None") != -1:
                # print("Caught None action")
                raise OutputParserException(
                f"Could not parse LLM output: `{text}`",
                observation=ACTION_IS_NONE_ERROR_MESSAGE,
                llm_output=text,
                send_to_llm=True,
            )
            action_input = action_match.group(2)
            tool_input = action_input.strip(" ")
            tool_input = tool_input.strip('"')
            # print('tool_input:', tool_input)

            return AgentAction(action, tool_input, text)

        elif includes_answer:
            return AgentFinish(
                {"output": format_output(text)}, text
            )

        action_match = action_regex.search(text)
        action_input_match = action_input_regex.search(text)

        if not action_match:
            raise OutputParserException(
                f"Could not parse LLM output: `{text}`",
                observation=MISSING_ACTION_AFTER_THOUGHT_ERROR_MESSAGE,
                llm_output=text,
                send_to_llm=True,
            )
        elif not action_input_match:
            action = action_match.group(1).strip().strip('"')
            # print("action:", action)
            if action.find("None") != -1:
                # print("Caught None action")
                raise OutputParserException(
                f"Could not parse LLM output: `{text}`",
                observation=ACTION_IS_NONE_ERROR_MESSAGE,
                llm_output=text,
                send_to_llm=True,
            )
            else:
                raise OutputParserException(
                    f"Could not parse LLM output: `{text}`",
                    observation=MISSING_ACTION_INPUT_AFTER_ACTION_ERROR_MESSAGE,
                    llm_output=text,
                    send_to_llm=True,
                )
        else:
            raise OutputParserException(f"Could not parse your output based on the answering template. Please follow the answering template and try again.", 
                                        obseration=f"Could not parse your previous step based on the answering template. Please follow the answering template and try again.", 
                                        llm_output=text, 
                                        send_to_llm=True)


class RobustJSONReACTParser(JSONAgentOutputParser):
    {
  "action": "Final Answer",
  "action_input": "Refactor: Simplify SSLUtils by removing default cipher suite filters and using Collections.emptyList() instead."
}
    def _verify_final_answer(self, text, response):
        if "type" not in response:
            raise OutputParserException(
                f"Could not parse LLM output: `{text}`",
                observation="Please provide the type of the output according to the initial guideline. The commit message should be presented as the value to the key 'action_input'.",
                llm_output=text,
                send_to_llm=True,
            )
        if "subject" not in response:
            raise OutputParserException(
                f"Could not parse LLM output: `{text}`",
                observation="subject is missing in the JSON blob. Please provide the Final Answer again by adding the subject according to the initial guideline.",
                llm_output=text,
                send_to_llm=True,
            )
    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        # if not text.strip().endswith('}'):
        #     text = text.strip() + "\n}\n"
        # print('\nRaw text:', text, sep='\n')
        # text = text.strip()
        # final_answer = text.split('Final Answer:')
        # json_str = None
        # if len(final_answer) > 1:
        #     final_answer = final_answer[1].strip()
        #     print('Raw Final Answer:', final_answer)
        #     match = re.search(r'{(.*?)}', final_answer, re.DOTALL)

        #     if match:
        #         json_str = match.group(1)
        #     else:
        #         return AgentFinish({"output": final_answer}, text)
            
        # if not json_str:
        json_str = re.search(r'(?s:.*)({(.*?)})', text, re.DOTALL)
        if not json_str:
            raise OutputParserException(
                f"Could not parse LLM output: `{text}`",
                observation="Could not find a JSON blob in your output. Please provide a JSON blob according to the answering template.",
                llm_output=text,
                send_to_llm=True,
            )
        # if isinstance(json_str, re.Match):
        response = parse_json_markdown(json_str.group(1))
        # else:
        #     response = parse_json_markdown(json_str)

        if not response:
            raise OutputParserException(
                f"Could not parse LLM output: `{text}`",
                observation="Could not find a valid JSON blob in your output. Please provide a JSON blob according to the answering template.",
                llm_output=text,
                send_to_llm=True,
            )
        if isinstance(response, list):
            # gpt turbo frequently ignores the directive to emit a single action
            logger.warning("Got multiple action responses: %s", response)
            response = response[0]

        if response.get('action','') == "Final Answer":
            final_answer = None
            if "action_input" in response:
                if response["action_input"] == "":
                    raise OutputParserException(
                        f"Could not parse LLM output: `{text}`",
                        observation="You have provided Final Answer without providing any value. Please provide the final answer according to the answering template.",
                        llm_output=text,
                        send_to_llm=True,
                    )
                final_answer = response["action_input"]

            elif "type" in response:
                if "subject" not in response:
                    raise OutputParserException(
                        f"Could not parse LLM output: `{text}`",
                        observation="subject is missing in the JSON blob. Please provide the Final Answer again by adding the subject according to the initial guideline.",
                        llm_output=text,
                        send_to_llm=True,
                    )
                
                response.pop("action")
                final_answer = response.copy()
            else:
                raise OutputParserException(
                    f"Could not parse LLM output: `{text}`",
                    observation="Incorrect JSON blob: The commit message should be presented as the value to the key 'action_input'.",
                    llm_output=text,
                    send_to_llm=True,
                )
            
            if not final_answer:
                raise OutputParserException(
                    f"Could not parse LLM output: `{text}`",
                    observation="Please provide the type of the output according to the initial guideline. The Final Answer should be provided as a JSON blob with the commit message as the value to the key 'action_input'.",
                    llm_output=text,
                    send_to_llm=True,
                )
            
            # self._verify_final_answer(text, final_answer)
            # return AgentFinish({"output": format_output(final_answer)}, text)
            return AgentFinish({"output": final_answer}, text)
        elif "type" in response:
            return AgentFinish({"output": format_output(response)}, text)
        else:
            if response.get('action','').find("None") != -1 or response.get('action','') == "":
                raise OutputParserException(
                    f"Could not parse LLM output: `{text}`",
                    observation=ACTION_IS_NONE_ERROR_MESSAGE,
                    llm_output=text,
                    send_to_llm=True,
                )
            return AgentAction(
                response["action"], response.get("action_input", {}), text
            )

if __name__ == '__main__':
    json_parser = RobustJSONReACTParser()
    string="""Raw text:  Thought: Based on the observation from the Changed method summarization tool, the commit adds a new test case for decoding URL-encoded keys in query parameters. This is a style change as it does not alter the existing functionality but rather enhances the test coverage of the codebase.

Action:
```
{
  "action": "Final Answer",
  "action_input": """""
    json_parser.parse(string)