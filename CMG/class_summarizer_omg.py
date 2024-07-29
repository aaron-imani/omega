import os
import pathlib
import shutil

# from langchain.prompts import PromptTemplate
import subprocess
import sys

if ".." not in sys.path:
    sys.path.append("..")

import CMG.cache_manager as cache_manager
import common.model_loader as model_loader

# HUGGINGFACEHUB_API_TOKEN
# os.environ['ACTIVELOOP_TOKEN'] = "your key"
# os.environ['HUGGINGFACEHUB_API_TOKEN'] = "your key"
# from langchain.chains.retrieval_qa.base import RetrievalQA
from CMG.class_summarization.class_summarizer import summarize_class

# from langchain_openai import OpenAIEmbeddings
# from langchain_community.embeddings import HuggingFaceHubEmbeddings
# from langchain.embeddings.ollama import OllamaEmbeddings
# from langchain.text_splitter import CharacterTextSplitter
# from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
# from langchain_openai import ChatOpenAI
# from langchain_community.chat_models.ollama import ChatOllama
# from langchain_community.document_loaders.text import TextLoader
# from langchain_community.vectorstores.deeplake import DeepLake
# from langchain.vectorstores.faiss import FAISS
from CMG.utils import (
    get_added_line_nums_file,
    get_commit_from_github,
    get_commit_id,
    get_deleted_line_nums_file,
    get_file_names,
    get_repo_name,
    git_reset,
    run_java_jar,
)

model = model_loader.model
embeddings = model_loader.embeddings

cur_dir = pathlib.Path(__file__).parent.resolve()
program_contexts_path = cur_dir / "program_contexts"
projects_dir = cur_dir / "Projects"

added_dir = program_contexts_path / "code_und_dirs/added"
modified_before_dir = program_contexts_path / "code_und_dirs/modified/before"
modified_after_dir = program_contexts_path / "code_und_dirs/modified/after"
deleted_dir = program_contexts_path / "code_und_dirs/deleted"
# text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)


def _clone_repo(repo_name):
    if not os.path.exists(projects_dir / repo_name):
        git_clone_cmd = f"cd {projects_dir} ; git clone {repo_name}"
        subprocess.run(
            git_clone_cmd, stdout=subprocess.PIPE, text=True, shell=True
        ).stdout


def _overwrite_folder(path):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)


# temp path is for saving the changed files in a commit


