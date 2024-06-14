import os
import subprocess
from difflib import unified_diff

import git
import javalang
from javalang.tree import (
    ClassReference,
    Invocation,
    MemberReference,
    MethodReference,
    SuperMemberReference,
    VoidClassReference,
)


# Function to get the body of a class or method from the AST node
def get_entity_body(node, source_lines):
    start_line = node.position.line
    # Find the end line by traversing node's children
    if hasattr(node, "body"):
        end_line = max(
            child.position.line for child in node.body if hasattr(child, "position")
        )
    else:
        end_line = start_line
    body_lines = source_lines[start_line - 1 : end_line + 1]
    body = "\n".join(body_lines)
    print(node.__dict__)
    return start_line, end_line, body


# Function to extract entities (classes, methods, imports) from Java code
def extract_entities(code):
    tree = javalang.parse.parse(code)
    source_lines = code.splitlines()
    entities = []

    for path, node in tree:
        if "farthest" in node.__dict__.values():
            print(type(node))
            print(node.__dict__, end="\n\n")
        # if isinstance(
        #     node,
        #     (
        #         Invocation,  # Function call
        #         MethodReference,  # Method reference
        #         MemberReference,  # Member reference
        #     ),
        # ):
        #     print(node.__dict__)
        # start_line, end_line, body = get_entity_body(node, source_lines)
        # entities.append((node.name, start_line, end_line, body))

    return entities


# Function to get the diff for a commit
def get_commit_diff(repo_path, commit_sha):
    repo = git.Repo(repo_path)
    commit = repo.commit(commit_sha)
    parent_commit = commit.parents[0]

    diff_data = parent_commit.diff(commit, create_patch=True)
    diffs = {}

    for diff in diff_data:
        if diff.a_path.endswith(".java"):
            diffs[diff.a_path] = diff.diff.decode()

    return diffs


# Function to get the file content at a specific commit
def get_file_content(repo_path, file_path, commit_sha):
    result = subprocess.run(
        ["git", "show", f"{commit_sha}:{file_path}"],
        cwd=repo_path,
        stdout=subprocess.PIPE,
        text=True,
    )
    return result.stdout


# Main function
def main(repo_path, commit_sha):
    diffs = get_commit_diff(repo_path, commit_sha)

    for file_path, diff in diffs.items():
        before_content = get_file_content(repo_path, file_path, f"{commit_sha}~1")
        after_content = get_file_content(repo_path, file_path, commit_sha)

        before_entities = extract_entities(before_content)
        # after_entities = extract_entities(after_content)

        diff_lines = list(
            unified_diff(before_content.splitlines(), after_content.splitlines())
        )

        print(f"File: {file_path}")
        print("--- Before:")
        before_index = after_index = 0
        Removals = []
        Additions = []

        # for entity in before_entities:
        #     if entity not in after_entities:
        #         print(f"{entity[0]}: Lines {entity[1]}-{entity[2]}\n{entity[3]}\n")
        # print("--- After:")
        # for entity in after_entities:
        #     print(f"{entity[0]}: Lines {entity[1]}-{entity[2]}\n{entity[3]}\n")

        print("--- Delta:")

        print("--- Diff:")
        print("\n".join(diff_lines))
        # print("\n\n")


if __name__ == "__main__":
    repo_path = "../OMG_based/Projects/directory-server"
    commit_sha = "9cbf06fcae73d281aa4804e574335d12fd0764ec"
    main(repo_path, commit_sha)
