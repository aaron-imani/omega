import os

os.environ["METHOD_SUMMARIES"] = "OLD"
os.environ["REMOVE_COMMENTS"] = "FALSE"

import pickle
import random
import re
import sys

import pandas as pd
from jsonlines import jsonlines
from langchain_core.documents import Document
from termcolor import colored
from tqdm import tqdm

sys.path.append("..")

from CMG.class_summarization.class_summarizer import *
from CMG.code_summarizer import _prepare_messages, summarize_method_body
from evaluation.evaluate_cm import evaluate_machine_generated_text

random.seed(42)


def _get_class_name(content: str) -> str:
    try:
        return re.findall(
            r"\b(?:public|protected|private)?\s*(?:static\s+|final\s+)*(?:class)\s+(\w+)",
            content,
        )[0]
    except IndexError:
        return None


def _colored_print(caption: str, value, baseline):
    color = "green" if value >= baseline else "red"
    print(f"{caption}: {colored(round(value,2), color)}")


def _prepare_class_summarization_records(use_retrieval):
    # Load the dataset
    with jsonlines.open("../dataset-classsum/data.jsonl") as reader:
        records = list(reader)

    if use_retrieval:
        # Create documents from the records
        documents = []

        for i, record in tqdm(
            enumerate(records),
            total=len(records),
            desc="Creating documents from records",
        ):
            doc = Document(record["content"])
            documents.append(doc)
            class_name = _get_class_name(record["content"])
            record.update({"class_name": class_name})

        inital_length = len(records)
        records = [record for record in records if record["class_name"] is not None]
        print(f"Removed {inital_length - len(records)} records without class names.")

        records = random.sample(records, 384)
        # Initialize the class summarizer
        documents = [
            Document(record["content"], metadata={"class_name": record["class_name"]})
            for record in records
        ]

        data = {"documents": documents, "records": records}
        pickle.dump(data, open("class_summaization_dataset_sample.pkl", "wb"))
    else:
        for record in tqdm(
            records, total=len(records), desc="Creating documents from records"
        ):
            class_name = _get_class_name(record["content"])
            record.update({"class_name": class_name})
        inital_length = len(records)
        records = [record for record in records if record["class_name"] is not None]
        print(f"Removed {inital_length - len(records)} records without class names.")

        records = random.sample(records, 384)
        data = {"records": records}

    return data


def evaluate_class_summaries(path="ToolValidation-Results/class_summaries"):
    model_names = []
    metrics = ["bleu", "meteor", "rougeL"]
    eval_basis = ["human", "gpt4"]

    for model_name in os.listdir(path):
        if not model_name.endswith(".jsonl"):
            continue
        model_names.append(model_name)
        if model_name.startswith("gpt"):
            with jsonlines.open(f"{path}/{model_name}") as reader:
                gpt4_data = list(reader)
            gpt4_references = [record["generated_summary"] for record in gpt4_data]
            human_references = [record["summary"] for record in gpt4_data]
    try:
        df = pd.read_csv("ToolValidation-Results/class_summaries_evaluation.csv")
        existing_models = df["model"].values
    except FileNotFoundError:
        columns = ["model"]
        for basis in eval_basis:
            for metric in metrics:
                columns.append(f"{basis}_{metric}")
        df = pd.DataFrame(columns=columns)
        existing_models = []

    data = []
    for model_name in tqdm(model_names, desc="Evaluating models"):
        name = model_name.split(".jsonl")[0]
        if name in existing_models:
            continue
        with jsonlines.open(f"{path}/{model_name}") as reader:
            summaries = list(reader)
        predictions = [record["generated_summary"] for record in summaries]
        human_eval = evaluate_machine_generated_text(human_references, predictions)
        gpt4_eval = evaluate_machine_generated_text(gpt4_references, predictions)

        # print(f"Evaluating {name}")
        eval_data = {"model": name}
        for metric in metrics:
            eval_data[f"human_{metric}"] = round(getattr(human_eval, metric), 2)
            eval_data[f"gpt4_{metric}"] = round(getattr(gpt4_eval, metric), 2)
        # evaluation = _evaluate_class_summaries(summaries)
        data.append(eval_data)

    df = df._append(data, ignore_index=True)
    df = df.sort_values(by=["gpt4_meteor", "gpt4_rougeL", "gpt4_bleu"], ascending=False)
    df.to_csv(f"ToolValidation-Results/class_summaries_evaluation.csv", index=False)


