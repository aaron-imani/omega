import os
import sys

sys.path.extend([".."])
from argparse import ArgumentParser
from pathlib import Path

from common.model_loader import processed_model_name

parser = ArgumentParser()
parser.add_argument(
    "commits_path",
    default="../evaluation/evaluation_preprocessed.xlsx",
    help="Path to the commits file",
    type=str,
)
parser.add_argument(
    "mode",
    help="Mode of the agent",
    choices=["random", "row_number", "hm", "all"],
    default="random",
)
parser.add_argument(
    "-o",
    "--output-dir",
    help="Path to save the output",
    default=Path(__file__).parent.resolve() / "csv" / processed_model_name,
)
parser.add_argument(
    "--prompt",
    help="Prompting technique",
    choices=["zero-shot", "react", "react-json", "in-context", "original"],
    default="in-context",
    required=False,
)
parser.add_argument(
    "--verbose", help="Verbose mode", action="store_true", default=False, required=False
)
parser.add_argument(
    "--reset",
    help="Restarts the commit message generation",
    action="store_true",
    default=False,
    required=False,
)
parser.add_argument(
    "--reset-cache",
    nargs="+",
    help="Resets the cache for a specific command",
    required=False,
)
parser.add_argument(
    "-n",
    "--file-name",
    help="Name of the output file",
    default="output.csv",
    required=False,
)
parser.add_argument(
    "-e",
    "--explain-diff",
    choices=["None", "zeroshot", "interactive", "fewshot"],
    default="None",
    required=False,
)


args = parser.parse_args()

if args.reset_cache:
    import cache_manager

    for command in args.reset_cache:
        cache_manager.delete_execution_value(command)

# Make the output folder if it doesn't exist
if not os.path.exists(args.output_dir):
    os.makedirs(args.output_dir)

output_path = os.path.join(args.output_dir, args.file_name)

os.environ["DIFF_EXPLANATION_METHOD"] = args.explain_diff


import agent_chains
import agent_chains.incontext
import agent_chains.original
import agent_chains.react_json
import pandas as pd
from Agent_tools import *
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_community.callbacks import get_openai_callback
from langchain_community.llms.ollama import OllamaEndpointNotFoundError
from output_parsers import *
from termcolor import colored
from tqdm import tqdm
from utils import format_output

from common.model_loader import base_url
from common.model_loader import model as llm
from evaluation.evaluate_cm import evaluate_machine_generated_text

CONTEXT_LENGTH = 8192

issue_collecting_tool = IssueCollectingTool()
pull_request_collecting_tool = PullRequestCollectingTool()
important_files_tool = ImportantFileTool()

tools = [
    git_diff_tool,
    commit_type_classifier_tool,
    code_summarization_tool,
    code_understanding_tool,
    issue_collecting_tool,
    pull_request_collecting_tool,
    important_files_tool,
]


# print("Using diff summary:", os.getenv("USE_DIFF_SUMMARY"))

# name_suffix = "-" + args.suffix if args.suffix else ""
prompting_technique = args.prompt
verbose = args.verbose if args.mode == "all" else True

if args.commits_path.endswith(".xlsx"):
    gt = pd.read_excel(args.commits_path)
    # Rename CMG to OMG if it is not already
    if "CMG" in gt.columns:
        gt.rename(columns={"CMG": "OMG"}, inplace=True)
elif args.commits_path.endswith(".csv"):
    gt = pd.read_csv(args.commits_path)
    # Rename CMG to OMG if it is not already
    if "CMG" in gt.columns:
        gt.rename(columns={"CMG": "OMG"}, inplace=True)

if prompting_technique == "original":
    agent_chain = agent_chains.original.get_agent_chain(verbose)

elif prompting_technique == "react-json":
    agent_chain = agent_chains.react_json.get_agent_chain(verbose)

