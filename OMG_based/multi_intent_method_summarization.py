import os
import pathlib

if __name__ == "__main__":
    import sys

    sys.path.append(str(pathlib.Path(__file__).parent.parent.resolve()))

import OMG_based.cache_manager as cache_manager
from OMG_based.code_summarizer import summarize_method_body
from OMG_based.method_body import get_method_bodies_after, get_method_bodies_before
from OMG_based.method_summarization.summarize import summarize_method
from OMG_based.utils import (  # get_commit_from_github,
    get_commit_id,
    get_file_names,
    get_repo_name,
    git_reset,
    run_java_jar,
)

use_old_method = os.getenv("METHOD_SUMMARIES", "NEW") == "OLD"
cur_dir = pathlib.Path(__file__).parent.resolve()
program_contexts_path = cur_dir / "program_contexts"
projects_dir = cur_dir / "Projects"


# print(get_method_bodies_after("https://github.com/apache/cxf/commit/70346bfc37cfd4de98bafa99681fa7276379162e"))
# before_method_bodies, deleted_method_bodies = get_method_bodies_before("https://github.com/apache/cxf/commit/70346bfc37cfd4de98bafa99681fa7276379162e")
def get_clustered_methods(commit_url):
    clustered_methods = {}

    before_method_bodies, deleted_method_bodies = get_method_bodies_before(commit_url)
    after_method_bodies, added_method_bodies = get_method_bodies_after(commit_url)

    before_methods = set(before_method_bodies.keys())
    after_methods = set(after_method_bodies.keys())
    added_methods = set(added_method_bodies.keys())
    deleted_methods = set(deleted_method_bodies.keys())

    modified_methods = before_methods.union(after_methods)

    clustered_methods["added"] = added_methods
    clustered_methods["deleted"] = deleted_methods
    clustered_methods["modified"] = modified_methods

    return (
        clustered_methods,
        before_method_bodies,
        after_method_bodies,
        added_method_bodies,
        deleted_method_bodies,
    )


