import getpass
import json
import os
import pathlib
import re
import subprocess

from dotenv import load_dotenv
from github import Commit, Github, GithubException

load_dotenv(".env")

auth_token_1 = os.environ.get("GITHUB_API_TOKEN")
if not auth_token_1:
    auth_token_1 = getpass.getpass("Enter your GitHub token:")

cur_dir = pathlib.Path(__file__).parent.absolute()
g = Github(auth_token_1)

# Original implementation
# def get_commit_from_github(commit_url): # must be from https://
#     headers = {'Authorization': 'token ' + auth_token_1}
#     api_url = commit_url.replace('https://github.com/', 'https://api.github.com/repos/').replace('/commit/', '/commits/')
#     response = requests.get(api_url, headers= headers)
#     response.raise_for_status()
#     return response.json()


def git_reset(repo_dir, commita_sha):
    git_reset_cmd = f"git reset --hard {commita_sha}"
    subprocess.run(
        git_reset_cmd, text=True, shell=True, cwd=repo_dir, stdout=subprocess.PIPE
    )


def run_java_jar(jar_name, *args):
    cmd = ["java", "-jar", f"program_contexts/{jar_name}"]
    cmd.extend(args)

    return subprocess.run(
        cmd, text=True, cwd=cur_dir, capture_output=True
    ).stdout.splitlines()


def get_commit_from_github(commit_url):  # must be from https://
    match = re.search(
        r"https?://github\.com/([^/]+/[^/]+)/commit/([a-f0-9]+)", commit_url
    )
    if not match:
        raise ValueError(f"Invalid commit URL: {commit_url}")

    repo_name = match.group(1)
    commit_id = match.group(2)
    repo = g.get_repo(repo_name)
    try:
        commit = repo.get_commit(commit_id)
    except GithubException:
        raise ValueError(
            f"You have not provided the original commit URL. Please use this tool again by providing the original commit URL."
        )
    return commit


def get_repo_name(commit_url):
    ls1 = commit_url.split("/")
    return ls1[4]


# Original implementation
# def get_file_names(commit):
#     if 'files' not in commit:
#         raise ValueError(f'Commit {commit} does not return any changed files')
#     change_files = []
#     for file in commit['files']:
#         change_files.append(file['filename'])
#     return change_files


# def get_file_names(commit):
#     if len(commit.files) == 0:
#         raise ValueError(f"Commit {commit} does not return any changed files")
#     return [file.filename for file in commit.files]


def get_file_names(repo_name, commit_sha):
    def get_status(status):
        if status == "A":
            return "added"
        elif status == "M":
            return "modified"
        return "deleted"

    cmd = [
        "git",
        "diff",
        "--name-status",
        f"{commit_sha}^",
        commit_sha,
        "--",
        "*.java",
    ]

    changed_files = (
        subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            text=True,
            cwd=cur_dir / f"Projects/{repo_name}",
        )
        .stdout.strip()
        .split("\n")
    )
    changed_files = [file.split("\t") for file in changed_files]
    file_names = [file[1] for file in changed_files]
    status = [file[0] for file in changed_files]
    status = list(map(get_status, status))
    return file_names, status


# Original implementation
# file name is from one of the filenames output from the api
# def get_file_change_status(commit, file_name):
#     file_info = {}
#     for file in commit['files']:
#         if file['filename'] == file_name:
#             file_info = file
#             break
#     if file_info:
#         return file_info["status"]
#     else:
#         return "There is something wrong with Github API to get changed file info"


def get_file_change_status(commit, file_name):
    for file in commit.files:
        if file.filename == file_name:
            return file.status
    return "There is something wrong with Github API to get changed file info"


# Original implementation
# def get_added_line_nums_file(commit, file_name):
#     file_info = {}
#     for file in commit['files']:
#         if file['filename'] == file_name:
#             file_info = file
#             break
#     if file_info:
#         file_commit_diff = file_info["patch"]
#         raw_file_diff_lines = file_commit_diff.split('\n')
#         block_start_idxs = []
#         for idx, raw_line in enumerate(raw_file_diff_lines):
#             if raw_line[0] == '@':
#                 block_start_idxs.append(idx)
#         starting_line_numbers = []
#         for idx in block_start_idxs:
#             block_header = raw_file_diff_lines[idx]
#             sub1_lst = re.findall(r'@@.+@@', block_header)
#             header = sub1_lst[0]
#             sub2_lst = re.findall(r'\+\d+', header)
#             added_line_starting_num = int(sub2_lst[0].replace("+", ""))
#             starting_line_numbers.append(added_line_starting_num)

#         blocks = []
#         cur_block = []
#         for idx, raw_line in enumerate(raw_file_diff_lines):
#             if idx in block_start_idxs:
#                 if cur_block:
#                     blocks.append(cur_block)
#                 cur_block = []
#                 continue
#             cur_block.append(raw_line)
#         blocks.append(cur_block)

