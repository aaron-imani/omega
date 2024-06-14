import difflib
import re

from langchain.prompts import ChatPromptTemplate

from common.model_loader import model

system_message = (
    "You are a senior Java developer. You will be given a Java function and a list of changes that will be applied to it. "
    "Your task is to identify how applying those changes will affect the function's behavior from the following aspects: \n"
    "What: The changes in what the function does. \n"
    "Why: The reason why a method is provided or the design rationale of the method\n"
    "How-to-use: The usage or the expected set-up of using a method\n"
    "How-it-is-done: How the function does what it does\n"
    "Property: Properties of a method including pre-conditions or post-conditions of a method.\n\n"
    "You will be given the original function, its current behavior from the above aspects, and the changes that will be applied to it. "
)

prompt = ChatPromptTemplate.from_messages(
    [("system", system_message), ("human", "{input}")]
)

chain = prompt | model

hunk_regex = re.compile(r"@@ -(\d+),(\d+) \+(\d+),(\d+) @@")


def _get_changes(before, after):
    before_lines = before.split("\n")
    after_lines = after.split("\n")

    report = []
    for i, line in enumerate(before_lines, 1):
        report.append(f"{i:3} {line}")

    # Generate differences using difflib
    diff = list(difflib.unified_diff(before_lines, after_lines, lineterm=""))
    # Initialize lists to hold changes with line numbers
    added_lines = []
    removed_lines = []

    # Variables to track current line numbers in old and new files
    old_line_num = 0
    new_line_num = 0

    # Track changes
    for line in diff:
        if line.startswith("@@"):
            # Parse line number information
            parts = line.split(" ")
            old_line_info = parts[1].split(",")
            new_line_info = parts[2].split(",")

            old_line_num = int(old_line_info[0][1:])
            new_line_num = int(new_line_info[0][1:])
        elif line.startswith("+") and not line.startswith("+++"):
            added_lines.append((new_line_num, line[1:]))
            new_line_num += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed_lines.append((old_line_num, line[1:]))
            old_line_num += 1
        else:
            old_line_num += 1
            new_line_num += 1

    # Identify replaced lines
    replacement_pairs = []
    for (old_num, old_line), (new_num, new_line) in zip(removed_lines, added_lines):
        if old_line != new_line:
            replacement_pairs.append((old_num, new_num, old_line, new_line))

    # Filter out replacements from added and removed lists
    for old_num, new_num, old_line, new_line in replacement_pairs:
        removed_lines = [item for item in removed_lines if item[0] != old_num]
        added_lines = [item for item in added_lines if item[0] != new_num]

    changes = []
    # Output the results
    # print("Added lines:")
    for line_num, line in added_lines:
        changes.append(
            f'Addition: "{line.strip()}" will be added after line {line_num-1}'
        )
        # print(f"{line_num}: {line}", end="")

    # print("\nRemoved lines:")
    for line_num, line in removed_lines:
        changes.append(f"Removal: Line {line_num} will be removed")
        # print(f"{line_num}: {line}", end="")

    # print("\nReplaced lines:")
    for old_num, new_num, old_line, new_line in replacement_pairs:
        # print(f"Old {old_num}: {old_line}New {new_num}: {new_line}", end="")
        changes.append(
            f'Replacement: "{new_line.strip()}" will replace "{old_line.strip()}" in line {old_num}'
        )

    report = "\n".join(report) + "\n\n" + "\n".join(changes)
    return report


def summarize_method(before, after, before_summary):
    method_changes = _get_changes(before, after)
    message = (
        method_changes
        + "\n\n"
        + before_summary
        + "\n\nNow, please tell me how each aspect of the method will change after the changes are applied."
    )
    return chain.invoke({"input": message}).content
    # print(added, removed)
    # print(before)
    # print(after)
    # print("===")
    # return model(before, after, added, removed)
