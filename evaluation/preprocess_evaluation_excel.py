import pandas as pd
import json
from tqdm import tqdm
import os
from dotenv import load_dotenv
from github import Github

load_dotenv('../.env')
repos = dict()
github_token = os.getenv("GITHUB_API_TOKEN")
if not github_token:
    import getpass
    github_token = getpass.getpass("Enter your GitHub token:")

g = Github(github_token)

def get_commit_diff(repo_name, commit_sha):
    repo = repos.get(repo_name)
    
    if not repo:
        repo = g.get_repo(repo_name)
        repos[repo_name] = repo

    commit = repo.get_commit(commit_sha)

    changes = []
    for file in commit.files:
        changes.append(f"File: {file.filename}")
        changes.append(f"Status: {file.status}")
        changes.append("```diff\n" + file.patch + "\n```\n\n")

    return "\n".join(changes).strip()
        
path = "evaluation/Final_evaluation_Samples.xlsx"
df = pd.read_excel(path)

with open("evaluation/repo_mapping.json") as f:
    repo_mapping = json.load(f)
df['project'] = df['project'].map(repo_mapping)

tqdm.pandas(desc="Downloading patches", total=len(df))
patch_values = df.progress_apply(lambda row: get_commit_diff(row['project'], row['commit']), axis=1)
df.insert(3, 'patch', patch_values)
df.to_excel("evaluation/evaluation_preprocessed.xlsx", index=False)