# class name is the changed class name in a commit
def class_sum(commit_url, use_cache=True):
    # https://docs.activeloop.ai/tutorials/deep-lake-vector-store-in-langchain
    # put changed files in a commit into temp_path (before or after)
    # class_name is from
    if use_cache:
        cached_class_sum = cache_manager.get_execution_value(
            commit_url, "OLD_class_sum"
        )
        if cached_class_sum:
            # cached_class_sum += "\n\nNow, proceed to the next step by using other tools if needed. If you are done, you can proceed to generate the Final Answer."
            return cached_class_sum
    try:
        commit = get_commit_from_github(commit_url)
    except ValueError as e:
        return "The tool did not receive a commit URL as input. Please provide the commit URL as input parameter."

    repo_name = get_repo_name(commit_url)
    # commit_id = commit.sha
    commit_id = get_commit_id(commit_url)
    changed_files, status = get_file_names(repo_name, commit_id)

    added_files = []
    modified_files = []
    deleted_files = []

    for name, s in zip(changed_files, status):
        if s == "added":
            added_files.append(name)
        if s == "modified":
            modified_files.append(name)
        if s == "removed":
            deleted_files.append(name)

    _overwrite_folder(added_dir)
    _overwrite_folder(deleted_dir)
    _overwrite_folder(modified_before_dir)
    _overwrite_folder(modified_after_dir)

    # if not os.path.exists(added_dir):
    #     os.makedirs(added_dir)
    # else:
    #     shutil.rmtree(added_dir)
    #     os.makedirs(added_dir)

    # if not os.path.exists(deleted_dir):
    #     os.makedirs(deleted_dir)

    # if not os.path.exists(modified_before_dir):
    #     os.makedirs(modified_before_dir)
    # if not os.path.exists(modified_after_dir):
    #     os.makedirs(modified_after_dir)

    _clone_repo(repo_name)

    repo_dir = projects_dir / repo_name

    git_reset(repo_dir, commit_id + "^1")

    for file in deleted_files:
        shutil.copy(
            repo_dir / file,
            deleted_dir / file.split("/")[-1],
        )
    for file in modified_files:
        shutil.copy(
            repo_dir / file,
            modified_before_dir / file.split("/")[-1],
        )

    git_reset(repo_dir, commit_id)

    for file in added_files:
        shutil.copy(
            repo_dir / file,
            added_dir / file.split("/")[-1],
        )
    for file in modified_files:
        shutil.copy(
            repo_dir / file,
            modified_after_dir / file.split("/")[-1],
        )

    # 1. for deleted files, find out the class names
    # 2. for added files, find out the class names
    # 3. for modified files, for before, identify the minus line numbers, and compare them with class ranges to identify the class names (affected classes)
    # 4. for modified files, for after, identify the plus line numbers, and compare them with class ranges to identify the class names (affected classes)
    # 5. the answer should be the summaries of added, deleted and modified classes
    # When embedding them, I can do them in groups, deleted+modified_before then added+modified_after

    deleted_classes = []
    added_classes = []
    before_classes = []
    after_classes = []

    for deleted_file in os.listdir(deleted_dir):
        if not deleted_file.endswith(".java"):
            continue

        del_cls_ranges = run_java_jar(
            "class_body_names_ranges.jar", str(deleted_dir / deleted_file)
        )

        for cls_name_rang in del_cls_ranges:
            class_name = cls_name_rang.strip().split(":")[0]
            deleted_classes.append(class_name)

    for added_file in os.listdir(added_dir):
        if not added_file.endswith(".java"):
            continue

        add_cls_ranges = run_java_jar(
            "class_body_names_ranges.jar", str(added_dir / added_file)
        )

        for cls_name_rang in add_cls_ranges:
            class_name = cls_name_rang.strip().split(":")[0]
            added_classes.append(class_name)

    for modified_before_f in os.listdir(modified_before_dir):
        if not modified_before_f.endswith(".java"):
            continue
        git_file_name = ""
        for file_name in modified_files:
            if file_name.strip().split("/")[-1] == modified_before_f:
                git_file_name = file_name
                break
        if not git_file_name:
            break

        deleted_line_nums = get_deleted_line_nums_file(commit, git_file_name)
        mb_cls_ranges = run_java_jar(
            "class_body_names_ranges.jar", str(modified_before_dir / modified_before_f)
        )
        for cls_name_rang in mb_cls_ranges:
            class_name = cls_name_rang.strip().split(":")[0]
            starting_line_num = int(cls_name_rang.strip().split(":")[1].split(",")[0])
            ending_line_num = int(cls_name_rang.strip().split(":")[1].split(",")[1])
            for deleted_line_num in deleted_line_nums:
                if (
                    starting_line_num <= deleted_line_num
                    and deleted_line_num <= ending_line_num
                ):
                    if class_name not in before_classes:
                        before_classes.append(class_name)
                    else:
                        continue

    for modified_after_f in os.listdir(modified_after_dir):
        if not modified_after_f.endswith(".java"):
            continue
        git_file_name = ""
        for file_name in modified_files:
            if file_name.strip().split("/")[-1] == modified_after_f:
                git_file_name = file_name
                break
        if not git_file_name:
            break
        added_line_nums = get_added_line_nums_file(commit, git_file_name)
        ma_cls_ranges = run_java_jar(
            "class_body_names_ranges.jar", str(modified_after_dir / modified_after_f)
        )
        for cls_name_rang in ma_cls_ranges:
            class_name = cls_name_rang.strip().split(":")[0]
            starting_line_num = int(cls_name_rang.strip().split(":")[1].split(",")[0])
            ending_line_num = int(cls_name_rang.strip().split(":")[1].split(",")[1])
            for added_line_num in added_line_nums:
                if (
                    starting_line_num <= added_line_num
                    and added_line_num <= ending_line_num
                ):
                    if class_name not in after_classes:
                        after_classes.append(class_name)
                    else:
                        continue

    if not before_classes and not after_classes:
        if use_cache:
            cache_manager.store_execution_value(
                commit_url,
                "OLD_class_sum",
                "The code changes in this git diff are not located within any class body. They might be either import statement or comment changes.",
            )
        return "The code changes in this git diff are not located within any class body. They might be either import statement or comment changes."

    before_after_pairs = list(set(before_classes).union(set(after_classes)))

    # prompt_template = """You are an expert Java programmer. Use the following pieces of context to answer the question.

    # {context}

    # Question: {question}
    # Answer:"""
    # PROMPT = PromptTemplate(
    #     template=prompt_template, input_variables=["context", "question"]
    # )

    ans = ""

    # # deleted+mb
    # docs = []
    # for dirpath, dirnames, filenames in os.walk(deleted_dir):
    #     for file in filenames:
    #         if file.strip().endswith(".java"):
    #             try:
    #                 loader = TextLoader(os.path.join(dirpath, file), encoding='utf-8')
    #                 docs.extend(loader.load_and_split())
    #             except Exception as e:
    #                 pass

    # for dirpath, dirnames, filenames in os.walk(modified_before_dir):
    #     for file in filenames:
    #         if file.strip().endswith(".java"):
    #             try:
    #                 loader = TextLoader(os.path.join(dirpath, file), encoding='utf-8')
    #                 docs.extend(loader.load_and_split())
    #             except Exception as e:
    #                 pass

    # texts = text_splitter.split_documents(docs)

    # db = DeepLake(dataset_path=f"./deleted-mb", embedding=embeddings, verbose=False, overwrite=True)
    # # db.delete_dataset() # empty the db first
    # db.add_documents(texts)

    # # db = FAISS.from_documents(texts, embeddings)
    # # db.save_local('deleted_modified_db')

    # retriever = db.as_retriever(search_type='mmr')
    # retriever.search_kwargs['distance_metric'] = 'cos'
    # retriever.search_kwargs['fetch_k'] = 100 # Number of Documents to fetch to pass to MMR algorithm.
    # # retriever.search_kwargs['maximal_marginal_relevance'] = True
    # retriever.search_kwargs['k'] = 10 # k: Number of Documents to return. Defaults to 4

    # def filter(x):
    #     # filter based on path e.g. extension
    #     metadata = x["metadata"].data()["value"]
    #     return "java" in metadata["source"]

    # retriever.search_kwargs['filter'] = filter
    # qa = RetrievalQA.from_llm(model, retriever=retriever, prompt=PROMPT)

    # if deleted_classes:
    #     ans += "The summaries of the deleted classes are described as follows:\n"
    #     for class_name in deleted_classes:
    #         ans = ans + class_name + ": " + qa.invoke('What is the main functionality (summary) of the class {}? Please use less than 20 words'.format(class_name))['result'] + '\n'
    #     for deleted_f in os.listdir(deleted_dir):
    #         os.remove(deleted_dir + "/" + deleted_f)

    # if before_after_pairs:
    #     ans += "The summaries of the modified classes before the change of the git diff are described as follows:\n"
    #     for class_name in before_after_pairs:
    #         ans = ans + class_name + ": " + qa.invoke('What is the main functionality (summary) of the class {}? Please use less than 20 words'.format(class_name))['result'] + '\n'
    #     for modified_before_f in os.listdir(modified_before_dir):
    #         os.remove(modified_before_dir+ '/' +modified_before_f)

    if deleted_classes:
        ans += "The summaries of the deleted classes are described as follows:\n"
        for dirpath, dirnames, filenames in os.walk(deleted_dir):
            for file in filenames:
                if file.strip().endswith(".java"):
                    with open(os.path.join(dirpath, file), "r") as f:
                        class_body = f.read()
                    class_summary = summarize_class(class_body=class_body)
                    ans = ans + file.split(".java")[0] + ": " + class_summary + "\n"
        # for deleted_f in os.listdir(deleted_dir):
        #     os.remove(deleted_dir + "/" + deleted_f)

    if before_after_pairs:
        ans += "The summaries of the modified classes before the change of the git diff are described as follows:\n"
        # for class_name in before_after_pairs:
        for dirpath, dirnames, filenames in os.walk(modified_before_dir):
            for file in filenames:
                with open(os.path.join(dirpath, file), "r") as f:
                    class_body = f.read()
                class_summary = summarize_class(class_body=class_body)
                ans = ans + file.split(".java")[0] + ": " + class_summary + "\n"
        # for modified_before_f in os.listdir(modified_before_dir):
        #     os.remove(modified_before_dir+ '/' +modified_before_f)

    # # added+ma
    # docs = []
    # for dirpath, dirnames, filenames in os.walk(added_dir):
    #     for file in filenames:
    #         if file.strip().endswith(".java"):
    #             try:
    #                 loader = TextLoader(os.path.join(dirpath, file), encoding='utf-8')
    #                 docs.extend(loader.load_and_split())
    #             except Exception as e:
    #                 pass

    # for dirpath, dirnames, filenames in os.walk(modified_after_dir):
    #     for file in filenames:
    #         if file.strip().endswith(".java"):
    #             try:
    #                 loader = TextLoader(os.path.join(dirpath, file), encoding='utf-8')
    #                 docs.extend(loader.load_and_split())
    #             except Exception as e:
    #                 pass

    # # text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    # texts = text_splitter.split_documents(docs)

    # # db = DeepLake(dataset_path=f"hub://jiawl28/cxf-test1", embedding=embeddings, verbose=False)
    # db = DeepLake(dataset_path=f"./added-ma", embedding=embeddings, verbose=False, overwrite=True)
    # # db.delete_dataset()  # empty the db first
    # db.add_documents(texts)

    # retriever = db.as_retriever(search_type='mmr')
    # retriever.search_kwargs['distance_metric'] = 'cos'
    # retriever.search_kwargs['fetch_k'] = 100 # Number of Documents to fetch to pass to MMR algorithm.
    # # retriever.search_kwargs['maximal_marginal_relevance'] = True
    # retriever.search_kwargs['k'] = 10 # k: Number of Documents to return. Defaults to 4

    # retriever.search_kwargs['filter'] = filter
    # qa = RetrievalQA.from_llm(model, retriever=retriever, prompt=PROMPT)

    # if before_after_pairs:
    #     ans += "The summaries of the modified classes after the change of the git diff are described as follows:\n"
    #     for class_name in before_after_pairs:
    #         ans = ans + class_name + ": " + qa.invoke(
    #             'What is the main functionality (summary) of the class {}? Please use less than 20 words'.format(class_name))['result'] + '\n'
    #     for modified_after_f in os.listdir(modified_after_dir):
    #         os.remove(modified_after_dir+ '/' +modified_after_f)

    # if added_classes:
    #     ans += "The summaries of the newly added classes are described as follows:\n"
    #     for class_name in added_classes:
    #         ans = ans + class_name + ": " + qa.invoke(
    #             'What is the main functionality (summary) of the class {}? Please use less than 20 words'.format(class_name))['result'] + '\n'
    #     for added_f in os.listdir(added_dir):
    #         os.remove(added_dir + "/" + added_f)

    if before_after_pairs:
        ans += "The summaries of the modified classes after the change of the git diff are described as follows:\n"
        for dirpath, dirnames, filenames in os.walk(modified_after_dir):
            for file in filenames:
                if file.strip().endswith(".java"):
                    with open(os.path.join(dirpath, file), "r") as f:
                        class_body = f.read()
                    class_summary = summarize_class(class_body=class_body)
                    ans = ans + file.split(".java")[0] + ": " + class_summary + "\n"

    if added_classes:
        ans += "The summaries of the newly added classes are described as follows:\n"
        for dirpath, dirnames, filenames in os.walk(added_dir):
            for file in filenames:
                if file.strip().endswith(".java"):
                    with open(os.path.join(dirpath, file), "r") as f:
                        class_body = f.read()
                    class_summary = summarize_class(class_body=class_body)
                    ans = ans + file.split(".java")[0] + ": " + class_summary + "\n"
    if use_cache:
        cache_manager.store_execution_value(commit_url, "OLD_class_sum", ans)
    # ans += "\n\nNow, proceed to the next step by using other tools if needed. If you are done, you can proceed to generate the Final Answer."
    return ans


if __name__ == "__main__":
    # from argparse import ArgumentParser
    # parser = ArgumentParser()
    # parser.add_argument("project", type=str, help="Project name")
    # parser.add_argument("sha", type=str, help="Commit SHA")
    # try:
    #     args = parser.parse_args()
    #     project = args.project
    #     sha = args.sha
    # except:
    #     project = input("Enter the project name: ")
    #     sha = input("Enter the commit SHA: ")

    project = "apache/jena"
    sha = "01bc520eda0dce834d20a71c9b90781346570a57"
    commit_url = f"https://github.com/{project}/commit/{sha}"
    print(commit_url)

    print(class_sum(commit_url, False))
