import json
import os
import re
import sys
from collections import namedtuple

sys.path.append(".")

import evaluate
import pandas as pd
import requests
from termcolor import colored

from .log_mxnet import log_mnext_score

# from nltk.translate.bleu_score import corpus_bleu
# from nltk.translate.bleu_score import SmoothingFunction
# cc = SmoothingFunction()

os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

bleu = evaluate.load("bleu")
rouge = evaluate.load("rouge")
meteor = evaluate.load("meteor")

Evaluation = namedtuple("Evaluation", ["bleu", "rougeL", "meteor", "bleurt"])


def fix_faulty_cm(cm):
    if not cm.startswith("{"):
        return cm
    dictionary = json.loads(cm)
    return dictionary.get("action_input", "")


def evaluate_machine_generated_text(
    references, predictions, bleurt_mode="off", print_results=False
):
    if isinstance(references, str):
        references = [references]
    if isinstance(predictions, str):
        predictions = [predictions]

    references = [re.sub(r"[^a-z0-9_ \.]", "", ref.lower()) for ref in references]
    # references = [re.sub(r'(<.*body.*>)','',ref) for ref in references]
    predictions = [re.sub(r"[^a-z0-9_ \.]", "", pred.lower()) for pred in predictions]
    # predictions = [re.sub(r'(<.*body.*>)','',pred) for pred in predictions]

    if bleurt_mode == "off":
        bleurt_score = 0
    else:
        if bleurt_mode == "remote":
            data = {"references": references, "predictions": predictions}
            response = requests.post("http://pyxis.ics.uci.edu:49998/bleurt", json=data)
            bleurt_score = float(response.content)
        else:
            bleurt_score = bleurt.compute(
                predictions=predictions, references=references
            )["scores"]
            # print(bleurt_score)
            bleurt_score = sum(bleurt_score) / len(bleurt_score)

    try:
        bleu_score = bleu.compute(
            predictions=predictions, references=references, smooth=True
        )
        bleu_score = bleu_score["bleu"] * 100
    except ZeroDivisionError:
        bleu_score = 0

    try:
        rouge_score = (
            rouge.compute(predictions=predictions, references=references)["rougeL"]
            * 100
        )
    except ZeroDivisionError:
        rouge_score = 0

    try:
        meteor_score = (
            meteor.compute(predictions=predictions, references=references)["meteor"]
            * 100
        )
    except ZeroDivisionError:
        meteor_score = 0

    evaluation = Evaluation(
        bleu=round(bleu_score, 2),
        rougeL=round(rouge_score, 2),
        meteor=round(meteor_score, 2),
        bleurt=round(bleurt_score, 2),
    )
    if print_results:
        print("BLEU:", evaluation.bleu)
        print("ROUGE-L:", evaluation.rougeL)
        print("METEOR:", evaluation.meteor)

    return evaluation


def _get_type(value):
    return value.split(":")[0].strip().lower()


def _get_type_agreement(predictions: pd.Series, references: pd.Series):
    type_predictions = predictions.apply(_get_type)
    type_references = references.apply(_get_type)

    agreement = type_predictions == type_references
    return sum(agreement) / len(agreement)


def _get_average_len_ratio(predictions: pd.Series, references: pd.Series):
    delta_lengths = []
    for pred, ref in zip(predictions, references):
        delta_lengths.append(len(pred) / len(ref))

    return sum(delta_lengths) / len(delta_lengths)


def evaluate_generation(
    predictions_path,
    reference_cols=["CMG"],
    prediction_col="AMG",
    bleurt_mode="off",
    basis_mode=False,
):
    df = pd.read_csv(predictions_path)
    if basis_mode:
        df = df[base_rows]

    df = df[df[prediction_col].notna()]
    print("Non-empty CMs:", len(df))
    # gt = pd.read_excel('../evaluation/evaluation_preprocessed.xlsx')
    # gt = gt[gt['commit'].isin(df['commit'])]
    gt = df

    df[prediction_col] = df[prediction_col].apply(fix_faulty_cm)
    valid_cms = df[prediction_col].str.match(".*:[^\n]*\n?.*", re.DOTALL)
    valid_cm_ratio = round(valid_cms.sum() / len(df) * 100, 2)
    print("Valid CM Ratio:", valid_cm_ratio)

    df = df[valid_cms]
    gt = gt[valid_cms]

    for reference_col in reference_cols:
        references = gt[reference_col].tolist()
        predictions = df[prediction_col].tolist()

        evaluation = evaluate_machine_generated_text(
            references, predictions, bleurt_mode
        )
        lmx_score = 0
        for ref, pred in zip(references, predictions):
            lmx_score += log_mnext_score([ref], pred)
        lmx_score /= len(references)

        type_agreement_omg = (
            _get_type_agreement(df[prediction_col], gt[reference_col]) * 100
        )
        delta_length = _get_average_len_ratio(df[prediction_col], gt[reference_col])

        # fira = gt['FIRA'].tolist()
        # evaluation_fira = evaluate_cm(references, fira, calculate_bert)
        # delta_length_fira = _get_average_len_ratio(gt['FIRA'], gt['CMG'])
        # print(colored('Baseline: FIRA', 'yellow'))
        # print_evaluation(evaluation_fira, calculate_bert)
        # print(f'Average Length Ratio: {delta_length_fira:.2f}')
        # print('---'*30)
        print(colored(f"Groundtruth: {reference_col}", "yellow"))
        print(f"Log-MXNet: {lmx_score*100:.2f}")
        print_evaluation(evaluation, bleurt_mode)
        print(f"Type Agreement: {type_agreement_omg:.2f}")
        print(f"Average Length Ratio: {delta_length:.2f}")
        print("---" * 30)

    if "HM" in gt.columns:
        references = gt["HM"].tolist()
        evaluation_human = evaluate_machine_generated_text(
            references, predictions, bleurt_mode
        )
        delta_length_human = _get_average_len_ratio(df[prediction_col], gt["HM"])

        lmx_human = 0
        for ref, pred in zip(references, predictions):
            lmx_human += log_mnext_score([ref], pred)
        lmx_human /= len(references)

        print(colored("Groundtruth: Human", "yellow"))
        print(f"Log-MXNet: {lmx_human*100:.2f}")
        print_evaluation(evaluation_human, bleurt_mode)
        print(f"Average Length Ratio: {delta_length_human:.2f}")


