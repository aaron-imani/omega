from openai import OpenAI
from dotenv import load_dotenv
import os
import time
import json
import tiktoken
load_dotenv("../.env")

def num_tokens_from_string(string: str) -> int:
    """Returns the number of tokens in a text string."""
    num_tokens = len(encoding.encode(string))
    return num_tokens

def fintuning_cost(num_tokens:int):
    # 8$ per million tokens https://openai.com/pricing
    return num_tokens / 1e6 * 8

def calculate_finetuning_cost(sample_path):
    import jsonlines
    with jsonlines.open(os.path.join(sample_path,"train.jsonl")) as reader:
        train_samples = list(reader)
    with jsonlines.open(os.path.join(sample_path,"validation.jsonl")) as reader:
        eval_samples = list(reader)
    
    train_tokens = sum([num_tokens_from_string(message["content"]) for sample in train_samples for message in sample['messages']])
    print("Train tokens:", train_tokens)
    eval_tokens = sum([num_tokens_from_string(message["content"]) for sample in eval_samples for message in sample['messages']])
    print("Validation tokens:", eval_tokens)
    total_tokens = train_tokens + eval_tokens
    print("Total tokens:", total_tokens)
    return fintuning_cost(total_tokens)

def schedule_finetuning_jon(client, sample_path)->str:
    """
    Schedule a fine-tuning job on OpenAI API based on the training and validation data provided.
    Args:
        train_path: Path to the training data file.
        validation_path: Path to the validation data file.

    Returns:
        job.id: The id of the fine-tuning job scheduled on OpenAI API.
    """
    training_data = client.files.create(
        file=open(os.path.join(sample_path,"train.jsonl"), "rb"), purpose="fine-tune"
    )
    results["training_file_id"] = training_data.id
    validation_data = client.files.create(
        file=open(os.path.join(sample_path,"validation.jsonl"), "rb"), purpose="fine-tune"
    )
    results["validation_file_id"] = validation_data.id

    job = client.fine_tuning.jobs.create(
        training_file=training_data.id, 
        validation_file=validation_data.id,
        model="gpt-3.5-turbo"
    )
    results["job_id"] = job.id
    return job.id

def monitor_finetuning_job(client, job_id):
    """
    Monitor the fine-tuning job on OpenAI API.
    Args:
        job_id: The id of the fine-tuning job scheduled on OpenAI API.
    """
    finetuned_model_name = None
    while True:
        job_info = client.fine_tuning.jobs.retrieve(job_id)
        if job_info.status == "succeeded":
            finetuned_model_name = job_info.model
            break
        elif job_info.status == "failed":
            break
        time.sleep(60)

    results["status"] = job_info.status
    results["finetuned_model_name"] = finetuned_model_name

    # Clean up the training and validation data files
    client.files.delete(results["training_file_id"])
    client.files.delete(results["validation_file_id"])

    f.write(json.dumps(results))

if __name__ == "__main__":
    from argparse import ArgumentParser
    import getpass

    os.makedirs("evaluation/fine_tuning", exist_ok=True)

    encoding = tiktoken.get_encoding("cl100k_base")

    f = open("evaluation/fine_tuning/results.json", "w")
    results = {"training_file_id": None, "validation_file_id": None,
        "job_id": None, "status": None}

    parser = ArgumentParser()
    parser.add_argument("-s", "--sample_path", type=str, required=True, help="Path to the sample data.")
    parser.add_argument("-t", "--token-ev-name", type=str, help="The environment variable name for the OpenAI API token.", default="OPENAI_TOKEN")
    args = parser.parse_args()

    client = OpenAI()
    token_name = args.token_ev_name
    client.api_key = os.getenv(token_name) if os.getenv(token_name) else getpass.getpass("Enter your OpenAI API key:")

    sample_path = args.sample_path
    cost = calculate_finetuning_cost(sample_path)
    print(f"Estimated fine-tuning cost for the sample data is: ${cost:.2f}")

    job_id = schedule_finetuning_jon(client, sample_path)
    f.write(json.dumps(results))
    monitor_finetuning_job(client, job_id)
    print("Fine-tuning is completed.")
    print("Fine-tuned model name is:", results["finetuned_model_name"])
    f.close()