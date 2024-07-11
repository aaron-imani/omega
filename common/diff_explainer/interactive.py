from common.log_config import get_logger
from common.model_loader import is_instruction_tuned, model
from diff_describer import describer

logger = get_logger("DiffSummarizer")

diff_reading_instruction = """A git diff lists modified/added/deleted Java files information in the following format:
`--- a/file.java\\n+++ b/file.java`: indicates the files being compared, with `a/` representing the name of the modified file before the commit and `b/` the name of the modified file after the commit.
The changes to the file are then shown as a list of hunks, where each hunk consists of:
1. A hunk header like '@@ -5,8 +5,9 @@' that states that the hunk covers the lines 5 to 13 (5+8) before the commit and lines 5 to 14 (5+9) after the commit.
2. In each hunk, changed lines are listed with:
    The prefix '+': for added lines
    The prefix '-': for deleted lines
3. Unchanged lines are listed with no prefix and are present in both the old and new versions.

Hint: Replaced lines can be seen as a sequence of deleted lines followed by a sequence added lines.
"""
# """
# To read a diff, follow these steps:
# 1. Find hunk headers to identify the lines being compared.
# 2. Look for added and deleted lines in each hunk.
# 3. Identify unchanged lines to understand the context of the changes.
# 4. Calculate the difference between the old and new versions of the file by comparing the added, deleted, and unchanged lines.
# 5. Realize the replacement of lines by observing chunks of deleted and added lines.
# """

# instructions = model.invoke(
#     [
#         ("system", "You are a senior Java developer"),
#         ("human", "How can I understand the changes in a universal git diff?"),
#     ],
#     frequency_penalty=1,
# ).content
# logger.info(f"Diff reading instructions: {instructions}")

if is_instruction_tuned:
    base_messages = [
        (
            "system",
            "You are a senior Java developer. Answer my questions factually and precisely.",
        )
    ]
else:
    base_messages = [
        (
            "human",
            "You are a senior Java developer. Answer my questions factually and precisely.",
        ),
        ("ai", "I am ready to answer your questions. How can I help?"),
    ]


def summarize_diff(diff):
    messages = base_messages + [
        ("human", "How can I read a git diff?"),
        ("ai", diff_reading_instruction),
        (
            "human",
            f"Follow the instructed steps for the following diff:\n\n{diff}",
        ),
        ("ai", describer.get_descriptions(diff)),
        (
            "human",
            # "TLDR. Just describe the changes into one paragraph without unnecessary details.",
            "Thank you! So, what are the differences between the old and new versions of each changed file?\n\n"
            "- Be careful about the different statement types, e.g., Javadoc, method call, variable declaration, etc.\n"  # Cite fan2024exploringcapabilitiesllmscode
            "- Be mindful about the order of lines in the diff.\n"  # To ensure the diff is intact we expliclty mentioned
            "- Be careful about any indentations or code style/formatting changes.",  # Cite OMG paper
        ),
    ]
    response = model.invoke(
        messages,
        max_tokens=1000,
        # frequency_penalty=0.5,
    ).content

    # response = model.invoke(
    #     [
    #         (
    #             "system",
    #             "You are a helpful AI assisstant with expertise in Java programming and Git. Answer my questions factually.",
    #         ),
    #         (
    #             "user",
    #             f"{diff_reading_instruction}\n\nDescribe all the changes made in the following diff:\n"
    #             + diff,
    #         ),
    #         ("ai", describer.get_descriptions(diff)),
    #         (
    #             "human",
    #             # "Based on the changes you reported and the unchanged lines in the diff, what has the developer done to the code? Summarize in a fluent paragraph.",
    #             # "For the replaced lines, tell the differences between the old and new version. For all the added/removed/replaced lines, specify the statement type (e.g., variable declaration, method call, Javadoc, comment, etc.). Lastly, send the corrected report.",
    #             "Send the report again. This time, for the replaced lines, tell the differences between the old and new version. For all the added/removed/replaced lines, specify the statement type (e.g., variable declaration, method call, Javadoc, comment, etc.).",
    #         ),
    #     ],
    #     max_tokens=500,
    #     # frequency_penalty=0.5,
    # ).content

    logger.info(response)
    return response
