import pandas as pd

old = pd.read_csv("all-incontext-survey-1.csv")
new = pd.read_csv("enhanced-context.csv")

sample_rows = new.sample(15, random_state=12)
old = old[old["commit_url"].isin(sample_rows["commit_url"])]

survey_sample = pd.DataFrame(
    {
        "commit_url": sample_rows["commit_url"],
        "old": old["AMG"],
        "new": sample_rows["AMG"],
    }
)
survey_sample.to_csv("survey_sample.csv", index=False)
