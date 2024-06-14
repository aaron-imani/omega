from common.model_loader import model

message = "Explain all the changes in the following diff:\n{diff}"


def summarize_diff(diff):
    return model.invoke(
        [{"role": "user", "content": message.format(diff=diff)}]
    ).content
