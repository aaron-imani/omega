import json
import os
import pathlib

from git import Repo
from tqdm.auto import tqdm

cur_dir = pathlib.Path(__file__).parent.resolve()


with open(cur_dir / "repo_mapping.json", "r") as f:
    repo_mapping = json.load(f)


for repo in tqdm(repo_mapping.values()):
    repo_name = repo.split("/")[-1]
    if os.path.exists(f"{str(cur_dir)}/Projects/{repo_name}"):
        continue
    print(f"Cloning {repo_name}")
    Repo.clone_from(f"https://github.com/{repo}.git", f"OMG_code/Projects/{repo_name}")