#         added_line_numbers = []
#         for idx, block in enumerate(blocks):
#             starting_line_number = starting_line_numbers[idx]
#             line_num = 0
#             for i, code_line in enumerate(block):
#                 if code_line[0] == '-': # remove those minus lines cuz they are still in there
#                     continue
#                 if code_line[0] == '+':
#                     added_line_numbers.append(starting_line_number + line_num)
#                 line_num += 1
#         return added_line_numbers

#     else:
#         return []


def get_added_line_nums_file(commit: Commit.Commit, file_name):
    for file in commit.files:
        if file.filename == file_name:
            file_commit_diff = file.patch
            raw_file_diff_lines = file_commit_diff.split("\n")
            block_start_idxs = []
            for idx, raw_line in enumerate(raw_file_diff_lines):
                if raw_line[0] == "@":
                    block_start_idxs.append(idx)
            starting_line_numbers = []
            for idx in block_start_idxs:
                block_header = raw_file_diff_lines[idx]
                sub1_lst = re.findall(r"@@.+@@", block_header)
                header = sub1_lst[0]
                sub2_lst = re.findall(r"\+\d+", header)
                added_line_starting_num = int(sub2_lst[0].replace("+", ""))
                starting_line_numbers.append(added_line_starting_num)

            blocks = []
            cur_block = []
            for idx, raw_line in enumerate(raw_file_diff_lines):
                if idx in block_start_idxs:
                    if cur_block:
                        blocks.append(cur_block)
                    cur_block = []
                    continue
                cur_block.append(raw_line)
            blocks.append(cur_block)

            added_line_numbers = []
            for idx, block in enumerate(blocks):
                starting_line_number = starting_line_numbers[idx]
                line_num = 0
                for i, code_line in enumerate(block):
                    if (
                        code_line[0] == "-"
                    ):  # remove those minus lines cuz they are still in there
                        continue
                    if code_line[0] == "+":
                        added_line_numbers.append(starting_line_number + line_num)
                    line_num += 1
            return added_line_numbers

    return []


# Original implementation
# def get_deleted_line_nums_file(commit, file_name):
#     file_info = {}
#     for file in commit['files']:
#         if file['filename'] == file_name:
#             file_info = file
#             break
#     if file_info:
#         file_commit_diff = file_info["patch"]
#         raw_file_diff_lines = file_commit_diff.split('\n')
#         block_start_idxs = []
#         for idx, raw_line in enumerate(raw_file_diff_lines):
#             if raw_line[0] == '@':
#                 block_start_idxs.append(idx)
#         starting_line_numbers = []
#         for idx in block_start_idxs:
#             block_header = raw_file_diff_lines[idx]
#             sub1_lst = re.findall(r'@@.+@@', block_header)
#             header = sub1_lst[0]
#             sub2_lst = re.findall(r'-\d+', header)
#             deleted_line_starting_num = int(sub2_lst[0].replace("-", ""))
#             starting_line_numbers.append(deleted_line_starting_num)

#         blocks = []
#         cur_block = []
#         for idx, raw_line in enumerate(raw_file_diff_lines):
#             if idx in block_start_idxs:
#                 if cur_block:
#                     blocks.append(cur_block)
#                 cur_block = []
#                 continue
#             cur_block.append(raw_line)
#         blocks.append(cur_block)

#         deleted_line_numbers = []
#         for idx, block in enumerate(blocks):
#             starting_line_number = starting_line_numbers[idx]
#             line_num = 0
#             for i, code_line in enumerate(block):
#                 if code_line[0] == '+':  # remove those plus lines cuz they are still in there
#                     continue
#                 if code_line[0] == '-':
#                     deleted_line_numbers.append(starting_line_number + line_num)
#                 line_num += 1
#         return deleted_line_numbers

#     else:
#         return []


def get_deleted_line_nums_file(commit: Commit.Commit, file_name):
    for file in commit.files:
        if file.filename == file_name:
            file_commit_diff = file.patch
            raw_file_diff_lines = file_commit_diff.split("\n")
            block_start_idxs = []
            for idx, raw_line in enumerate(raw_file_diff_lines):
                if raw_line[0] == "@":
                    block_start_idxs.append(idx)
            starting_line_numbers = []
            for idx in block_start_idxs:
                block_header = raw_file_diff_lines[idx]
                sub1_lst = re.findall(r"@@.+@@", block_header)
                header = sub1_lst[0]
                sub2_lst = re.findall(r"-\d+", header)
                deleted_line_starting_num = int(sub2_lst[0].replace("-", ""))
                starting_line_numbers.append(deleted_line_starting_num)

            blocks = []
            cur_block = []
            for idx, raw_line in enumerate(raw_file_diff_lines):
                if idx in block_start_idxs:
                    if cur_block:
                        blocks.append(cur_block)
                    cur_block = []
                    continue
                cur_block.append(raw_line)
            blocks.append(cur_block)

            deleted_line_numbers = []
            for idx, block in enumerate(blocks):
                starting_line_number = starting_line_numbers[idx]
                line_num = 0
                for i, code_line in enumerate(block):
                    if (
                        code_line[0] == "+"
                    ):  # remove those plus lines cuz they are still in there
                        continue
                    if code_line[0] == "-":
                        deleted_line_numbers.append(starting_line_number + line_num)
                    line_num += 1
            return deleted_line_numbers

    return []


