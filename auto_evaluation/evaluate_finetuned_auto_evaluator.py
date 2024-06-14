from langchain_openai import ChatOpenAI
from langchain_community.chat_models.ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.prompts import ChatPromptTemplate, PromptTemplate
import jsonlines
from tqdm import tqdm
from langchain_community.callbacks import get_openai_callback
import json
from sklearn.metrics import cohen_kappa_score
from scipy.stats import spearmanr
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
import pandas as pd
import os


class Rating(BaseModel):
    rationality: int = Field(
        description="The rationality of the commit message on a scale of 0-4", ge=0, le=4
    )
    comprehensiveness: int = Field(
        description="The comprehensiveness of the commit message on a scale of 0-4", ge=0, le=4
    )
    conciseness: int = Field(
        description="The conciseness of the commit message on a scale of 0-4", ge=0, le=4
    )
    expressiveness: int = Field(
        description="The expressiveness of the commit message on a scale of 0-4", ge=0, le=4
    )

def _formatted_messages(cm, patch, fewshot=False):
    messages = [
                {"role": "system", "content": "You are a senior developer."},
            ]
    
    if fewshot:
        for example in fewshot_examples:
            messages.extend(example)
    
    messages.append({
                    "role": "user",
                    "content": (
                        "You are tasked with evaluating a commit message from four aspects:\n"
                        "Rationality: Whether the commit message provides a logical explanation for the code change (Why information), and provides the commit type information.\n"
                        "Comprehensiveness: Whether the message describes a summary of what has been changed (What information), and also covers relevant important details.\n"
                        "Conciseness: Whether the message conveys information as brief as possible, ensuring readability and quick comprehension.\n"
                        "Expressiveness: Whether the message content is grammatically correct and fluent.\n"
                        "For each aspect, give an score on a 5-point Likert scale (0 for poor, 1 for marginal, 2 for acceptable, 3 for good, and 4 for excellent).\n"
                        f"The commit message is: \"{cm}\"\n"
                        f"The changes are:\n{patch}\n\n"
                        "Answer format:\n"
                        "{{'rationality':'YOUR SCORE', 'comprehensiveness':'YOUR SCORE', 'conciseness':'YOUR SCORE', 'expressiveness':'YOUR SCORE'}}"
                    ),
                })
    return messages

def evaluate_finetuned_model(model_name, name, fewshot=False):
    gpt = ChatOpenAI(model=model_name, temperature=0.0, max_tokens=100)

    predictions = []
    with get_openai_callback() as cb:
        for _, item in tqdm(
            test_data.iterrows(), desc="Generating responses for test data", total=len(test_data)
        ):
            messages = _formatted_messages(item["CM"], item["patch"], fewshot=fewshot)
            response = json.loads(gpt.invoke(messages).content.replace('\'','\"').replace('{{', '{').replace('}}', '}'))
            predictions.append(
                {
                    "predictor": name,
                    "cm": item["CM"],
                    "patch": item["patch"],
                    "rationality": response["rationality"],
                    "comprehensiveness": response["comprehensiveness"],
                    "conciseness": response["conciseness"],
                    "expressiveness": response["expressiveness"],
                }
            )

        print(cb)

    df = pd.DataFrame(predictions)
    df.to_csv(f"evaluation/ratings_{name}.csv", index=False)


def evaluate_ollama_model(model_name, name, fewshot=False):
    # base_url = 'http://localhost:11434'
    base_url = 'http://128.195.42.240:49999'
    gpt = ChatOllama(base_url = base_url, model=model_name, temperature=0.0, num_predict=100, format="json")
    chain = gpt | parser

    predictions = []
    for _, item in tqdm(
        test_data.iterrows(), desc="Generating responses for test data", total=len(test_data)
    ):
        messages = _formatted_messages(item["CM"], item["patch"], fewshot=fewshot)
        response = chain.invoke(messages)

        try:
            predictions.append(
                {
                    "predictor": name,
                    "cm": item["CM"],
                    "patch": item["patch"],
                    "rationality": response["rationality"],
                    "comprehensiveness": response["comprehensiveness"],
                    "conciseness": response["conciseness"],
                    "expressiveness": response["expressiveness"],
                }
            )
        except KeyError:
            predictions.append(
                {
                    "predictor": name,
                    "cm": item["CM"],
                    "patch": item["patch"],
                    "rationality": response["rationality".capitalize()],
                    "comprehensiveness": response["comprehensiveness".capitalize()],
                    "conciseness": response["conciseness".capitalize()],
                    "expressiveness": response["expressiveness".capitalize()],
                }
            )

    df = pd.DataFrame(predictions)
    df.to_csv(f"evaluation/ratings_{name}.csv", index=False)


