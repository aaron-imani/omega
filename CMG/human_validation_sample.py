from argparse import ArgumentParser

import pandas as pd


def sample_predictions(args):
    df = pd.read_csv(args.prediction_path)
    # df = df[(df['AMG_BLEU'] < args.max_bleu) & (df['ROUGEL'] < args.max_rougeL) & (df['METEOR'] < args.max_meteor)]
    sample_size = min(args.sample_size, len(df))
    print(f"Sampling out of {len(df)} commit messages")
    sample = df.sample(n=sample_size, random_state=args.random_seed)
    sample["commit_url"] = sample.apply(
        lambda x: f"https://github.com/{x['project']}/commit/{x['commit']}", axis=1
    )

    # Move commit_url to the first column
    cols = sample.columns.tolist()
    cols = cols[-1:] + cols[:-1]

    # capitalize the first letter of the AMG column
    # sample["AMG"] = sample["AMG"].str.capitalize()
    sample = sample[cols]
    sample.to_csv("sample.csv", index=False)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("prediction_path", type=str)
    parser.add_argument("sample_size", type=int)
    parser.add_argument("--max-bleu", type=float, default=100.0)
    parser.add_argument("--max-rougeL", type=float, default=100.0)
    parser.add_argument("--max-meteor", type=float, default=100.0)
    # Use -r 13 to generate survey 3 sample
    parser.add_argument("-r", "--random-seed", type=int, default=12)

    args = parser.parse_args()
    sample_predictions(args)