# def get_deleted_line_nums_file(diff, file_name):
#     for file in commit.files:
#         if file.filename == file_name:
#             file_commit_diff = file.patch
#             raw_file_diff_lines = file_commit_diff.split("\n")
#             block_start_idxs = []
#             for idx, raw_line in enumerate(raw_file_diff_lines):
#                 if raw_line[0] == "@":
#                     block_start_idxs.append(idx)
#             starting_line_numbers = []
#             for idx in block_start_idxs:
#                 block_header = raw_file_diff_lines[idx]
#                 sub1_lst = re.findall(r"@@.+@@", block_header)
#                 header = sub1_lst[0]
#                 sub2_lst = re.findall(r"-\d+", header)
#                 deleted_line_starting_num = int(sub2_lst[0].replace("-", ""))
#                 starting_line_numbers.append(deleted_line_starting_num)

#             blocks = []
#             cur_block = []
#             for idx, raw_line in enumerate(raw_file_diff_lines):
#                 if idx in block_start_idxs:
#                     if cur_block:
#                         blocks.append(cur_block)
#                     cur_block = []
#                     continue
#                 cur_block.append(raw_line)
#             blocks.append(cur_block)

#             deleted_line_numbers = []
#             for idx, block in enumerate(blocks):
#                 starting_line_number = starting_line_numbers[idx]
#                 line_num = 0
#                 for i, code_line in enumerate(block):
#                     if (
#                         code_line[0] == "+"
#                     ):  # remove those plus lines cuz they are still in there
#                         continue
#                     if code_line[0] == "-":
#                         deleted_line_numbers.append(starting_line_number + line_num)
#                     line_num += 1
#             return deleted_line_numbers

#     return []


def get_commit_id(commit_url):
    ls1 = commit_url.split("/")
    return ls1[6]


# Original implementation
# def get_patches(commit):
#     if 'files' not in commit:
#         raise ValueError(f'Commit {commit} does not return any changed files')
#     return "".join([get_patch(file) for file in commit['files']])

# def get_patch(file):
#     patch = repr(file['patch']) + "\n" if 'patch' in file else ""
#     return f"--- a/{file['filename']}\n+++ b/{file['filename']}\n" + patch

# def get_patches(commit):
#     """Get the patches of a commit based on pygithub's Commit object"""
#     if len(commit.files) == 0:
#         raise ValueError(f'Commit {commit} does not return any changed files')

#     changes = []
#     for file in commit.files:
#         changes.append(f"File: {file.filename}")
#         changes.append(f"Status: {file.status}")
#         changes.append("```diff\n" + file.patch + "\n```\n\n")

#     return "\n".join(changes).strip()+"\n"


def highlight_git_diff(raw_diff: str) -> str:
    """
    Highlights a git diff in unified format.

    Args:
        raw_diff (str): Raw git diff in unified format.

    Returns:
        str: Highlighted version of the git diff.
    """
    raw_diff = raw_diff.strip()
    lines = raw_diff.split("\n")
    highlighted_diff = []
    highlighted_diff.extend(lines[:5])

    def is_comment_line(line):
        line = line.strip()
        # Detect comment lines in Java code
        return (
            line.startswith("*")
            or line.startswith("/**")
            or line.startswith("*/")
            or line.startswith("//")
        )

    for line in lines[5:]:
        # line = line.strip()
        # if line.startswith("+++") or line.startswith("---"):
        #     # Mark the file name lines
        #     # highlighted_diff.append(f"# FILE: {line[4:]}")
        #     highlighted_diff.append(line)
        # elif line.startswith("@@"):
        #     # Mark the diff hunk headers
        #     # highlighted_diff.append(f"@@ HUNK: {line[3:]} @@")
        #     highlighted_diff.append(line)
        # el
        if line.startswith("+"):
            # Highlight added lines
            variation = "COMMENT" if is_comment_line(line[1:]) else "CODE"
            highlighted_diff.append(f"{f'ADDED {variation} LINE |':20} {line[1:]}")
        elif line.startswith("-"):
            # Highlight removed lines
            variation = "COMMENT" if is_comment_line(line[1:]) else "CODE"
            highlighted_diff.append(f"{f'REMOVED {variation} LINE |':20} {line[1:]}")
        else:
            # Keep unchanged lines
            highlighted_diff.append(f"{'UNCHANGED LINE |':20} {line}")

    return "\n".join(highlighted_diff)


