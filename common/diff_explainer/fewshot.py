import pickle
from pathlib import Path

from langchain.prompts import ChatPromptTemplate

from common.diff_explainer.zeroshot import system_msg
from common.model_loader import model

curdir = Path(__file__).parent.resolve()
with open(curdir / "fewshot_prompt.pkl", "rb") as f:
    fewshot_prompt = pickle.load(f)

final_fewshot_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_msg),
        fewshot_prompt,
        ("human", "Explain all the changes in the following diff:\n\n{input}"),
    ]
)
fewshot_summarizer = final_fewshot_prompt | model.bind(max_tokens=500)


def summarize_diff(diff):
    return fewshot_summarizer.invoke(input=diff).content