def estimate_class_summarization_price():
    import tiktoken

    encoding = tiktoken.encoding_for_model("gpt-4-turbo")

    if not os.path.exists("class_summaization_dataset_sample.pkl"):
        data = _prepare_class_summarization_records(False)
    else:
        data = pickle.load(open("class_summaization_dataset_sample.pkl", "rb"))

    records = data["records"]
    tokens = []
    output_tokens = len(records) * 50

    for record in records:
        messages = zeroshot_prompt.format_messages(code_block=record["content"])
        cur_tokens = 0
        for m in messages:
            cur_tokens += len(encoding.encode(m.content))

        tokens.append(cur_tokens)
    input_tokens = sum(tokens)
    print(f"Total tokens: {input_tokens+output_tokens}")
    print(f"Total cost: ${input_tokens/1e6*30 + output_tokens/1e6*60}")


def validate_class_summarizer(use_retrieval=False):
    if not os.path.exists("class_summaization_dataset_sample.pkl"):
        data = _prepare_class_summarization_records(use_retrieval)
    else:
        data = pickle.load(open("class_summaization_dataset_sample.pkl", "rb"))

    if use_retrieval:
        # Initialize the class summarizer
        init_class_summarizer(data["documents"], "dataset-classsum")

    records = data["records"]
    # Generating summaries for each class
    for record in tqdm(records, desc="Summarizing classes"):
        record.update({"summary": " ".join(record["summary"])})
        generated_summary = summarize_class(
            record["class_name"], use_retrieval, record["content"]
        )
        print(f"{record['class_name']}: {generated_summary}")
        record.update({"generated_summary": generated_summary})

    # Save the summaries
    with jsonlines.open(
        f"ToolValidation-Results/class_summaries/{model_name}.jsonl", "w"
    ) as writer:
        writer.write_all(records)


def validate_method_summarizer():
    validation_data = pd.read_csv("program_contexts/methdsum-test-sample.csv")

    for i, row in tqdm(
        validation_data.iterrows(),
        total=validation_data.shape[0],
        desc="Summarizing methods",
    ):
        generated_summary = summarize_method_body(row["raw_code"], row["label"])
        print(
            f"Generated Summary: {generated_summary}\nActual Summary: {row['comment']}\n\n"
        )
        validation_data.at[i, "generated_comment"] = generated_summary

    validation_data.to_csv(
        f"ToolValidation-Results/method_summaries/{model_name}.csv", index=False
    )
    references = validation_data["comment"].values
    predictions = validation_data["generated_comment"].values
    evaluation = evaluate_machine_generated_text(references, predictions)
    print(
        f"BLEU: {evaluation.bleu}\nMETEOR: {evaluation.meteor}\nROUGE-L: {evaluation.rougeL}"
    )


def estimate_method_summarization_price():
    import tiktoken

    encoding = tiktoken.encoding_for_model("gpt-4-turbo")
    validation_data = pd.read_csv("program_contexts/methdsum-test-sample.csv")
    tokens = []
    output_tokens = len(validation_data) * 50
    for i, row in tqdm(
        validation_data.iterrows(),
        total=validation_data.shape[0],
        desc="Calculating tokens",
    ):
        messages = _prepare_messages(row["raw_code"], row["label"])
        cur_tokens = 0
        for m in messages:
            cur_tokens += len(encoding.encode(m["content"]))

        tokens.append(cur_tokens)
    input_tokens = sum(tokens)
    print(f"Total tokens: {input_tokens+output_tokens}")
    print(f"Total cost: ${input_tokens/1e6*30 + output_tokens/1e6*60}")