elif prompting_technique == "react":
    agent = create_react_agent(
        llm, tools, prompt, output_parser=RobustReActSingleInputOutputParser()
    )
    # With history
    # agent_chain = AgentExecutor(agent=agent, tools=tools, memory=memory,
    #                             handle_parsing_errors=True,
    #                             verbose=True)

    # Without history
    agent_chain = AgentExecutor(
        agent=agent, tools=tools, handle_parsing_errors=True, verbose=args.verbose
    )
elif prompting_technique == "in-context":
    agent_chain = agent_chains.incontext.get_agent_chain()
    name_suffix = "-incontext"
else:
    # from zeroshot_prompt import zeroshot_parser, retry_parser
    tmpl = """A git diff lists each changed (or added or deleted) Java source code file information in the following format:
* `--- a/file.java\n+++ b/file.java`: indicating that in the following code lines, lines prefixed with `---` are lines that only occur in the old version `a/file.java`,
i.e. are deleted in the new version `b/file.java`, and lines prefixed with `+++` are lines that only occur in the new version `b/file.java`,
i.e. are added to the new version `b/file.java`. Code lines that are not prefixed with `---` or `+++` are lines that occur in both versions, i.e. are unchanged and only listed for better understanding.
* The code changes are then shown as a list of hunks, where each hunk consists of:
  * `@@ -5,8 +5,9 @@`: a hunk header that states that the hunk covers the code lines 5 to 5 + 8 in the old version and code lines 5 to 5 + 9 in the new version.
  * then those code lines are listed with the prefix `---` for deleted lines, `+++` for added lines, and no prefix for unchanged lines, as described above. 
  
You are an AI model that specializes in generating high quality commit messages. You are given an input as a git diff, and you should generate a commit message of high quality for it.

Your commit message should be in the following format:

```json
{{
    "type": "the type of the commit",
    "subject": "the subject of the commit message",
    "body": "the body of the commit message"
}}

- The subject must be at most 72 characters. It should contain a brief summary of the changes introduced by the commit. You must use **imperative mood** to write the subject. Do not repeat the type in the subject.
- The body is optional and can be used to provide additional relevant contextual information and/or justifications/motivations behind the commit. If you do not provide a body, you should use an empty string for its value. You are strongly encouraged to provide a body based on all your observations. 
- Body should not include code blocks or snippets. 
- Keep body as consise as possible and avoid generic useless statements.
- The type is the software maintenance activity type of the commit that should be determined based on the changes introduced by the commit. 
- Type can only be one of the following: feat, fix, style, refactor.  Do not write anything else. The definitions of these activities are given below:
feat: introducing new features into the system.
fix: fixing faults or software bugs.
style: code format changes such as fixing redundant white-space, adding missing semi-colons, and similar changes.
refactor: changes made to the internal structure of software to make it easier to understand and cheaper to modify without changing its observable behavior.
- Choose type very carefully and do not repeat type in the subject. Do not write anything other than the four types mentioned above.

Here is the git diff for the commit:
{input}

subject: $subject
body: $body
type: $type

Your commit message as a JSON blob:
"""

    prompt = PromptTemplate(input_variables=["input"], template=tmpl)
    agent_chain = prompt | llm
    name_suffix = "-zeroshot"


def print_results(human_cm, omg_cm, formatted):
    print(colored("Human-written commit message:", "green"))
    print(human_cm, end="\n\n")
    print(colored("OMG Commit Message:", "green"))
    print(omg_cm, end="\n\n")
    print(colored("AMG Commit Message:", "green"))

    # if prompting_technique == "react-json":
    #     formatted = response["output"]
    # elif prompting_technique == "react":
    #     formatted = format_output(response["output"])
    # elif prompting_technique == "original":
    #     formatted = response["output"]
    # else:
    #     formatted = format_output(response.content)

    print(formatted, end="\n\n")
    evaluation = evaluate_machine_generated_text(omg_cm, formatted)
    print(
        colored("Evaluation", "yellow"), end="\n------------------------------------\n"
    )
    print("BLEU:", evaluation.bleu)
    print("ROUGE:", evaluation.rougeL)
    print("METEOR:", evaluation.meteor)


