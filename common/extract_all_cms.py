import json
import os
import pathlib
import subprocess
from argparse import ArgumentParser

import pandas as pd
from tqdm.auto import tqdm

# script dir
script_dir = pathlib.Path(__file__).parent.resolve()

repo_mapping = json.load(open(script_dir / "repo_mapping.json"))

# Make keys lowercase
repo_mapping = {key.lower(): value for key, value in repo_mapping.items()}


def _retrieve_commits(project_path):
    cmd = ["git", "log", '--format="%H %s"']
    commits = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=project_path,
    ).stdout.split("\n")
    commits = [
        (commit.split(" ")[0].strip('" '), " ".join(commit.split(" ")[1:]))
        for commit in commits
        if commit != ""
    ]
    return commits


def _get_repo_name(project_name):
    project_name = project_name.lower()
    if project_name in repo_mapping:
        return repo_mapping[project_name]
    for key in repo_mapping:
        if key.find(project_name) != -1:
            return repo_mapping[key]


def _retrieve_all_commits(projects_path):
    projects_path = pathlib.Path(projects_path).resolve()
    projects = [project for project in os.listdir(projects_path)]
    records = []
    for project in tqdm(projects, desc="Retrieving commits for all projects"):
        project = projects_path / project
        repo_name = _get_repo_name(project.parts[-1])
        if repo_name == None:
            print(f"Skipping {project.parts[-1]}")
            continue
        project_commits = _retrieve_commits(project)
        for commit in project_commits:
            records.append(
                {
                    "commit_url": f"https://github.com/{repo_name}/commit/{commit[0]}",
                    "commit": commit[0],
                    "project": repo_name,
                    "HM": commit[1],
                }
            )

    return records


def _store_all_commits(projects_path, csv_path):
    commits = _retrieve_all_commits(projects_path)
    if not commits:
        print("No commits retrieved")
        return
    df = pd.DataFrame(commits)
    df.to_csv(csv_path, index=False)
    print(f"Retrieved {len(commits)} commits and stored them in {csv_path}")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("projects_path", type=str)
    parser.add_argument("csv_path", type=str)

    args = parser.parse_args()

    _store_all_commits(args.projects_path, args.csv_path)