def validate_ratings(ratings_path):
    df = pd.read_csv(ratings_path)
    
    model_name = ratings_path.split("_")[-1].split(".")[0]

    # Calculate cohen's kappa and spearman correlation of the scored with the gold answers
    gold_answers = test_data

    evaluations = []
    
    print("--" * 20, f"Metrics for {model_name}", "--" * 20)
    average_spearman = 0
    average_kappa = 0

    for col in [
        "rationality",
        "comprehensiveness",
        "conciseness",
        "expressiveness",
    ]:
        
        kappa = cohen_kappa_score(gold_answers[col.capitalize()], df[col])
        spearman_statistic, p_value = spearmanr(gold_answers[col.capitalize()], df[col])
        print(f"{col.capitalize()} - Cohen's Kappa: {kappa}")
        print(
            f"{col.capitalize()} - Spearman Correlation Coefficient: {spearman_statistic}"
        )
        print("**" * 20)
        evaluations.append(
            {
                "metric": f"{col.capitalize()}",
                "kappa": kappa,
                "spearman": spearman_statistic,
                "p-value": p_value,
            }
        )
        average_spearman += spearman_statistic
        average_kappa += kappa

    print('\x1b[2K')

    eval_df = pd.DataFrame(evaluations)
    eval_df.to_csv(f"../evaluation/eval_{model_name}.csv", index=False)
    return average_kappa / 4, average_spearman / 4


if __name__ == "__main__":
    from dotenv import load_dotenv
    import jsonlines
    import random
    random.seed(42)

    with jsonlines.open("../evaluation/train.jsonl", "r") as f:
        examples = [item for item in f]
        examples = [item['messages'][1:] for item in examples]
        # Select 10 random examples for few-shot learning by a fixed seed
        fewshot_examples = random.sample(examples, 10)

    test_data = pd.read_csv("evaluation/test.csv")
    parser = JsonOutputParser(pydantic_object=Rating)
    # query_template = (
    #     "You are tasked with evaluating a commit message from four aspects:\n"
    #     "Rationality: Whether the commit message provides a logical explanation for the code change (Why information), and provides the commit type information.\n"
    #     "Comprehensiveness: Whether the message describes a summary of what has been changed (What information), and also covers relevant important details.\n"
    #     "Conciseness: Whether the message conveys information succinctly, ensuring readability and quick comprehension.\n"
    #     "Expressiveness: Whether the message content is grammatically correct and fluent.\n"
    #     "For each aspect, give an score on a 5-point Likert scale (0 for poor, 1 for marginal, 2 for acceptable, 3 for good, and 4 for excellent).\n"
    #     'The commit message is: "{cm}"\n'
    #     "The changes are:\n{patch}\n\n"
    #     "{format_instructions}"
    # )

    # prompt = PromptTemplate(
    #     template=query_template,
    #     input_variables=["cm", "patch"],
    #     partial_variables={"format_instructions": parser.get_format_instructions()},
    # )

    load_dotenv("../.env")

    # model_name = "ft:gpt-3.5-turbo-0125:sepe::99Mgd0ZP"
    # evaluate_finetuned_model(model_name, "finetuned-v1")

    # model_name = "gpt-4"
    # evaluate_finetuned_model(model_name, "gpt4-zeroshot")

    model_name = "gemma:latest"
    evaluate_ollama_model(model_name, model_name.replace(":", "-")+'-fewshot', fewshot=True)


    all_files = os.listdir("../evaluation")
    all_files = [f for f in all_files if f.startswith("ratings_") and f.endswith(".csv")]
    best_spear = 0
    best_model = ""
    for m in all_files:
        avg_kappa, avg_spear = validate_ratings(os.path.join("evaluation", m))
       
        if avg_spear > best_spear:
            best_spear = avg_spear
            best_model = m
    
    print(f"Best model: {best_model}")
    print(f"Best Spearman: {best_spear}")
