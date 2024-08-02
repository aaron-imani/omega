import os
import sys

from openai import BadRequestError

sys.path.extend([".."])
from argparse import ArgumentParser
from pathlib import Path

import jsonlines

from common.diff_narrator import DiffNarrator
from common.information_card import diff_reading_instruction, make_commit_context
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
    choices=["react-json", "in-context", "original"],
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
    "-f",
    "--fidex",
    action="store_true",
)
parser.add_argument(
    "--dn",
    "--narrate-diff",
    action="store_true",
)
parser.add_argument(
    "-r",
    "--reference-column",
    help="Name of the column containing the groundtruth commit messages",
    default="OMG",
    required=False,
)
parser.add_argument(
    "--line-type",
    action="store_true",
)


args = parser.parse_args()

narrator = DiffNarrator(args.line_type)

if args.reset_cache:
    import cache_manager

    for command in args.reset_cache:
        cache_manager.delete_execution_value(command)

# Make the output folder if it doesn't exist
if not os.path.exists(args.output_dir):
    os.makedirs(args.output_dir)

output_path = os.path.join(args.output_dir, args.file_name)

os.environ["USE_FIDEX"] = "TRUE" if args.fidex else "FALSE"


import agent_chains
import pandas as pd

# import agent_chains.incontext
# import agent_chains.original
# import agent_chains.react_json
from agent_chains import incontext, original, react_json
from Agent_tools import *
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_community.callbacks import get_openai_callback
from langchain_community.llms.ollama import OllamaEndpointNotFoundError
from output_parsers import *
from termcolor import colored
from tqdm import tqdm
from utils import format_output

from common import log_config
from common.model_loader import base_url
from common.model_loader import model as llm
from evaluation.evaluate_cm import evaluate_generation, evaluate_machine_generated_text

logger = log_config.get_logger("AMG")

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
elif prompting_technique == "in-context":
    agent_chain = incontext.get_agent_chain()
    name_suffix = "-incontext"


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
    return evaluation


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


def get_commit_context(commit_url):
    diff = git_diff_tool.invoke(commit_url)

    if args.dn:
        diff = diff + "\n\n" + narrator.get_narrative(diff)
    return {
        "git_diff": diff,
        "changed_method_summaries": code_summarization_tool.invoke(commit_url),
        "changed_class_functionality_summary": code_understanding_tool.invoke(
            commit_url
        ),
        "associated_issues": issue_collecting_tool.invoke(commit_url),
        "associated_pull_requests": pull_request_collecting_tool.invoke(commit_url),
        "changed_files_importance": important_files_tool.invoke(commit_url),
    }


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
        context = get_commit_context(test_commit_url)
        logger.debug(incontext.prompt.format(**context))
        response = agent_chain.invoke(context)
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
    logs_folder = Path(__file__).parent.resolve() / "logs" / processed_model_name
    if not os.path.exists(logs_folder):
        os.makedirs(logs_folder)
    output_file_name = output_path.split("/")[-1].split(".")[-2]
    msgs_path = logs_folder / f"{output_file_name}.jsonl"
    logs = []
    if args.reset:
        logs_mode = "w"
        generated_cms = gt.copy()
        generated_cms["AMG"] = ""

    else:
        logs_mode = "a"
        try:
            previous_generation = pd.read_csv(output_path)
            generated_cms = gt.copy()
            generated_cms["AMG"] = previous_generation["AMG"].fillna(value="")
            if "CMG" in previous_generation.columns:
                generated_cms.rename(columns={"CMG": "OMG"}, inplace=True)
            for col in previous_generation.columns:
                if col not in generated_cms.columns:
                    generated_cms[col] = previous_generation[col].fillna(value="")
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
                print_results(row["HM"], row[args.reference_column], response["output"])
            except KeyboardInterrupt:
                break

    elif prompting_technique == "in-context":
        prompt = agent_chains.incontext.prompt
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
                context = get_commit_context(test_commit_url)
                for k, v in context.items():
                    generated_cms.at[index, k] = v

                logger.debug(context["git_diff"])
                try:
                    response = agent_chain.invoke(context)
                except BadRequestError as e:
                    body = e.body["message"]
                    if body.startswith("This model's maximum context"):
                        generated_cms.at[index, "AMG"] = ""
                        continue

                messages = prompt.format_messages(**context)
                roles = incontext.roles
                messages = [
                    {"role": roles[i], "content": message.content}
                    for i, message in enumerate(messages)
                ]
                messages.append({"role": "assistant", "content": response.content})
                logs.append(messages)
                formatted = format_output(response.content)

                generated_cms.at[index, "AMG"] = formatted

                print("Index:", index)
                print(colored("Commit URL:", "green"), test_commit_url)
                evaluation = print_results(
                    row["HM"], row[args.reference_column], formatted
                )
                generated_cms.at[index, "AMG_BLEU"] = evaluation.bleu
                generated_cms.at[index, "AMG_ROUGE"] = evaluation.rougeL
                generated_cms.at[index, "AMG_METEOR"] = evaluation.meteor

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
    print(f'Wrote the results to "{output_path}"')
    with jsonlines.open(str(msgs_path), logs_mode) as writer:
        writer.write_all(logs)

    evaluate_generation(output_path, reference_cols=["OMG"], prediction_col="AMG")

    # generated_cms = generated_cms[generated_cms["AMG"] != ""]
    # evaluation = evaluate_machine_generated_text(
    #     generated_cms[args.reference_column].astype(str).values,
    #     generated_cms["AMG"].astype(str).values,
    # )
    # print(
    #     colored("Evaluation", "yellow"), end="\n------------------------------------\n"
    # )
    # print("BLEU:", evaluation.bleu)
    # print("ROUGE-L:", evaluation.rougeL)
    # print("METEOR:", evaluation.meteor)
