import sqlite3
from pathlib import Path
from typing import Literal, Union

if __name__ == "__main__":
    import sys

    sys.path.append("..")

from common.model_loader import processed_model_name as model_name

# Set up database paths
base_path = Path(Path(__file__).parent.resolve() / "cache")
db_path = base_path / f"{model_name}.db"
commits_db_path = base_path / "commits.db"


# Function to connect to a database
def connect_db(path):
    connection = sqlite3.connect(path)
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """
    )
    connection.commit()
    return connection


def get_model_db(model_name):
    db_path = base_path / f"{model_name}.db"
    db = connect_db(db_path)
    return db


def initiate_commits_db():
    connection = sqlite3.connect(commits_db_path)
    cursor = connection.cursor()
    tables = ["issues", "prs", "git_diff", "important_files"]
    for table in tables:
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table} (
                commit_url TEXT PRIMARY KEY,
                value TEXT
            )
        """
        )
        connection.commit()
    return connection


# Connect to databases
db = connect_db(db_path)
commits_db = initiate_commits_db()


# Utility functions for operations
def _get(cursor, key, keyname="key", table="cache"):
    command = f'SELECT value FROM {table} WHERE {keyname}="{key}"'
    cursor.execute(command)
    row = cursor.fetchone()
    return row[0] if row else None


def store_execution_value(commit_url, command, output):
    existing_output = _get(db.cursor(), commit_url)
    if existing_output is None:
        value = {command: output}
    else:
        value = eval(existing_output)  # Convert string back to dictionary
        value[command] = output
    db.cursor().execute(
        "REPLACE INTO cache (key, value) VALUES (?, ?)", (commit_url, str(value))
    )
    db.commit()


def get_execution_value(commit_url, command, model_name=None):
    if model_name:
        cur_db = get_model_db(model_name)
    else:
        cur_db = db

    execution_value = _get(cur_db.cursor(), commit_url)
    if execution_value is None:
        return None
    execution_value = eval(execution_value)  # Convert string back to dictionary
    if model_name:
        cur_db.close()
    return execution_value.get(command)


def delete_execution_value(command):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM cache")
    row = cursor.fetchall()
    vals = [eval(i[1]) for i in row]

    for v in vals:
        if command in v:
            print(f"Deleting {command} from cache")
            del v[command]

    for i, v in enumerate(vals):
        db.cursor().execute(
            "REPLACE INTO cache (key, value) VALUES (?, ?)", (row[i][0], str(v))
        )

    db.commit()


def store_commit_data(
    commit_url,
    metadata: Union[
        Literal["prs"],
        Literal["issues"],
        Literal["git_diff"],
        Literal["important_files"],
    ],
    value,
):
    commits_db.cursor().execute(
        f"REPLACE INTO {metadata} (commit_url, value) VALUES (?, ?)",
        (commit_url, str(value)),
    )
    commits_db.commit()


def delete_commit_data(metadata):
    commits_db.cursor().execute(f"DELETE FROM {metadata}")
    commits_db.commit()


def get_commit_data(
    commit_url,
    metadata: Union[
        Literal["prs"],
        Literal["issues"],
        Literal["git_diff"],
        Literal["important_files"],
    ],
):
    return _get(commits_db.cursor(), commit_url, table=metadata, keyname="commit_url")


# Test to see how many items are cached
print(
    "Cached model's values:",
    db.cursor().execute("SELECT COUNT(*) FROM cache").fetchone()[0],
)

for table in ["issues", "prs", "git_diff", "important_files"]:
    print(
        f"Cached {table}:",
        commits_db.cursor().execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0],
    )

# delete_commit_data("prs")
# delete_commit_data("issues")

# delete_execution_value("diff_summary")
# delete_execution_value("class_sum")
# delete_execution_value("generate_multi_intent_summaries")
