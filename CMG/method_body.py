import os
import pathlib
import subprocess

if __name__ == "__main__":
    import sys

    sys.path.append("..")

from CMG.utils import (
    get_added_line_nums_file,
    get_commit_from_github,
    get_commit_id,
    get_deleted_line_nums_file,
    get_file_change_status,
    get_file_names,
    get_repo_name,
    git_reset,
)

cur_dir = pathlib.Path(__file__).parent.resolve()
program_contexts_path = cur_dir / "program_contexts"
projects_dir = cur_dir / "Projects"


def _get_method_ranges(file_path):
    method_ranges_cmd = [
        "java",
        "-jar",
        "program_contexts/method_body_ranges.jar",
        file_path,
    ]
    raw_ranges = subprocess.run(
        method_ranges_cmd, text=True, capture_output=True, cwd=cur_dir
    ).stdout.splitlines()
    return raw_ranges


def _get_method_dec(file_path):
    method_decs_cmd = [
        "java",
        "-jar",
        "program_contexts/method_dec.jar",
        file_path,
    ]
    method_decs = subprocess.run(
        method_decs_cmd, text=True, capture_output=True, cwd=cur_dir
    ).stdout.splitlines()
    return method_decs


# file change status: added, removed, modified, renamed
def get_method_bodies_before(commit_url):
    """For a commit, collect all the changed method bodies (before change)"""
    changed_method_bodies = {}
    deleted_method_bodies = {}
    try:
        commit = get_commit_from_github(commit_url)
    except ValueError as e:
        return (
            "The tool did not receive a commit URL as input. Please provide a commit URL as input parameter.",
            "The tool did not receive a commit URL as input. Please provide a commit URL as input parameter.",
        )

    repo_name = get_repo_name(commit_url)
    repo_dir = projects_dir / repo_name
    # commit_id = commit.commit.sha
    commit_id = get_commit_id(commit_url)
    changed_files, file_status = get_file_names(repo_name, commit_id)

    minus_related_files = []
    for i, file in enumerate(changed_files):
        if file_status[i] == "removed" or file_status[i] == "modified":
            minus_related_files.append(file)

    for file in minus_related_files:
        deleted_line_nums = get_deleted_line_nums_file(commit, file)
        if not deleted_line_nums:
            return {}, {}

        file_path = projects_dir / repo_name / file
        file_path = str(file_path)

        git_reset(repo_dir, commit_id + "^1")

        raw_ranges = _get_method_ranges(file_path)
        if not raw_ranges:
            return {}, {}

        method_decs = _get_method_dec(file_path)

        method_ranges = {}

        for i, rang in enumerate(raw_ranges):
            method_ranges[rang.strip()] = [0, method_decs[i].strip()]
        for deleted_line_num in deleted_line_nums:
            for rang in method_ranges.keys():
                starting_line_num = int(rang.split(",")[0])
                ending_line_num = int(rang.split(",")[1])
                if (
                    starting_line_num <= deleted_line_num
                    and deleted_line_num <= ending_line_num
                ):
                    if method_ranges[rang][0] == 0:
                        if deleted_line_num == starting_line_num:
                            method_ranges[rang][0] = 2
                        else:
                            method_ranges[rang][0] = 1
                    break
        changed_method_ranges = []
        deleted_method_ranges = []
        for rang in method_ranges.keys():
            if method_ranges[rang][0] == 1:
                changed_method_ranges.append([rang, method_ranges[rang][1]])
            if method_ranges[rang][0] == 2:
                deleted_method_ranges.append([rang, method_ranges[rang][1]])

        file_obj = open(file_path, "r")
        all_file_lines = file_obj.readlines()
        cur_changed_method_body = ""
        for rang, dec in changed_method_ranges:
            starting_line_num = int(rang.split(",")[0])
            ending_line_num = int(rang.split(",")[1])
            for line in all_file_lines[starting_line_num - 1 : ending_line_num]:
                cur_changed_method_body += line
            changed_method_bodies[dec] = cur_changed_method_body
            cur_changed_method_body = ""

        cur_deleted_method_body = ""
        for rang, dec in deleted_method_ranges:
            starting_line_num = int(rang.split(",")[0])
            ending_line_num = int(rang.split(",")[1])
            for line in all_file_lines[starting_line_num - 1 : ending_line_num]:
                cur_deleted_method_body += line
            deleted_method_bodies[dec] = cur_deleted_method_body
            cur_deleted_method_body = ""

    # os.remove(program_contexts_path / "del_method_ranges.txt")
    # os.remove(program_contexts_path / "del_method_decs.txt")
    return changed_method_bodies, deleted_method_bodies


