import os
import subprocess
import sys

from termcolor import colored

sys.path.append("..")
should_remove_comments = os.getenv("REMOVE_COMMENTS", "TRUE") == "TRUE"
use_fidex = os.getenv("USE_FIDEX", "FALSE") == "TRUE"

if use_fidex:
    print(colored("Using FIDEX to augment diff", "green"))
    from common.fidex import explain_diff

if should_remove_comments:
    print("Removing comments from class bodies before summarization")
else:
    print("Keeping comments in class bodies before summarization")

# from .utils import get_commit_from_github, get_repo_name, get_file_names, get_commit_id
import pandas as pd

# import re
from langchain.agents import Tool
from langchain.tools import BaseTool

import CMG.cache_manager as cache_manager

# from OMG_based.code_understanding import class_sum
if not should_remove_comments:
    from CMG.class_summarizer_omg import class_sum
else:
    from CMG.class_summarizer_enhanced import class_sum

from CMG.commit_type_classifier import classify_commit_type
from CMG.crawl_pr_issue import *
from CMG.fetch_important_files import export_dependencies_csv
from CMG.multi_intent_method_summarization import (
    generate_multi_intent_summaries,
    projects_dir,
)
from CMG.utils import *

# diff_explanation_method = os.getenv("DIFF_EXPLANATION_METHOD", "None")

# if diff_explanation_method == "zeroshot":
#     from common.diff_explainer.zeroshot import summarize_diff
# elif diff_explanation_method == "interactive":
#     from common.diff_explainer.interactive import summarize_diff
# elif diff_explanation_method == "fewshot":
#     from common.diff_explainer.fewshot import summarize_diff

# print("Diff explanation method:", diff_explanation_method)


def get_git_diff_from_commit_url(commit_url=""):
    try:
        # try:
        #     commit = get_commit_from_github(commit_url)
        # except GithubException as e:
        #     return "It seems like you have not provided the user's commit URL and modified the original URL. Please use this Action again and provide the original commit URL as Action Input."
        # try:
        # repo_name = get_repo_name(commit_url)
        # commit_id = get_commit_id(commit_url)
        cached_diff = cache_manager.get_commit_data(commit_url, "git_diff")
        if cached_diff:
            if not use_fidex:
                return "\n" + cached_diff
            else:
                diff_summary = cache_manager.get_execution_value(
                    commit_url,
                    "diff_summary",
                    # model_name="Meta-Llama-3-70B-Instruct-AWQ",
                )
                if diff_summary:
                    return "\n" + cached_diff + "\n\n" + diff_summary
                else:
                    diff_summary = explain_diff(cached_diff)
                    cache_manager.store_execution_value(
                        commit_url, "diff_summary", diff_summary
                    )
                    return "\n" + cached_diff + "\n\n" + diff_summary

        patches = get_patches(commit_url)
        cache_manager.store_commit_data(commit_url, "git_diff", patches)

        git_diff = "\n" + patches
        if not use_fidex:
            return git_diff
        else:
            diff_summary = explain_diff(patches)
            cache_manager.store_execution_value(
                commit_url, "diff_summary", diff_summary
            )
            return git_diff + "\n\n" + diff_summary
        # except:
        #     return "It seems like you have not provided the original user's commit URL and modified the original URL. Please use this Action again and provide the original commit URL as Action Input."

    except ValueError as e:
        print("\n" + str(e))
        return "The tool did not receive a full commit URL as input. Please use this Action again and provide a full commit URL as Action Input. You should use the exact same commit URL for which you want to get the git diff."


git_diff_tool = Tool(
    name="Git diff collector tool",
    func=get_git_diff_from_commit_url,
    description="Given a commit url, this tool outputs git diff. Input should be a full commit url.",
)

code_summarization_tool = Tool(
    name="Changed method summarization tool",
    func=generate_multi_intent_summaries,
    description="useful when  the changes are in method bodies and you need to collect the summaries of all changed methods (from various perspectives) in the git diff in a commit url. Input should be a commit url",
)