def generate_multi_intent_summaries(commit_url, disable_cache=False):
    if not disable_cache:
        cached_value = cache_manager.get_execution_value(
            commit_url, "generate_multi_intent_summaries"
        )
        if cached_value:
            return cached_value
    # try:
    #     commit = get_commit_from_github(commit_url)
    # except ValueError as e:
    #     return "The tool did not receive a commit URL as input. Please provide a commit URL as input parameter."

    (
        clustered_methods,
        before_method_bodies,
        after_method_bodies,
        added_method_bodies,
        deleted_method_bodies,
    ) = get_clustered_methods(commit_url)

    # print(clustered_methods)
    repo_name = get_repo_name(commit_url)
    repo_dir = projects_dir / str(repo_name)
    # commit_id = commit.sha
    commit_id = get_commit_id(commit_url)
    # print(commit_id)
    # print(repo_name)
    changed_files, _ = get_file_names(repo_name, commit_id)

    if (
        not before_method_bodies
        and not after_method_bodies
        and not added_method_bodies
        and not deleted_method_bodies
    ):
        if not disable_cache:
            cache_manager.store_execution_value(
                commit_url,
                "generate_multi_intent_summaries",
                "The code changes in this git diff are not located within any method body.",
            )
        # return "The code changes in this git diff are not located within any method body. You probably should see if they are located in any class body."
        return (
            "The code changes in this git diff are not located within any method body."
        )

    ans = """Here are the summaries for all changed methods in this git diff in the commit url. For each method's before and after change versions, the summaries summarize it from five different perspectives: 

What: Describes the functionality of a method
Why: Explains the reason why a method is provided or the design rationale of the method
How-to-use: Describes the usage or the expected set-up of using a method
How-it-is-done: Describes the implementation details of a method
Property: Asserts properties of a method including pre-conditions or post-conditions of a method

"""
    for method_dec in clustered_methods["modified"]:
        if method_dec not in before_method_bodies:
            git_reset(repo_dir, commit_id + "^")

            for file in changed_files:

                dec_ranges = run_java_jar("method_dec_range.jar", str(repo_dir / file))

                for dec_range in dec_ranges:
                    cur_dec = dec_range.strip().split(":")[0]
                    if method_dec == cur_dec:
                        cur_rang = dec_range.strip().split(":")[1]
                        starting_line_num = int(cur_rang.split(",")[0])
                        ending_line_num = int(cur_rang.split(",")[1])
                        file_obj = open(projects_dir / str(repo_name) / file, "r")
                        all_file_lines = file_obj.readlines()
                        ori_method_body = ""
                        for line in all_file_lines[
                            starting_line_num - 1 : ending_line_num
                        ]:
                            ori_method_body += line
                        before_method_bodies[method_dec] = ori_method_body
                        break
                if (
                    method_dec in before_method_bodies
                    and before_method_bodies[method_dec]
                ):
                    break

        before_method_body = before_method_bodies.get(method_dec, None)

        if not before_method_body:
            continue
        # if before_method_body is none, this means there is no '-' in the before version
        # we need to git reset to the before version and extract the method body based on its dec
        if method_dec not in after_method_bodies:
            git_reset(repo_dir, commit_id)
            for file in changed_files:
                dec_ranges = run_java_jar("method_dec_range.jar", str(repo_dir / file))
                for dec_range in dec_ranges:
                    cur_dec = dec_range.strip().split(":")[0]
                    if method_dec == cur_dec:
                        cur_rang = dec_range.strip().split(":")[1]
                        starting_line_num = int(cur_rang.split(",")[0])
                        ending_line_num = int(cur_rang.split(",")[1])
                        file_obj = open(projects_dir / str(repo_name) / file, "r")
                        all_file_lines = file_obj.readlines()
                        ori_method_body = ""
                        for line in all_file_lines[
                            starting_line_num - 1 : ending_line_num
                        ]:
                            ori_method_body += line
                        after_method_bodies[method_dec] = ori_method_body
                        break
                if (
                    method_dec in after_method_bodies
                    and after_method_bodies[method_dec]
                ):
                    break

        # print(before_method_body)
        if before_method_body:
            before_method_what = summarize_method_body(before_method_body, "what")
            before_method_why = summarize_method_body(before_method_body, "why")
            before_method_use = summarize_method_body(before_method_body, "usage")
            before_method_done = summarize_method_body(before_method_body, "done")
            before_method_property = summarize_method_body(
                before_method_body, "property"
            )
            before_summary = (
                "What: "
                + before_method_what
                + "\n"
                + "Why: "
                + before_method_why
                + "\n"
                "How-to-use: "
                + before_method_use
                + "\n"
                + "How-it-is-done: "
                + before_method_done
                + "\n"
                + "Property: "
                + before_method_property
                + "\n"
            )

        after_method_body = after_method_bodies.get(method_dec, None)

        if after_method_body:
            if use_old_method:
                after_method_what = summarize_method_body(after_method_body, "what")
                after_method_why = summarize_method_body(after_method_body, "why")
                after_method_use = summarize_method_body(after_method_body, "usage")
                after_method_done = summarize_method_body(after_method_body, "done")
                after_method_property = summarize_method_body(
                    after_method_body, "property"
                )
                after_summary = (
                    "The method summaries after the commit are:\n"
                    "What: "
                    + after_method_what
                    + "\n"
                    + "Why: "
                    + after_method_why
                    + "\n"
                    "How-to-use: "
                    + after_method_use
                    + "\n"
                    + "How-it-is-done: "
                    + after_method_done
                    + "\n"
                    + "Property: "
                    + after_method_property
                    + "\n"
                )
            else:
                after_summary = summarize_method(
                    before_method_body, after_method_body, before_summary
                )
            ans += "Method {} is modified by this git diff.\n".format(method_dec)
            ans += "The method summaries before the commit are:\n"
            ans += before_summary + "\n\n"
            ans += after_summary

    for method_dec in clustered_methods["added"]:
        after_method_body = added_method_bodies[method_dec]

        after_method_what = summarize_method_body(after_method_body, "what")
        after_method_why = summarize_method_body(after_method_body, "why")
        after_method_use = summarize_method_body(after_method_body, "usage")
        after_method_done = summarize_method_body(after_method_body, "done")
        after_method_property = summarize_method_body(after_method_body, "property")

        ans += "Method {} is newly added by this git diff.\n".format(method_dec)
        ans += "Its summaries are: \n"
        ans += (
            "What: " + after_method_what + "\n" + "Why: " + after_method_why + "\n"
            "How-to-use: "
            + after_method_use
            + "\n"
            + "How-it-is-done: "
            + after_method_done
            + "\n"
            + "Property: "
            + after_method_property
            + "\n"
        )

    for method_dec in clustered_methods["deleted"]:
        before_method_body = deleted_method_bodies[method_dec]

        before_method_what = summarize_method_body(before_method_body, "what")
        before_method_why = summarize_method_body(before_method_body, "why")
        before_method_use = summarize_method_body(before_method_body, "usage")
        before_method_done = summarize_method_body(before_method_body, "done")
        before_method_property = summarize_method_body(before_method_body, "property")

        ans += "\n\nMethod {} is deleted by this git diff.\n".format(method_dec)
        ans += "Its summaries are: \n"
        ans += (
            "What: " + before_method_what + "\n" + "Why: " + before_method_why + "\n"
            "How-to-use: "
            + before_method_use
            + "\n"
            + "How-it-is-done: "
            + before_method_done
            + "\n"
            + "Property: "
            + before_method_property
            + "\n"
        )

    if not disable_cache:
        cache_manager.store_execution_value(
            commit_url, "generate_multi_intent_summaries", ans
        )

    return ans


if __name__ == "__main__":
    project = "apache/directory-server"
    sha = "9cbf06fcae73d281aa4804e574335d12fd0764ec"

    # project = "apache/ant"
    # sha = "5e099552e5af434568a4294cf7bcebb732cd3bfa"

    # project = "apache/cxf"
    # sha = "260efe56fc1bfc89950d1eda89114feb287490cd"
    commit_url = f"https://github.com/{project}/commit/{sha}"

    # commit_url = (
    #     "https://github.com/apache/cxf/commit/cbc0fde7f85d01e379e40a7f27fe5cea20169ddf"
    # )

    print(commit_url)
    response = generate_multi_intent_summaries(commit_url, disable_cache=True)
    print(response)
