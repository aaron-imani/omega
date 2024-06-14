"""
MAD: Multi-Agent Debate with Large Language Models
Copyright (C) 2023  The MAD Team

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import argparse
import json
import os
import sys
import time

sys.path.extend([".."])
from datetime import datetime

from tqdm import tqdm

from evaluation.evaluate_cm import evaluate_machine_generated_text

# from langcodes import Language
from MAD_based.debate.incremental import Debate
from MAD_based.prompts import incremental as basic
from OMG_based.Agent_tools import *

# from OMG_based.gitdiff_summarizer import summarize_diff

# from OMG_based.utils import format_output


issue_collecting_tool = IssueCollectingTool()
pull_request_collecting_tool = PullRequestCollectingTool()
important_files_tool = ImportantFileTool()

# tools = [
#     git_diff_tool,
#     commit_type_classifier_tool,
#     code_summarization_tool,
#     code_understanding_tool,
#     important_files_tool,
#     issue_collecting_tool,
#     pull_request_collecting_tool,
# ]

# NAME_LIST=[
#     "Affirmative side",
#     "Negative side",
#     "Moderator",
# ]

NAME_LIST = [
    "Debater 1",
    "Debater 2",
    # "Debater 3",
    "Moderator",
]


def parse_args():
    parser = argparse.ArgumentParser(
        "", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("input_file", type=str, help="Input file path")
    parser.add_argument("output_dir", type=str, help="Output file dir")
    parser.add_argument("-n", "--csv-name", type=str, help="CSV file name")
    parser.add_argument(
        "-m",
        "--model-name",
        type=str,
        default="codellama:13b-instruct",
        help="Model name",
    )
    parser.add_argument(
        "-t", "--temperature", type=float, default=0, help="Sampling temperature"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose mode")
    parser.add_argument("-r", "--random-row", action="store_true", help="Random mode")
    parser.add_argument(
        "-s", "--commit-sha", help="Commit Sha of the commit to generate commit message"
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    current_script_path = os.path.abspath(__file__)

    config = json.load(open("utils/config4cm.json", "r"))

    save_file_dir = args.output_dir
    if not os.path.exists(save_file_dir):
        os.mkdir(save_file_dir)
    prompts_path = f"{save_file_dir}/config.json"

    if args.input_file.endswith(".txt"):
        input = open(args.input_file, "r").read()
        config["diff"] = input
        # config['evaluation_criteria'] = instructions

        # with open(prompts_path, 'w') as file:
        #     json.dump(config, file, ensure_ascii=False, indent=4)
        context = {name: basic.make_context(input) for name in NAME_LIST}
        context["judge"] = basic.make_context(input)

        debate = Debate(
            save_file_dir=save_file_dir, num_players=3, temperature=0, verbose=True
        )
        debate.init_debate(config, input, context)
        debate.run()
        debate.save_file_to_json("output")

    elif args.input_file.endswith("xlsx") or args.input_file.endswith("csv"):
        import pandas as pd
        from termcolor import colored

        # from OMG_based import cache_manager
        from tqdm.auto import tqdm

        if args.input_file.endswith("csv"):
            df = pd.read_csv(args.input_file)
        else:
            df = pd.read_excel(args.input_file)
        debate = Debate(
            save_file_dir=save_file_dir,
            num_players=3,
            temperature=0,
            verbose=args.verbose,
        )

        if args.random_row or args.commit_sha:
            if args.commit_sha:
                row = df[df["commit"] == args.commit_sha].iloc[0]
            else:
                row = df.sample(1).iloc[0]

            commit_url = f'https://github.com/{row["project"]}/commit/{row["commit"]}'
            diff = git_diff_tool.invoke(commit_url)
            # diff = basic.git_diff.format(diff=diff, summary=summarize_diff(diff))
            print(diff)

            # config['diff'] = diff
            # config['evaluation_criteria'] = instructions

            # with open(prompts_path, 'w') as file:
            #     json.dump(config, file, ensure_ascii=False, indent=4)
            complete_context = basic.make_context(
                diff,
                changed_files_importance=important_files_tool.invoke(commit_url),
                associated_issues=issue_collecting_tool.invoke(commit_url),
                associated_pull_requests=pull_request_collecting_tool.invoke(
                    commit_url
                ),
                changed_method_summaries=code_summarization_tool.invoke(commit_url),
                changed_class_functionality_summary=code_understanding_tool.invoke(
                    commit_url
                ),
            )
            # context = {
            #     "Debater 1": prompts.make_context(
            #         diff,
            #         changed_files_importance=important_files_tool.invoke(
            #             commit_url
            #         ),
            #     ),
            #     "Debater 2": prompts.make_context(
            #         diff,
            #         associated_issues=issue_collecting_tool.invoke(commit_url),
            #         associated_pull_requests=pull_request_collecting_tool.invoke(
            #             commit_url
            #         ),
            #     ),
            #     "Debater 3": prompts.make_context(
            #         diff,
            #         changed_method_summaries=code_summarization_tool.invoke(commit_url),
            #         changed_class_functionality_summary=code_understanding_tool.invoke(
            #             commit_url
            #         ),
            #     ),
            #     "judge": complete_context,
            # }
            context = {
                "Debater 1": complete_context,
                "Debater 2": complete_context,
                # "Debater 3": complete_context,
                "judge": complete_context,
            }
            debate.init_debate(config, context, "type")
            debate.run()
            cm_type = debate.save_file["selected_type"]

            debate.init_debate(config, context, "subject", cm_type=cm_type)
            debate.run()
            cm_subject = debate.save_file["selected_subject"]

            debate.init_debate(
                config, context, "body", cm_type=cm_type, cm_subject=cm_subject
            )
            debate.run()
            cm_body = debate.save_file["selected_body"]

            cm = f"{cm_type}: {cm_subject}\n{cm_body}"
            print("Commit URL:", colored(commit_url, "light_blue"))
            print("Commit Message:", colored(cm, "light_green"), sep="\n")
        else:
            csv_name = args.csv_name if args.csv_name else "mad.csv"
            save_file_path = os.path.join(save_file_dir, csv_name)
            if os.path.exists(save_file_path):
                df = pd.read_csv(save_file_path)
                df = df.fillna("")
                # Rename the CMG column to OMG
            else:
                df["MAD"] = ""

            if "CMG" in df.columns:
                df = df.rename(columns={"CMG": "OMG"})

            try:
                for i, row in tqdm(
                    df.iterrows(), desc="Generating commit messages", total=len(df)
                ):
                    if row["MAD"] != "":
                        continue

                    commit_url = (
                        f'https://github.com/{row["project"]}/commit/{row["commit"]}'
                    )
                    diff = git_diff_tool.invoke(commit_url)
                    # diff = basic.git_diff.format(
                    #     diff=diff, summary=summarize_diff(diff)
                    # )

                    # config['diff'] = diff
                    # config['evaluation_criteria'] = instructions

                    # with open(prompts_path, 'w') as file:
                    #     json.dump(config, file, ensure_ascii=False, indent=4)
                    complete_context = basic.make_context(
                        diff,
                        changed_files_importance=important_files_tool.invoke(
                            commit_url
                        ),
                        associated_issues=issue_collecting_tool.invoke(commit_url),
                        associated_pull_requests=pull_request_collecting_tool.invoke(
                            commit_url
                        ),
                        changed_method_summaries=code_summarization_tool.invoke(
                            commit_url
                        ),
                        changed_class_functionality_summary=code_understanding_tool.invoke(
                            commit_url
                        ),
                    )
                    # context = {
                    #     "Debater 1": prompts.make_context(
                    #         diff,
                    #         changed_files_importance=important_files_tool.invoke(
                    #             commit_url
                    #         ),
                    #     ),
                    #     "Debater 2": prompts.make_context(
                    #         diff,
                    #         associated_issues=issue_collecting_tool.invoke(commit_url),
                    #         associated_pull_requests=pull_request_collecting_tool.invoke(
                    #             commit_url
                    #         ),
                    #     ),
                    #     "Debater 3": prompts.make_context(
                    #         diff,
                    #         changed_method_summaries=code_summarization_tool.invoke(commit_url),
                    #         changed_class_functionality_summary=code_understanding_tool.invoke(
                    #             commit_url
                    #         ),
                    #     ),
                    #     "judge": complete_context,
                    # }
                    context = {
                        "Debater 1": complete_context,
                        "Debater 2": complete_context,
                        # "Debater 3": complete_context,
                        "judge": complete_context,
                    }

                    debate.init_debate(config, context, "type")
                    t1 = time.time()
                    debate.run()
                    cm_type = debate.save_file["selected_type"]

                    debate.init_debate(config, context, "subject", cm_type=cm_type)
                    debate.run()
                    cm_subject = debate.save_file["selected_subject"]

                    debate.init_debate(
                        config, context, "body", cm_type=cm_type, cm_subject=cm_subject
                    )
                    debate.run()
                    t2 = time.time()

                    cm_body = debate.save_file["selected_body"]

                    cm = f"{cm_type}: {cm_subject}\n{cm_body}"

                    df.at[i, "MAD"] = cm
                    df.at[i, "MAD_duration"] = t2 - t1
                    df.at[i, "Rounds"] = debate.round
                    df.at[i, "Total Tokens"] = debate.total_tokens
                    print("Time taken:", t2 - t1)
                    print("Commit URL:", commit_url)
                    print("Commit Message:", colored(cm, "yellow"), sep="\n")
                    print(colored("--" * 40, "light_green"))
            except KeyboardInterrupt:
                print("Stopping generation...")
            except Exception as e:
                print(e)
                print("Stopping due to exception...")

            df = df[
                [
                    "project",
                    "commit",
                    "OMG",
                    "AMG",
                    "MAD",
                    "MAD_duration",
                    "Rounds",
                    "Total Tokens",
                ]
            ]
            df.to_csv(save_file_path, index=False)
            df = df[df["MAD"] != ""]
            print("--" * 15, "MAD VS OMG", "--" * 15)
            evaluate_machine_generated_text(df["OMG"], df["MAD"], print_results=True)

    # for id, input in enumerate(tqdm(inputs)):
    # files = os.listdir(save_file_dir)
    # if f"{id}.json" in files:
    #     continue
