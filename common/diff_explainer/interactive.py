from common.model_loader import model

instructions = model.invoke(
    [
        ("system", "You are a senior Java developer"),
        ("human", "How can I understand the changes in a universal git diff?"),
    ]
).content


def summarize_diff(diff):
    return model.invoke(
        [
            ("system", "You are a senior Java developer."),
            ("human", "How can I understand the changes in a universal git diff?"),
            ("ai", instructions),
            ("human", f"Explain the changes in the following diff:\n\n{diff}"),
        ],
        max_tokens=500,
    ).content