code_understanding_tool = Tool(
    name="Changed class functionality summarization tool",
    func=class_sum,
    description="useful when the changes impact some class(es) functionality and you need to collect the functionality summaries of all changed classes in the git diff in a commit url. Input should be a commit url",
)

commit_type_classifier_tool = Tool(
    name="Software maintenance activity type classifier tool",
    func=classify_commit_type,
    description="useful when you want to realize the software maintenance activity type of a commit. Input should be a commit url",
)


class IssueCollectingTool(BaseTool):
    name = "Issue report content collector"
    description = "Returns associated issue report content using a commit url. Input should be a commit url"

    def _run(self, commit_url: str):
        cached = cache_manager.get_commit_data(commit_url, "issues")
        if cached:
            return cached

        try:
            github_issue = get_github_issue_content(commit_url)
        except ValueError as e:
            return "The tool did not receive a commit URL as input. Please use the tool with initial commit URL as Action Input."

        jira_issue = get_jira_issue_content(commit_url)
        if github_issue:
            return_val = github_issue
        elif jira_issue:
            return_val = jira_issue
        else:
            return_val = (
                "There is no issue report associated with this commit url (git diff)"
            )

        cache_manager.store_commit_data(commit_url, "issues", return_val)
        return return_val

    def _arun(self, commit_url: str):
        raise NotImplementedError("This tool does not support async")


class PullRequestCollectingTool(BaseTool):
    name = "Pull request content collector"
    description = "use this tool when you need to collect associated pull request content using a commit url. Input should be a commit url"

    def _run(self, commit_url: str):
        cached = cache_manager.get_commit_data(commit_url, "prs")
        if cached:
            return cached

        try:
            pr_content = get_pr_content(commit_url)
        except ValueError as e:
            return_val = "The tool did not receive a commit URL as input. Please use the tool with initial commit URL as Action Input."

        if pr_content:
            return_val = pr_content
        else:
            return_val = (
                "There is no pull request associated with this commit url (git diff)"
            )

        cache_manager.store_commit_data(commit_url, "prs", return_val)
        return return_val

    def _arun(self, commit_url: str):
        raise NotImplementedError("This tool does not support async")


class ImportantFileTool(BaseTool):
    name = "changed files importance ranker tool"
    description = "use this tool when the commit has changed more than one file and you need to understand their relative importance. Input should be a commit url"

    def _run(self, commit_url: str):
        cached = cache_manager.get_commit_data(commit_url, "important_files")
        if cached:
            return cached
        return_val = None
        commit = get_commit_from_github(commit_url)
        repo_name = get_repo_name(commit_url)
        if commit:
            changed_files, _ = get_file_names(commit)
            max_deps_files = []
            if len(changed_files) > 1:
                commit_id = get_commit_id(commit_url)
                dependencies_path = projects_dir / repo_name / f"{commit_id}.csv"
                # dependencies_path = os.path.join(
                #     "program_contexts",
                #     "file_dependencies",
                #     repo_name,
                #     f"{commit_id}.csv",
                # )
                if not os.path.exists(dependencies_path):
                    # this input file should also be ready
                    export_dependencies_csv(repo_name, commit_id)
                df = pd.read_csv(dependencies_path)
                changed_files_deps = df[df["To File"].isin(changed_files)]
                if changed_files_deps.empty:
                    return_val = "Could not figure out the most important file(s)."
                else:
                    changed_files_deps = changed_files_deps.sort_values(
                        by="From Files", ascending=False
                    )
                    max_deps_files = changed_files_deps["To File"].values.tolist()
                # max_deps_val = max(outwards_deps)
                # for idx, outwards_dep in enumerate(outwards_deps):
                #     if outwards_dep == max_deps_val:
                #         max_deps_files.append(change_files_deps[idx])
            else:
                return_val = "There is only one changed file in this commit. There was no need to use this tool."

            if not return_val:
                output_deps_files = "Here is the list of changed files in the commit ordered by their importance from the most important to the least important:\n\n"
                for i, deps_file in enumerate(max_deps_files):
                    output_deps_files += f"{i+1}- {deps_file}\n"
                return_val = output_deps_files

            cache_manager.store_commit_data(commit_url, "important_files", return_val)
            return return_val
        else:
            cache_manager.store_execution_value(
                commit_url, "important_files", "Could not find this commit on Github."
            )
            return "Could not find this commit on Github."

    def _arun(self, commit_url: str):
        raise NotImplementedError("This tool does not support async")


