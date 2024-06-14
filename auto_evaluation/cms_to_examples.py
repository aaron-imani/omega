import jsonlines
import pandas as pd
from sklearn.model_selection import train_test_split


def generate_human_rating_example(row):
    return {
        "messages": [
            {"role": "system", "content": "You are a senior developer."},
            {
                "role": "user",
                "content": (
                    "You are tasked with evaluating a commit message from four aspects:\n"
                    "Rationality: Whether the commit message provides a logical explanation for the code change (Why information), and provides the commit type information.\n"
                    "Comprehensiveness: Whether the message describes a summary of what has been changed (What information), and also covers relevant important details.\n"
                    "Conciseness: Whether the message conveys information succinctly, ensuring readability and quick comprehension.\n"
                    "Expressiveness: Whether the message content is grammatically correct and fluent.\n"
                    "For each aspect, give an score on a 5-point Likert scale (0 for poor, 1 for marginal, 2 for acceptable, 3 for good, and 4 for excellent).\n"
                    f"The commit message is: \"{row['CM']}\"\n"
                    f"The changes are:\n{row['patch']}\n\n"
                    "Answer format:\n"
                    "{{'rationality':'YOUR SCORE', 'comprehensiveness':'YOUR SCORE', 'conciseness':'YOUR SCORE', 'expressiveness':'YOUR SCORE'}}"
                ),
            },
            {
                "role": "assistant",
                "content": f"{{'rationality':'{row['Rationality']}', 'comprehensiveness':'{row['Comprehensiveness']}', 'conciseness':'{row['Conciseness']}', 'expressiveness':'{row['Expressiveness']}'}}",
            },
        ]
    }



def convert_xlsx_to_jsonl(path, num_samples=5):
    df = pd.read_excel(path)

    # Trim column names after the first space
    df.columns = df.columns.str.split(" ").str[0]

    split_dfs = []
    for i in range(4, len(df.columns), 5):
        # Select columns from current index i to i+5, but not including the endpoint i+5
        split_df = df.iloc[:, i : i + 5]
        split_df = split_df.rename(columns={split_df.columns[0]: "CM"})
        split_df['patch'] = df['patch']
        split_dfs.append(split_df)

    df = pd.concat(split_dfs)
    
    train, test = train_test_split(df, test_size=0.4, random_state=42)
    test, val = train_test_split(test, test_size=0.5, random_state=42)

    with jsonlines.open("evaluation/train.jsonl", mode="w") as writer:
        for _, row in train.iterrows():
            writer.write(generate_human_rating_example(row))
      
    with jsonlines.open("evaluation/validation.jsonl", mode="w") as writer:
        for _, row in val.iterrows():
            writer.write(generate_human_rating_example(row))

    test.to_csv("evaluation/test.csv", index=False)


if __name__ == "__main__":
    import sys
    
    convert_xlsx_to_jsonl(
        "evaluation/evaluation_preprocessed.xlsx", int(sys.argv[1]) if len(sys.argv) > 1 else 50
    )
