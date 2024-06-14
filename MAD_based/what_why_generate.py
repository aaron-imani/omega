import sys
from argparse import ArgumentParser

sys.path.extend(["..", "../OMG_based"])

import pandas as pd
from tqdm.auto import tqdm

from evaluation.evaluate_cm import evaluate_machine_generated_text
from MAD_based.debate.what_why_generate import Debate
from OMG_based.Agent_tools import *
from OMG_based.utils import highlight_git_diff

issue_collecting_tool = IssueCollectingTool()
pull_request_collecting_tool = PullRequestCollectingTool()
important_files_tool = ImportantFileTool()

if __name__ == "__main__":
    import time

    from termcolor import colored

    parser = ArgumentParser()
    parser.add_argument(
        "input_path",
        type=str,
    )
    parser.add_argument("output_path", type=str)
    parser.add_argument("--num_players", type=int, default=2)
    parser.add_argument("-i", "--information-card", action="store_true")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    df = pd.read_csv(args.input_path)
    debate = Debate(args.num_players, use_information_card=args.information_card)

    save_file_path = args.output_path
    if os.path.exists(save_file_path) and not args.reset:
        df = pd.read_csv(save_file_path)
        df = df.fillna("")
    else:
        df["MAD"] = ""

    try:
        for i, row in tqdm(
            df.iterrows(), desc="Generating commit messages", total=len(df)
        ):
            if row["MAD"] != "":
                continue

            commit_url = f'https://github.com/{row["project"]}/commit/{row["commit"]}'

            t1 = time.time()
            diff = git_diff_tool.invoke(commit_url)
            diff = highlight_git_diff(diff)

            commit_context = {
                "git_diff": diff,
                "changed_files_importance": important_files_tool.invoke(commit_url),
                "changed_method_summaries": code_summarization_tool.invoke(commit_url),
                "changed_class_functionality_summary": code_understanding_tool.invoke(
                    commit_url
                ),
                "associated_issues": issue_collecting_tool.invoke(commit_url),
                "associated_pull_requests": pull_request_collecting_tool.invoke(
                    commit_url
                ),
            }
            debate.prepare_context(commit_context)
            cm = debate.run()
            t2 = time.time()
            df.at[i, "MAD"] = cm
            print("Time taken:", t2 - t1)
            print("Commit URL:", commit_url)
            print("Commit Message:", colored(cm, "yellow"), sep="\n")
            print(colored("--" * 40, "light_green"))
    except KeyboardInterrupt:
        print("Stopping generation...")
    except Exception as e:
        print(type(e))
        print(e)
        print("Stopping due to exception...")

    df.to_csv(save_file_path, index=False)
    evaluate_machine_generated_text(df["CMG"], df["MAD"], print_results=True)

# if __name__ == "__main__":
#     debate = Debate(2, use_information_card=False)

#     # commit_url = input("Enter the commit URL: ")
#     # commit_url = (
#     #     "https://github.com/apache/ant/commit/89aa7775a83989345756349f99bd3556780eafee"
#     # )
#     commit_url = (
#         "https://github.com/apache/ant/commit/1a3090627d25c1ede9407003e24d7e76ca48f293"
#     )
#     # commit_url = "https://github.com/apache/directory-server/commit/9cbf06fcae73d281aa4804e574335d12fd0764ec"
#     # commit_url = "https://github.com/apache/wicket/commit/526bb16ab2f8b770a052fc93069b8b38a1d6c1f5"
#     while commit_url != "q":
#         diff = git_diff_tool.invoke(commit_url)
#         diff = highlight_git_diff(diff)

#         commit_context = {
#             "git_diff": diff,
#             "changed_files_importance": important_files_tool.invoke(commit_url),
#             "changed_method_summaries": code_summarization_tool.invoke(commit_url),
#             "changed_class_functionality_summary": code_understanding_tool.invoke(
#                 commit_url
#             ),
#             "associated_issues": issue_collecting_tool.invoke(commit_url),
#             "associated_pull_requests": pull_request_collecting_tool.invoke(commit_url),
#         }
#         debate.prepare_context(commit_context)
#         cm = debate.run()
#         print(cm)
#         commit_url = input("Enter the commit URL: ")