class HistoricalContextTool(BaseTool):
    name = "Historical context collector tool"
    description = "use this tool when you need to collect the historical context of a commit. Input should be a commit url."

    def _get_last_commit_info(self, repo_name: str, commit_id: str, file_path: str):
        raw_output = subprocess.run(
            f'cd Projects/{repo_name}; git log --patch --pretty=format:"%H%n%s%n%b" {commit_id}^ -- {file_path};',
            stdout=subprocess.PIPE,
            text=True,
            shell=True,
        ).stdout.split("\n", 3)
        if len(raw_output) < 4:
            return None
        return {
            "commit_id": raw_output[0],
            "commit_message": raw_output[1] + "\n" + raw_output[2],
            "diff": raw_output[3].strip(),
        }

    def _run(self, commit_url: str):
        commit = get_commit_from_github(commit_url)
        repo_name = get_repo_name(commit_url)
        if commit:
            changed_files, _ = get_file_names(commit)
            commit_id = get_commit_id(commit_url)
            history = []
            changed_files_list = "\n".join(changed_files)
            history.append(
                f"This commit has affected the following files:\n\n{changed_files_list}\n\n"
            )
            history.append(
                "For each file, here is the information gathered from the last commit that affected it before the current commit:\n\n"
            )
            for f in changed_files:
                history.append(f"File: {f}\n")
                commit_info = self._get_last_commit_info(repo_name, commit_id, f)
                if commit_info:
                    history.append(f'Commit ID: {commit_info["commit_id"]}\n')
                    history.append(
                        f'Commit Message:\n```\n{commit_info["commit_message"]}\n```\n'
                    )
                    history.append(f'Git Diff: \n```{commit_info["diff"]}\n```\n')
                else:
                    history.append("No previous commit found that changed this file.\n")
                history.append("\n")
            # print(changed_files)
            dependencies_path = os.path.join(
                "program_contexts",
                "file_dependencies",
                repo_name,
                f"pairwise-{commit_id}.csv",
            )
            if not os.path.exists(dependencies_path):
                export_dependencies_csv(repo_name, commit_id)

            df = pd.read_csv(dependencies_path)
            dependency_from = df[df["To File"].isin(changed_files)]
            dependency_to = df[df["From File"].isin(changed_files)]
            # dependency_from.to_csv('program_contexts/dependency_from.csv', index=False)
            # dependency_to.to_csv('program_contexts/dependency_to.csv', index=False)
            if dependency_from.empty and dependency_to.empty:
                return "Could not retrieve historical context for this commit."

            return "".join(history)
        else:
            return "Could not retrieve historical context for this commit."

    def _arun(self, commit_url: str):
        raise NotImplementedError("This tool does not support async")


if __name__ == "__main__":
    # tool = PullRequestCollectingTool()
    tool = get_git_diff_from_commit_url

    # For testing issue collecting tool
    # commit_url = "https://github.com/apache/cassandra/commit/8c04ffd52a43358a8eb56a68fa7aeae0bfa94577"

    # For testing commit with multiple changed files
    # commit_url = "https://github.com/apache/directory-server/commit/5ce848b860c02a77a8d45757b11ebd2ece71fbb9"
    commit_url = "https://github.com/apache/directory-server/commit/b5546be3333d7a261e6db37ab6e36f34193cffbb"

    # Get the url from user
    # commit_url = input("Enter the commit url: ")

    print(tool(commit_url))
