import os
import re
from urllib import response

import openai
from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_community.vectorstores.deeplake import DeepLake
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

import common.model_loader as model_loader
from common.log_config import get_logger

logger = get_logger("ClassSummarizer")
model = model_loader.model
embeddings = model_loader.embeddings
path_prefix = model_loader.raw_model_name.replace("/", "-").replace(":", "-")

java_splitter = RecursiveCharacterTextSplitter.from_language(
    language=Language.JAVA, chunk_size=1000, chunk_overlap=0
)

zeroshot_template = (
    "You are an expert Java programmer. Whenever I send you a Java class, you should give me a one-line answer about what its main functionality is in less than 20 words.\n"
    # "- Your answer should be a summary of the class functionality in less than 20 words.\n"
    # "- Your answer should be concise and to the point.\n"
    # "- Your answer must not mention the class name or phrases such as 'This Java class' and similar. Use the allowed 20 words wisely."
    "Your answer must begin with a verb such as 'Creates', 'Handles', 'Initializes', etc.\n"
    "Write your answer to the point and avoid any introductory phrases.\n"
)

if model_loader.is_instruction_tuned:
    zeroshot_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", zeroshot_template),
            (
                "human",
                "What is the main functionality of the below Java class in a few words?\n```{code_block}\n```\n\nYour answer: (MUST START WITH A VERB)",
            ),
        ]
    )
else:
    zeroshot_prompt = ChatPromptTemplate.from_messages(
        [
            ("human", zeroshot_template),
            ("ai", "I am ready. Please send me the Java class."),
            (
                "human",
                "What is the main functionality of the below Java class in a few words?\n```{code_block}\n```\n\nYour answer: (MUST START WITH A VERB)",
            ),
        ]
    )
model = (
    model.bind(max_tokens=50)
    if isinstance(model, model_loader.ChatOpenAI)
    else model.bind(num_predict=50)
).bind(stop=["\n"])

chain = zeroshot_prompt | model


def filter(x):
    # filter based on path e.g. extension
    metadata = x["metadata"].data()["value"]
    return "java" in metadata["source"]


def strip_tags(text):
    # Define a regex pattern to match tags at the beginning or end of the string
    pattern = r"^<[^>]+>|<[^>]+>$"

    # Use re.sub to remove any matching tags
    cleaned_text = re.sub(pattern, "", text)

    return cleaned_text


def init_class_summarizer(documents, dataset_name, overwite=False, verbose=True):
    global qa

    dataset_path = os.path.join("DeepLake", path_prefix, dataset_name)

    if overwite or not os.path.exists(dataset_path):
        db = DeepLake(
            dataset_path=dataset_path,
            embedding=embeddings,
            verbose=False,
            overwrite=True,
        )
        if overwite:
            try:
                db.delete_dataset()
            except:
                DeepLake.force_delete_by_path(dataset_path)

        # texts = java_splitter.split_documents(documents)
        db.add_documents(documents)

    else:
        db = DeepLake(dataset_path=dataset_path, embedding=embeddings, read_only=True)

    retriever = db.as_retriever(
        # search_type="mmr",
        search_kwargs={
            "distance_metric": "cos",
            "fetch_k": 100,
            "k": 10,
            # "filter": filter,
        },
    )
    # retriever.search_kwargs['distance_metric'] = 'cos'
    # retriever.search_kwargs['fetch_k'] = 100 # Number of Documents to fetch to pass to MMR algorithm.
    # retriever.search_kwargs['maximal_marginal_relevance'] = True
    # retriever.search_kwargs['k'] = 10 # k: Number of Documents to return. Defaults to 4
    # system_template = ("You are an expert Java programmer. Use the following pieces of context to answer the question.\n\n"
    #     f"```\n{{context}}\n```\n\n"
    #     "- Your answer should be a summary of the class functionality in less than 20 words.\n"
    #     "- Your answer should be concise and to the point.\n"
    #     "- Your answer must start with a verb.\n"
    #     "- Your answer must not mention the class name. Use the 20 words wisely.\n\n"
    # )
    prompt_template = (
        "You are an expert Java programmer. Use the following pieces of context to answer the question.\n\n"
        "```\n{context}\n```\n\n"
        "- Your answer should be a summary of the class functionality in less than 20 words.\n"
        "- Your answer should be concise and to the point.\n"
        "- Your answer must start with a verb.\n"
        "- Your answer must not mention the class name. Use the 20 words wisely.\n\n"
        "Question: {question}\n"
        "Answer: "
    )

    PROMPT = PromptTemplate(
        template=prompt_template, input_variables=["context", "question"]
    )

    # qa = RetrievalQA.from_llm(model, retriever=retriever, prompt=PROMPT)
    qa = RetrievalQA.from_chain_type(
        model,
        retriever=retriever,
        chain_type_kwargs={"prompt": PROMPT, "verbose": True},
    )

    # First we need a prompt that we can pass into an LLM to generate this search query
    # prompt = ChatPromptTemplate.from_messages(
    #     [
    #         ("system", system_template),
    #         ("user", "Question: {input}"),
    #     ]
    # )
    # document_chain = create_stuff_documents_chain(model, prompt)

    # qa = create_retrieval_chain(retriever, document_chain)


def summarize_class(class_name=None, use_retrieval=False, class_body=None):
    # summary = qa.pick("answer").invoke({"input": f"What is the main functionality (summary) of the class {class_name}? Please use less than 20 words."}).strip()
    if use_retrieval:
        response = qa.invoke(
            f"What is the main functionality (summary) of the class {class_name}? Please use less than 20 words.",
            num_predict=30,
        )["result"].strip()
    else:
        try:
            response = chain.invoke({"code_block": class_body}).content.strip(' "')
            # summary = model_loader.ask_llm(["What is the main functionality of the below Java class in a few words?\n```\n" + class_body + "\n```\n Please answer in less than 20 words, starting with a verb."], verbose=True, max_tokens=50).strip(' "')
        except openai.BadRequestError as e:
            # summary = "Too long to summarize"
            error_msg = e.body["message"]
            logger.error(error_msg)

            if error_msg.startswith("This model's maximum context length is"):
                response = "Too long to summarize"

            else:
                response = "Error occurred while summarizing class"

    return strip_tags(response)


if __name__ == "__main__":
    from langchain_community.document_loaders.parsers.language import LanguageParser
    from langchain_text_splitters import Language
    from LenientLoader import LenientLoader

    project_name = "fop-cs/src/java/org/apache/fop/area"
    loader = LenientLoader.from_filesystem(
        f"../Projects/{project_name}",
        glob="**/*",
        suffixes=[".java"],
        parser=LanguageParser(language=Language.JAVA),
        show_progress=True,
    )
    documents = loader.load()

    print(f"Loaded {len(documents)} documents")
    print("Initializing class summarizer...")
    # os.makedirs('../FAISS/qpid', exist_ok=True)
    init_class_summarizer(documents, f"../DeepLake/{project_name}")
    print("Class summarizer initialized.")
    class_name = input("Enter the class name: ")
    while class_name != "q":
        print(f"Summarizing class {class_name}...")
        summary = summarize_class(class_name)
        print(f"Summary: {summary}")
        class_name = input("Enter the class name: ")
