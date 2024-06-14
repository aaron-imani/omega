from langchain.prompts import ChatPromptTemplate

from common.model_loader import model

# how_to_read = """A git diff lists each modified/added/deleted Java files information in the following format:
# * `--- a/file.java\\n+++ b/file.java`: indicating that in the following code lines
# Lines starting with `---` are lines that only occur in the old version `a/file.java`, i.e. are deleted in the new version `b/file.java
# Lines starting with `+++` are lines that only occur in the new version `b/file.java`,
# i.e. are added to the new version `b/file.java`. Lines that are not prefixed with `---` or `+++` are lines that occur in both versions, i.e. are unchanged and only listed as context.
# * The code changes are then shown as a list of hunks, where each hunk consists of:
#   * `@@ -5,8 +5,9 @@`: a hunk header that states that the hunk covers the lines 5 to 5 + 8 in the old version and lines 5 to 5 + 9 in the new version.
#   * then those lines are listed with:
#        the prefix `-`: for deleted lines
#        the prefix `+`: for added lines
#        no prefix: for unchanged lines
# """

how_to_read = """
Understanding a `git diff` in the unified format is crucial for interpreting code changes. Below, I will explain the structure and elements of a diff.

A diff displays the differences between two versions of files. Here is a typical structure:

diff --git a/file.txt b/file.txt
index abc1234..def5678 100644
--- a/file.txt
+++ b/file.txt
@@ -1,4 +1,4 @@
 Line 1
-Line 2
+Line 2 changed
 Line 3
 Line 4

Let's break down the key components:

1. **Header Lines**:
   - `diff --git a/file.txt b/file.txt`: This line indicates the files being compared, with `a/` representing the old version and `b/` the new version.
   - `index abc1234..def5678 100644`: This shows the SHA-1 checksums (hashes) of the old and new versions, and the file mode.

2. **File Indicators**:
   - `--- a/file.txt`: The `---` line indicates the old file path.
   - `+++ b/file.txt`: The `+++` line indicates the new file path.

3. **Hunk Headers**:
   - `@@ -1,4 +1,4 @@`: This line is the "hunk header." It shows the starting line numbers and the number of lines in the old and new versions. For example, `-1,4` means the hunk starts at line 1 in the old file and spans 4 lines, while `+1,4` means the same for the new file.

4. **Context Lines**:
   - ` Line 1`: Lines that are unchanged in both versions appear without any prefix.

5. **Deletion Lines**:
   - `-Line 2`: Lines that are removed from the old version are prefixed with a minus (`-`) sign.

6. **Addition Lines**:
   - `+Line 2 changed`: Lines that are added in the new version are prefixed with a plus (`+`) sign.

### Step-by-Step Reading Guide

1. **Identify the Files**: Look at the `diff --git` line to see which files are being compared.
2. **Understand the Changes**:
   - Examine the `index` line for version information.
   - Review the `---` and `+++` lines to know the old and new file paths.
3. **Analyze Each Hunk**:
   - Read the `@@` line to understand the affected line numbers and the number of lines.
   - Look at the context lines (without prefix) to understand the unchanged parts of the code.
   - Identify the deletions (lines prefixed with `-`) and additions (lines prefixed with `+`).
"""

# System message with reading instructions
# system_msg = f"You are a senior Java developer with a long experience in using Git. You are asked to review a git diff of a commit. Your task is to understand the diff and brief it for your team. {how_to_read}"

# V1
system_msg = "You are a senior Java developer with extensive experience in code review."
message = "Explain all the changes in the following diff:\n{diff}"

# What - Why
# system_msg = "You are a senior Java developer with extensive experience in code review."
# message = "Explain the following diff to me.\n{diff}\n\nOutput format:\n\nWhat is changed: (explain the changes)\nWhy is it changed: (expain potential reasons behind the change if obvious from the diff)"

# Changed lines question
# message = "What lines have changed? Explain.\n{diff}"

# Basic system message


prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            system_msg,
        ),
        ("user", message),
    ]
)

summarizer = prompt | model.bind(max_tokens=500)


def summarize_diff(diff):
    return summarizer.invoke({"diff": diff}).content