def get_method_bodies_after(commit_url):
    """For a commit, collect all the changed method bodies (after change)"""
    changed_method_bodies = {}
    added_method_bodies = {}

    commit = get_commit_from_github(commit_url)
    repo_name = get_repo_name(commit_url)
    repo_dir = projects_dir / repo_name
    # commit_id = commit.commit.sha
    commit_id = get_commit_id(commit_url)
    changed_files, file_status = get_file_names(repo_name, commit_id)

    minus_related_files = []
    for i, file in enumerate(changed_files):
        if file_status[i] == "added" or file_status[i] == "modified":
            minus_related_files.append(file)

    for file in minus_related_files:
        deleted_line_nums = get_added_line_nums_file(commit, file)
        file_path = projects_dir / repo_name / file
        file_path = str(file_path)

        if not deleted_line_nums:
            return {}, {}

        git_reset(repo_dir, commit_id)

        raw_ranges = _get_method_ranges(file_path)
        if not raw_ranges:
            return {}, {}

        method_decs = _get_method_dec(file_path)

        method_ranges = {}
        for i, rang in enumerate(raw_ranges):
            method_ranges[rang.strip()] = [0, method_decs[i].strip()]
        for deleted_line_num in deleted_line_nums:
            for rang in method_ranges.keys():
                starting_line_num = int(rang.split(",")[0])
                ending_line_num = int(rang.split(",")[1])
                if (
                    starting_line_num <= deleted_line_num
                    and deleted_line_num <= ending_line_num
                ):
                    if method_ranges[rang][0] == 0:
                        if deleted_line_num == starting_line_num:
                            method_ranges[rang][0] = 2
                        else:
                            method_ranges[rang][0] = 1
                    break

        changed_method_ranges = []
        added_method_ranges = []
        for rang in method_ranges.keys():
            if method_ranges[rang][0] == 1:
                changed_method_ranges.append([rang, method_ranges[rang][1]])
            if method_ranges[rang][0] == 2:
                added_method_ranges.append([rang, method_ranges[rang][1]])

        file_obj = open(file_path, "r")
        all_file_lines = file_obj.readlines()
        cur_changed_method_body = ""
        for rang, dec in changed_method_ranges:
            starting_line_num = int(rang.split(",")[0])
            ending_line_num = int(rang.split(",")[1])
            for line in all_file_lines[starting_line_num - 1 : ending_line_num]:
                cur_changed_method_body += line
            changed_method_bodies[dec] = cur_changed_method_body
            cur_changed_method_body = ""

        cur_added_method_body = ""
        for rang, dec in added_method_ranges:
            starting_line_num = int(rang.split(",")[0])
            ending_line_num = int(rang.split(",")[1])
            for line in all_file_lines[starting_line_num - 1 : ending_line_num]:
                cur_added_method_body += line
            added_method_bodies[dec] = cur_added_method_body
            cur_added_method_body = ""

    return changed_method_bodies, added_method_bodies


if __name__ == "__main__":
    print(
        get_method_bodies_before(
            "https://github.com/apache/directory-server/commit/9cbf06fcae73d281aa4804e574335d12fd0764ec"
        )[0]
    )
    print(
        get_method_bodies_after(
            "https://github.com/apache/directory-server/commit/9cbf06fcae73d281aa4804e574335d12fd0764ec"
        )[0]
    )

# print(get_method_bodies_after("https://github.com/apache/aries/commit/1d218aa184252f1e26a66f8e13eb277bdab343f2"))
