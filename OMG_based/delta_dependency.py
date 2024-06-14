import os
import pathlib
import subprocess

import understand

from OMG_based.utils import git_reset

cur_dir = pathlib.Path(__file__).parent.absolute()
program_contexts = cur_dir / "program_contexts"
pre_template_path = program_contexts / "delta_dependency_pre_template.txt"
post_template_path = program_contexts / "delta_dependency_post_template.txt"

with open(pre_template_path, "r") as f:
    pre_template = f.read()
with open(post_template_path, "r") as f:
    post_template = f.read()

if __name__ == "__main__":
    os.environ["UNDERSTAND_PATH"] = "/home/alirezi/scitools/bin/linux64/und"

temp_dir = cur_dir / "temp"
os.makedirs(temp_dir, exist_ok=True)
delta_commands_path = temp_dir / "delta_command.txt"
und_cmd = f"{os.getenv('UNDERSTAND_PATH')} {str(delta_commands_path)}"


class EntList:
    def __init__(self, ent_list):
        self.ent_list = ent_list

    def __contains__(self, item):
        # Customize the containment check here
        # For example, by longname or kindname
        if isinstance(item, understand.Ent):
            for ent in self.ent_list:
                if (
                    ent.longname() == item.longname()
                    and ent.kind() == item.kind()
                    and ent.contents() == item.contents()
                ):
                    return True
        return False

    def __iter__(self):
        return iter(self.ent_list)

    def __len__(self):
        return len(self.ent_list)

    def __getitem__(self, index):
        return self.ent_list[index]


def get_entities_in_file(file_name, ents):
    ents = [ent for ent in ents if ent.ref().file().relname() == file_name]
    ents = sorted(ents, key=lambda ent: ent.ref().line())
    return EntList(ents)


def _process_und_command(cmd):
    with open(delta_commands_path, "w") as f:
        f.write(cmd)

    subprocess.run(
        und_cmd,
        stdout=subprocess.PIPE,
        text=True,
        shell=True,
    )


def make_und_dbs(repo_name, commit_sha):
    repo_path = cur_dir / "Projects" / repo_name
    parent_commit_sha = subprocess.run(
        f"git rev-parse {commit_sha}^", text=True, capture_output=True, cwd=repo_path
    ).stdout.strip()

    if os.path.exists(temp_dir / f"{repo_name}-{commit_sha}.und"):
        print("DB already exists")
        return

    pre_und_path = temp_dir / f"{repo_name}-{parent_commit_sha}.und"
    post_und_path = temp_dir / f"{repo_name}-{commit_sha}.und"

    pre_cmd = (
        pre_template.replace("REPO_PATH", str(repo_path))
        .replace("POST_UND_PATH", str(post_und_path))
        .replace("PRE_UND_PATH", str(pre_und_path))
        .replace("PARENT_COMMIT_SHA", parent_commit_sha)
    )
    post_cmd = (
        post_template.replace("REPO_PATH", str(repo_path))
        .replace("POST_UND_PATH", str(post_und_path))
        .replace("PARENT_COMMIT_SHA", parent_commit_sha)
        .replace("COMMIT_SHA", commit_sha)
    )

    git_reset(repo_path, commit_sha)
    _process_und_command(post_cmd)

    subprocess.run(
        ["git", "reset", "--hard", parent_commit_sha],
        stdout=subprocess.PIPE,
        text=True,
        shell=True,
        cwd=repo_path,
    )
    _process_und_command(pre_cmd)


# project_name = "cxf"
# commit_sha = "260efe56fc1bfc89950d1eda89114feb287490cd"

project_name = "directory-server"
commit_sha = "9cbf06fcae73d281aa4804e574335d12fd0764ec"
make_und_dbs(project_name, commit_sha)
# und_path = os.getenv("UNDERSTAND_PATH")

db_post = understand.open(f"temp/{project_name}-{commit_sha}.und")
db_pre = db_post.comparison_db()
assert db_pre is not None
print(db_pre.name())


# for ent in sorted(ents, key=lambda ent: ent.longname()):
#     ref = ent.ref("definein")
#     if ref is None:
#         continue
#     print(ent.longname(), "(", ent.parameters(), ")")
#     print(" ", ref.file().relname(), "(", ref.line(), ")")


def get_delta_ents(pre_ents, post_ents):
    added_ents = []
    removed_ents = []
    for ent in pre_ents:
        for post_ent in post_ents:
            if ent == post_ent:
                break
    for ent in post_ents:
        if ent not in pre_ents:
            added_ents.append(ent)

    for ent in pre_ents:
        if ent not in post_ents:
            removed_ents.append(ent)

    return added_ents, removed_ents


def print_ents(ents):
    for ent in ents:
        print(ent.kind(), ent.name())
        print("--" * 20)


def print_refs(refs):
    for ref in refs:
        print(ref.line(), ref.scope(), ref.kindname(), ref.ent())
        print("--" * 20)


file_name = "rt/rs/security/oauth-parent/oauth2/src/main/java/org/apache/cxf/rs/security/oauth2/common/Client.java"

# for file in db_post.lookup(
#     file_name,
#     "File",
# ):
#     # refs = file.filerefs()
#     # print_refs(refs)
#     print(file)
#     print_ents(file.ents())
#     depdencies = file.depends()
#     for ent, refs in depdencies.items():
#         print(ent.name())
#         print_refs(refs)
#         print("--" * 20)

# print(db_post.ents())

pre_ents = get_entities_in_file(
    file_name,
    db_pre.ents(),
)

post_ents = get_entities_in_file(
    file_name,
    db_post.ents(),
)

print("Pre Entities:")
print_ents(pre_ents)

print("\n\n\n")

print("Post Entities:")
print_ents(post_ents)

added_ents, removed_ents = get_delta_ents(pre_ents, post_ents)

print("Added Entities:")
print_ents(added_ents)

print("Removed Entities:")
print_ents(removed_ents)

db_post.close()
db_pre.close()

# Example usage
# if __name__ == "__main__":
#     from dotenv import load_dotenv

#     load_dotenv()

#     diff_text = """diff --git a/core/src/main/java/org/apache/directory/server/core/referral/ReferralLut.java b/core/src/main/java/org/apache/directory/server/core/referral/ReferralLut.java
# index 15321bd07f..e1ab28d7f0 100644
# --- a/core/src/main/java/org/apache/directory/server/core/referral/ReferralLut.java
# +++ b/core/src/main/java/org/apache/directory/server/core/referral/ReferralLut.java
# @@ -99,7 +99,7 @@ public class ReferralLut

#         for ( int ii = 0; ii < dn.size(); ii++ )
#         {
# -            farthest.add( dn.getRdn( ii ) );
# +            farthest.addNormalized( dn.getRdn( ii ) );

#             // do not return dn if it is the farthest referral
#             if ( isReferral( farthest ) && ( farthest.size() != dn.size() ) )
# """
#     udb_path = "program_contexts/temp.udb"  # Understand database file path
#     repo_path = "Projects/directory-server"  # Path to the local repository
#     und_path = os.getenv("UNDERSTAND_PATH")  # Path to the Understand executable

#     changed_references = analyze_references(diff_text, udb_path, repo_path)
#     # print(changed_references)
#     for file, refs in changed_references.items():
#         # print(f"File: {file}")
#         for ref in refs:
#             print(f"  Entity Type: {ref[0]}, Entity Name: {ref[1]}, Line: {ref[2]}")
