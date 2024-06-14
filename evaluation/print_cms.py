import pandas as pd
from termcolor import colored


def _print_csv(file_path, cols, metrics=["BLEU", "ROUGEL", "METEOR"]):
    df = pd.read_csv(file_path)
    print_df(df, cols, metrics)


def print_df(df, cols, metrics=["BLEU", "ROUGEL", "METEOR"], references=["OMG"]):
    for _, row in df.iterrows():
        commit_url = f'https://github.com/{row["project"]}/commit/{row["commit"]}'
        print("Commit URL:", colored(commit_url, "blue"))
        print(colored(f"OMG:", "green"), row["OMG"], end="\n\n")

        for col in cols:
            print(colored(f"{col}:", "yellow"), row[col])
            for metric in metrics:
                for ref in references:
                    try:
                        print(
                            colored(f"{col}_{ref}_{metric}:", "light_cyan"),
                            row[f"{col}_{ref}_{metric}"],
                        )
                    except KeyError:
                        continue
            print()
            # print('~~'*20)

        print("--" * 20)


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("file_path", help="File path to print")
    parser.add_argument("cols", nargs="+", help="Columns to print")
    args = parser.parse_args()

    _print_csv(args.file_path, args.cols)