def generate_cm(commit_url, verbose=True):
    if verbose:
        print(colored("URL:", "green"), commit_url, end="\n\n")
        print(
            colored(
                "Now, let's see how this agent performs on this commit message...",
                "yellow",
            )
        )

    try:
        if os.getenv("USE_OPEN_SOURCE") == "0":
            with get_openai_callback() as cb:
                if verbose:
                    print(cb)
                response = agent_chain.invoke({"input": commit_url})
        else:
            response = agent_chain.invoke({"input": commit_url})
            if (
                isinstance(response, dict)
                and response["output"]
                == "Agent stopped due to iteration limit or time limit."
            ):
                print(
                    colored(
                        "Agent stopped due to iteration limit or time limit.", "red"
                    )
                )
                response["output"] = "TOOL ERROR"

        return response

    except OllamaEndpointNotFoundError:
        if verbose:
            print("Model is not available. Proceeding to download the model.")
        from ollama_python.endpoints import ModelManagementAPI

        api = ModelManagementAPI(base_url=base_url + "/api")
        result = api.pull(name=os.getenv("MODEL_NAME"))
        if verbose:
            print(result.status)

        response = agent_chain.invoke({"input": commit_url})
        return response
    except Exception as e:
        print(colored(f"An error occurred: {e}", "red"))
        if prompting_technique != "zero-shot":
            return {"output": "TOOL ERROR"}
        else:
            return "TOOL ERROR"


if args.mode != "all":
    import time

    if args.mode == "random":
        random_row = gt.sample()
    elif args.mode == "hm":
        random_row = gt[gt["HM"] == input("Enter human-written commit message: ")]
    else:
        random_row = gt.iloc[int(input("Enter row number: "))]

    try:
        test_commit_url = (
            f"https://github.com/"
            + random_row["project"].values[0]
            + f"/commit/"
            + random_row["commit"].values[0]
        )
    except AttributeError:
        test_commit_url = (
            f"https://github.com/"
            + random_row["project"]
            + f"/commit/"
            + random_row["commit"]
        )

    cur_time = time.time()
    if prompting_technique == "in-context":
        response = agent_chain.invoke(
            {
                "git_diff": git_diff_tool.invoke(test_commit_url),
                "changed_method_summaries": code_summarization_tool.invoke(
                    test_commit_url
                ),
                "changed_class_functionality_summary": code_understanding_tool.invoke(
                    test_commit_url
                ),
                "associated_issues": issue_collecting_tool.invoke(test_commit_url),
                "associated_pull_requests": pull_request_collecting_tool.invoke(
                    test_commit_url
                ),
                "changed_files_importance": important_files_tool.invoke(
                    test_commit_url
                ),
            }
        )
    elif prompting_technique == "zero-shot":
        diff = git_diff_tool.invoke(test_commit_url)
        response = generate_cm(diff)
    else:
        response = generate_cm(test_commit_url)

    print(colored("Commit URL:", "light_yellow"), test_commit_url)
    print(
        colored("Duration:", "light_yellow"),
        round(time.time() - cur_time, 2),
        "seconds",
    )
    # if verbose:
    #     print('Raw output:', response['output'], sep='\n')
    formatted = format_output(response.content)
    try:
        print_results(
            random_row["HM"].values[0], random_row["OMG"].values[0], formatted
        )
    except AttributeError:
        print_results(random_row["HM"], random_row["OMG"], formatted)

