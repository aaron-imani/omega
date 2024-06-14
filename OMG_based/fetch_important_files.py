import os
import pathlib
import subprocess

cur_dir = pathlib.Path(__file__).parent.absolute()
program_contexts = cur_dir / "program_contexts"
template_path = program_contexts / "understand_commands_template.txt"
with open(template_path, "r") as f:
    commands_template = f.read()

temp_path = str(program_contexts / "temp.und")


def export_dependencies_csv(repo_name, commit_sha):
    repo_path = cur_dir / "Projects" / repo_name

    csv_path = program_contexts / "file_dependencies" / repo_name / f"{commit_sha}.csv"

    pairwise_csv_path = (
        program_contexts
        / "file_dependencies"
        / repo_name
        / f"pairwise-{commit_sha}.csv"
    )

    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    commands = (
        commands_template.replace("PROJECT_NAME", repo_name)
        .replace("PROJECT_PATH", str(repo_path))
        .replace("GITHASH", commit_sha)
        .replace("CSV_PATH", str(csv_path))
        .replace("PAIRWISE_PATH", str(pairwise_csv_path))
        .replace("TEMP_UND_PATH", temp_path)
    )

    commands_path = program_contexts / "understand_commands.txt"
    with open(commands_path, "w") as f:
        f.write(commands)

    subprocess.run(
        f"cd {repo_path}; git reset --hard {commit_sha}",
        stdout=subprocess.PIPE,
        text=True,
        shell=True,
    )
    cmd = f"cd {repo_path} ; {os.getenv('UNDERSTAND_PATH')} {str(commands_path)}"
    print(cmd)
    subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        text=True,
        shell=True,
    )


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    repo_name = "directory-server"
    sha = "9cbf06fcae73d281aa4804e574335d12fd0764ec"
    export_dependencies_csv(repo_name, sha)