def evaluate_method_summaries(path="ToolValidation-Results/method_summaries"):
    model_names = []
    metrics = ["bleu", "meteor", "rougeL"]
    eval_basis = ["human", "gpt4"]

    existing_generations = os.listdir(path)
    # gpt4_exists = any('gpt' in name for name in existing_generations)
    human_references_loaded = False

    for model_name in existing_generations:
        if not model_name.endswith(".csv"):
            continue
        model_names.append(model_name)
        # if model_name.startswith('gpt'):
        #     gpt4_data = pd.read_csv(f"{path}/{model_name}")
        #     gpt4_references = gpt4_data['generated_comment'].values
        #     human_references = gpt4_data['comment'].values
        # elif not gpt4_exists:
        if not human_references_loaded:
            data = pd.read_csv(f"{path}/{model_name}")
            human_references = data["comment"].values
            human_references_loaded = True

    try:
        df = pd.read_csv("ToolValidation-Results/method_summaries_evaluation.csv")
        existing_models = df["model"].values
    except FileNotFoundError:
        columns = ["model"]
        # for basis in eval_basis:
        for metric in metrics:
            columns.append(f"{metric}")
        df = pd.DataFrame(columns=columns)
        existing_models = []

    data = []
    for model_name in tqdm(model_names, desc="Evaluating models"):
        name = model_name.split(".csv")[0]
        if name in existing_models:
            continue
        summaries = pd.read_csv(f"{path}/{model_name}")
        predictions = summaries["generated_comment"].values
        human_eval = evaluate_machine_generated_text(human_references, predictions)
        # if gpt4_exists:
        #     gpt4_eval = evaluate_machine_generated_text(gpt4_references, predictions)

        # print(f"Evaluating {name}")
        eval_data = {"model": name}
        for metric in metrics:
            eval_data[f"{metric}"] = round(getattr(human_eval, metric), 2)
            # eval_data[f"gpt4_{metric}"] = round(getattr(gpt4_eval, metric), 2)
        # evaluation = _evaluate_class_summaries(summaries)
        data.append(eval_data)

    df = df._append(data, ignore_index=True)
    df = df.sort_values(by=["bleu", "meteor", "rougeL"], ascending=False)
    df.to_csv(f"ToolValidation-Results/method_summaries_evaluation.csv", index=False)


def validate_commit_type_classifier():
    from Agent_tools import get_git_diff_from_commit_url
    from sklearn.metrics import classification_report

    from CMG.commit_type_classifier import classifier

    def _extract_type(raw_response):
        raw_response = raw_response.lower()
        if "feat" in raw_response:
            return "a"
        if "fix" in raw_response:
            return "c"
        else:
            return "p"

    try:
        df = pd.read_csv(
            f"ToolValidation-Results/commit_type_classification/{model_name}.csv"
        )
        df["predicted_type"].fillna("", inplace=True)
    except FileNotFoundError:
        df = pd.read_csv(
            "../data/sma-dataset/preprocessed_1151-commits-labeled-with-maintenance-activities.csv"
        )
        df["predicted_type"] = ""

    for i, row in tqdm(
        df.iterrows(), total=df.shape[0], desc="Classifying commit types"
    ):
        commit_url = row["commitURL"]
        if row["predicted_type"] != "":
            continue
        diff = get_git_diff_from_commit_url(commit_url)
        try:
            response = classifier.invoke({"git_diff": diff})
            response = response.content.strip()
            prediction = _extract_type(response)
        except KeyboardInterrupt:
            break
        except Exception as e:
            prediction = "ERROR"
        print(f"Predicted: {prediction}\nActual: {row['label']}")
        df.at[i, "predicted_type"] = prediction

    df.to_csv(
        f"ToolValidation-Results/commit_type_classification/{model_name}.csv",
        index=False,
    )
    df = df[df["predicted_type"].isna() == False]
    df = df[df["predicted_type"] != "ERROR"]
    report = classification_report(
        df["label"].astype(str),
        df["predicted_type"].astype(str),
        labels=["a", "p", "c"],
        output_dict=True,
    )
    pd.DataFrame(report).to_csv(
        f"ToolValidation-Results/commit_type_classification/report_{model_name}.csv"
    )
    print("Accuracy:", round(report["accuracy"], 2))


if __name__ == "__main__":
    import os

    os.makedirs("ToolValidation-Results/class_summaries", exist_ok=True)
    os.makedirs("ToolValidation-Results/method_summaries", exist_ok=True)
    os.makedirs("ToolValidation-Results/commit_type_classification", exist_ok=True)

    model_name = model_loader.processed_model_name
    # print(model_name)
    # estimate_method_summarization_price()
    # estimate_class_summarization_price()

    # validate_class_summarizer()
    # evaluate_class_summaries()
    # validate_method_summarizer()
    # evaluate_method_summaries()

    validate_commit_type_classifier()