else:
    if args.reset:
        generated_cms = gt.copy()
        generated_cms["AMG"] = ""
    else:
        try:
            previous_generation = pd.read_csv(output_path)
            generated_cms = gt.copy()
            generated_cms["AMG"] = previous_generation["AMG"].fillna(value="")
            if "CMG" in previous_generation.columns:
                generated_cms.rename(columns={"CMG": "OMG"}, inplace=True)
        except FileNotFoundError:
            generated_cms = gt.copy()
            generated_cms["AMG"] = ""

    if prompting_technique not in ["zero-shot", "in-context"]:
        for index, row in tqdm(
            generated_cms.iterrows(),
            total=generated_cms.shape[0],
            desc="Generating commit messages",
        ):
            try:
                if not row["AMG"] == "":
                    continue

                test_commit_url = (
                    f"https://github.com/"
                    + row["project"]
                    + f"/commit/"
                    + row["commit"]
                )

                # For important files ablation study
                # important_files = important_files_tool.invoke(test_commit_url)
                # if important_files == "There is only one changed file in this commit. There was no need to use this tool.":
                #     continue

                # For PR and Issues ablation study
                # issues = issue_collecting_tool.invoke(test_commit_url)
                # prs = pull_request_collecting_tool(test_commit_url)
                # if issues.startswith('There is no') and prs.startswith('There is no'):
                #     continue

                # For class summaries ablation study
                # class_sum = code_understanding_tool.invoke(test_commit_url)
                # if class_sum == "The code changes in this git diff are not located within any class body. They might be either import statement or comment changes.":
                #     continue

                # For method summaries ablation study
                # method_sum = code_summarization_tool.invoke(test_commit_url)
                # if method_sum.startswith('The code changes in this git diff are not located within any method body.'):
                #     continue

                response = generate_cm(test_commit_url, args.verbose)
                if response["output"] == "":
                    response["output"] = "TOOL ERROR"

                generated_cms.at[index, "AMG"] = response["output"]
                # print('Index:', index)
                print_results(row["HM"], row["OMG"])
            except KeyboardInterrupt:
                break
    elif prompting_technique == "in-context":
        for index, row in tqdm(
            generated_cms.iterrows(),
            total=generated_cms.shape[0],
            desc="Generating commit messages",
        ):
            try:
                if row["AMG"] != "":
                    continue

                test_commit_url = (
                    f"https://github.com/"
                    + row["project"]
                    + f"/commit/"
                    + row["commit"]
                )
                response = agent_chain.invoke(
                    {
                        # "git_diff": git_diff_tool.invoke(test_commit_url),
                        "git_diff": highlight_git_diff(
                            git_diff_tool.invoke(test_commit_url)
                        ),
                        "changed_method_summaries": code_summarization_tool.invoke(
                            test_commit_url
                        ),
                        "changed_class_functionality_summary": code_understanding_tool.invoke(
                            test_commit_url
                        ),
                        "associated_issues": issue_collecting_tool.invoke(
                            test_commit_url
                        ),
                        "associated_pull_requests": pull_request_collecting_tool.invoke(
                            test_commit_url
                        ),
                        "changed_files_importance": important_files_tool.invoke(
                            test_commit_url
                        ),
                    }
                )
                formatted = format_output(response.content)
                generated_cms.at[index, "AMG"] = formatted
                print("Index:", index)
                print_results(row["HM"], row["OMG"], formatted)
            except KeyboardInterrupt:
                break
    else:
        for index, row in tqdm(
            generated_cms.iterrows(),
            total=generated_cms.shape[0],
            desc="Generating commit messages",
        ):
            if row["AMG"] != "":
                continue

            test_commit_url = (
                f"https://github.com/" + row["project"] + f"/commit/" + row["commit"]
            )
            diff = get_git_diff_from_commit_url(test_commit_url)
            response = generate_cm(diff, args.verbose)
            generated_cms.at[index, "AMG"] = format_output(response)
            print_results(row["HM"], row["OMG"])

    generated_cms.to_csv(output_path, index=False)

    generated_cms = generated_cms[generated_cms["AMG"] != ""]
    evaluation = evaluate_machine_generated_text(
        generated_cms["OMG"].astype(str).values, generated_cms["AMG"].astype(str).values
    )
    print(
        colored("Evaluation", "yellow"), end="\n------------------------------------\n"
    )
    print("BLEU:", evaluation.bleu)
    print("ROUGE-L:", evaluation.rougeL)
    print("METEOR:", evaluation.meteor)