def print_evaluation(evaluation, bleurt_mode="off"):
    print(f"BLEU: {evaluation.bleu:.2f}")
    print(f"ROUGE-L: {evaluation.rougeL:.2f}")
    print(f"METEOR: {evaluation.meteor:.2f}")
    if bleurt_mode != "off":
        print(f"BLEURT-20: {evaluation.bleurt:.2f}")


def evaluate_rows(
    prediction_path, reference_cols=["CMG"], prediction_col="AMG", bleurt_mode="off"
):
    from tqdm import tqdm

    df = pd.read_csv(prediction_path)
    for reference_col in reference_cols:
        col_name = f"{prediction_col}_{reference_col}"
        for i, row in tqdm(df.iterrows(), total=len(df)):
            row_eval = evaluate_machine_generated_text(
                row[reference_col], row[prediction_col], bleurt_mode
            )
            df.at[i, col_name + "_BLEU"] = row_eval.bleu
            df.at[i, col_name + "_ROUGEL"] = row_eval.rougeL
            df.at[i, col_name + "_METEOR"] = row_eval.meteor
            df.at[i, col_name + "_BLEURT"] = row_eval.bleurt

    df.to_csv(prediction_path, index=False)


def store_all_cms(filenames, calculate_bert=False):
    all_cms = {}
    method_mode = filenames[0].split("-")[0]
    model_name = "default"

    for file_name in filenames:
        if file_name.endswith("_all.csv"):
            continue
        splitted = file_name.split(".csv")[0]
        splitted = splitted.split("-")

        if len(splitted) > 1:
            method_mode = "-".join(splitted[1:])
        else:
            method_mode = "ReAct"
            model_name = file_name.split(".csv")[0]

        df = pd.read_csv(file_name)
        if "HM" not in all_cms:
            all_cms["HM"] = df["HM"]

        all_cms[method_mode] = df["AMG"].astype(str)

    final_df = pd.DataFrame(all_cms)

    references = final_df["ReAct"].tolist()

    print(colored("Comparing against ReAct", "cyan"))
    for col in final_df.columns:
        if col in ["ReAct", "HM"]:
            continue
        predictions = final_df[col].tolist()
        evaluation = evaluate_machine_generated_text(
            references, predictions, calculate_bert
        )
        print(colored(f"Method: {col}", "yellow"))
        print(f"BLEU: {evaluation.bleu:.2f}")
        print(f"ROUGE-L: {evaluation.rougeL:.2f}")
        print(f"METEOR: {evaluation.meteor:.2f}")
        if calculate_bert:
            print(f"BLEURT: {evaluation.bleurt:.2f}")
        print("---" * 30)

    gt = pd.read_excel("../evaluation/evaluation_preprocessed.xlsx")
    omg = gt["CMG"]
    final_df["OMG"] = omg
    final_df.to_csv(f"{model_name}_all.csv", index=False)


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("file_names", nargs="+", help="File names to evaluate")
    parser.add_argument(
        "mode", choices=["all", "rows"], default="all", help="Evaluation mode"
    )
    parser.add_argument(
        "--store-cms",
        action="store_true",
        help="Store the generated commit messages in one file",
    )
    parser.add_argument(
        "--basis",
        help="Basis file to be used for evaluation. Used when comparing an ablative version of a model. Use the ablated model file as the basis.",
    )
    parser.add_argument(
        "--bleurt",
        choices=["off", "local", "remote"],
        default="off",
        help="Calculate BLEURT score",
    )
    parser.add_argument(
        "-r",
        "--reference-cols",
        nargs="+",
        default=["CMG"],
        help="Reference column name",
    )
    parser.add_argument(
        "-p", "--prediction-col", default="AMG", help="Prediction column name"
    )
    args = parser.parse_args()

    if args.bleurt == "local":
        bleurt = evaluate.load("bleurt", "BLEURT-20", device="cuda")

    global basis_mode, base_rows
    basis_mode = args.basis
    if basis_mode:
        basis = pd.read_csv(basis_mode)
        base_rows = basis[args.prediction_col].notna()

    for f_name in args.file_names:
        if f_name.endswith("_all.csv"):
            continue
        print(
            colored("--" * 20, "green"),
            f"Evaluating: {f_name}",
            colored("--" * 20, "green"),
        )
        if args.mode == "all":
            evaluate_generation(
                f_name, args.reference_cols, args.prediction_col, args.bleurt
            )
        else:
            evaluate_rows(f_name, args.reference_cols, args.prediction_col, args.bleurt)

    if args.store_cms:
        store_all_cms(args.file_names)

        # print(colored('---'*40, 'green'))
    # evaluate_generation(sys.argv[1])
    # evaluate_generation('wizardlm2.csv')
