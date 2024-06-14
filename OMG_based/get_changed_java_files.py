import os
import pathlib
import re
import subprocess

cur_dir = pathlib.Path(__file__).parent.resolve()
base_dir = cur_dir / "Projects"
commit_url_pattern = re.compile(
    r"https?://github\.com/([^/]+/[^/]+)/commit/([a-f0-9]+)"
)


def get_changed_java_files(commit_url):
    match = commit_url_pattern.match(commit_url)
    if not match:
        raise ValueError(f"Invalid commit URL: {commit_url}")

    repo_name = match.group(1).split("/")[1]
    commit_sha = match.group(2)

    # Construct the path to the specific repository
    repo_path = base_dir / repo_name

    # Ensure the repository path exists
    if not os.path.isdir(repo_path):
        raise FileNotFoundError(
            f"The repository '{repo_name}' was not found in '{base_dir}'."
        )

    # Define the git command to get the list of changed Java files
    git_diff_command = [
        "git",
        "diff",
        "--name-only",
        "--diff-filter=M",
        commit_sha + "^!",
        "--",
        "*.java",
    ]

    # Define the git command to get the content of a file at a specific commit
    def get_file_content(commit, filepath):
        git_show_command = ["git", "show", f"{commit}:{filepath}"]
        try:
            result = subprocess.run(
                git_show_command,
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"Error: {e.output}"

    def add_line_numbers(content):
        lines = content.split("\n")
        line_numbers = range(1, len(lines) + 1)
        return "\n".join(f"{i:4} | {line}" for i, line in zip(line_numbers, lines))

    try:
        # Run the git diff command
        result = subprocess.run(
            git_diff_command, cwd=repo_path, capture_output=True, text=True, check=True
        )
        changed_files = result.stdout.strip().split("\n")

        # Create a list to store the file contents before and after the commit
        file_contents = []

        for file in changed_files:
            if file:  # Check if the file string is not empty
                # Get the content of the file before the commit
                before_content = get_file_content(commit_sha + "^", file)
                before_content = add_line_numbers(before_content)
                # Get the content of the file after the commit
                after_content = get_file_content(commit_sha, file)
                after_content = add_line_numbers(after_content)

                # Append the content as a tuple to the list
                file_contents.append((file, before_content, after_content))

        return file_contents

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error running git command: {e.output}")


# Example usage
# Replace 'repo_name' and 'commit_sha' with actual values
if __name__ == "__main__":
    changed_files = get_changed_java_files(
        "https://github.com/apache/ant/commit/89aa7775a83989345756349f99bd3556780eafee"
    )
    for changed_file in changed_files:
        file, before_content, after_content = changed_file
        print(f"File: {file}")
        print("Before:")
        print(before_content)
        print("\n\nAfter:")
        print(after_content)
        print("\n" + "=" * 50 + "\n")