def get_patches(commit_url):
    match = re.search(
        r"https?://github\.com/([^/]+/[^/]+)/commit/([a-f0-9]+)", commit_url
    )
    if not match:
        raise ValueError(f"Invalid commit URL: {commit_url}")

    repo_name = match.group(1).split("/")[1]
    commit_id = match.group(2)
    git_reset_cmd = (
        "cd Projects/" + str(repo_name) + " ; " + f"git diff {commit_id}^ {commit_id}"
    )
    git_diff = subprocess.run(
        git_reset_cmd, stdout=subprocess.PIPE, text=True, shell=True, cwd=cur_dir
    ).stdout

    return git_diff


# def format_output(raw_output):
#     matches = re.search(r"({[^}]+})" , raw_output)

#     if matches:
#         json_str = matches[0]
#         json_str = re.sub(r'{\s\n*', '{', json_str)
#         json_str = re.sub(r'\n*\s*}', '}', json_str)
#         json_str = re.sub(r'\n\s*', '\n', json_str)
#         json_str = re.sub(r'[^,]\n', r'\\n', json_str)
#         json_str = json_str.replace("'", '').replace('\\','')

#         try:
#             json_output = json.loads(json_str)
#             return f"{json_output['type']}: {json_output['subject']}\n{json_output.get('body', '')}"
#         except json.JSONDecodeError:
#             return raw_output
#     else:
#         try:
#             json_output = json.loads(raw_output)
#             return f"{json_output['type']}: {json_output['subject']}\n{json_output.get('body', '')}"
#         except json.JSONDecodeError:
#             matches = re.search(r'Type\s*:(.*)Subject\s*:(.*)Body\s*:(.*)',raw_output, flags=re.DOTALL)
#             if matches:
#                 return f"{matches.group(1).strip()}: {matches.group(2).strip()}\n{matches.group(3).strip()}"
#             else:
#                 return raw_output


def format_output(raw_output):
    if isinstance(raw_output, dict):
        try:
            subject = (
                re.search(r"(.*?:\s*)?(.*)", raw_output["subject"], re.DOTALL)
                .group(2)
                .replace("\\", "")
            )
            body = raw_output.get("body", "")
            if body:
                body = (
                    re.search(r"(.*?:\s*)?(.*)", body, re.DOTALL)
                    .group(2)
                    .replace("\\", "")
                )

            return f"{raw_output['type']}: {subject}\n{body}".strip()
        except KeyError:
            return str(raw_output)

    matches = re.search(
        r'({[\s\n]*(\s*".+"\s*:\s*".*"[,\s\n]*)+[\s\n]*})', raw_output, re.DOTALL
    )

    if matches:
        json_str = matches[0]
        matches = re.match(
            r'{\s*"type"\s*:\s*"(.*)",\s*"subject":\s*"(.*?)"(,\s*"body"\s*:\s*"(.*?)")?,?\s*}',
            json_str,
            re.DOTALL,
        )
        try:
            cm_type = matches.group(1)
            subject = (
                re.match("(.*?:\s*)?(.*)", matches.group(2)).group(0).replace("\\", "")
            )
            body = re.sub(r"\\[^n]", "", matches.group(4)) if matches.group(4) else ""

            return f"{cm_type}: {subject}\n{body}".strip()
        except:
            return raw_output
    else:
        try:
            json_output = json.loads(raw_output)
            return f"{json_output['type']}: {json_output['subject']}\n{json_output.get('body', '')}"
        except json.JSONDecodeError:
            matches = re.search(
                r"Type\s*:(.*)Subject\s*:(.*)Body\s*:(.*)",
                raw_output,
                flags=re.DOTALL | re.IGNORECASE,
            )
            if matches:
                return f"{matches.group(1).strip()}: {matches.group(2).strip()}\n{matches.group(3).strip()}"
            else:
                return raw_output


def process_class(path):
    forbidden_start = re.compile(r"^\s*(\n|/\*|\*|\*/|package|import)")
    with open(path, "r") as f:
        lines = f.readlines()
        i = 0
        while forbidden_start.match(lines[i]):
            i += 1
        content = "".join(lines[i:])
    return content


if __name__ == "__main__":
    project = "directory-server"
    sha = "9cbf06fcae73d281aa4804e574335d12fd0764ec"
    print(get_file_names(sha, project))
