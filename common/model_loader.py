import os
from typing import List

from dotenv import load_dotenv
from langchain_community.chat_models.ollama import ChatOllama
from langchain_community.embeddings.ollama import OllamaEmbeddings
from langchain_community.llms.ollama import Ollama
from langchain_openai import ChatOpenAI, OpenAI, OpenAIEmbeddings

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
from langchain.globals import set_llm_cache
from langchain_community.cache import SQLiteCache

set_llm_cache(SQLiteCache(database_path=".langchain.db"))


assert (
    os.getenv("USE_OPEN_SOURCE") is not None
), "Please set the USE_OPEN_SOURCE variable in the .env file."

temperature = float(os.getenv("MODEL_TEMPERATURE"))
using_open_source = os.getenv("USE_OPEN_SOURCE") == "1"
if using_open_source:
    raw_model_name = os.getenv("MODEL_NAME")
    base_url = os.getenv("OLLAMA_SERVER")
else:
    raw_model_name = "gpt-4-turbo"

processed_model_name = raw_model_name.split("/")[-1].replace(":", "-")


def make_chat_model(base_url, model_name, server_type, temperature=0.0):
    if server_type == "ollama":
        return ChatOllama(
            base_url=base_url,
            model=model_name,
            temperature=temperature,
            num_ctx=8196,
        )
    else:
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key="lm-studio",
            base_url=base_url,
        )


def make_completion_model(model_name, server_type, base_url, temperature=0.0):
    if server_type == "ollama":
        return Ollama(model=model_name, temperature=temperature, base_url=base_url)
    else:
        return OpenAI(
            model_name=model_name,
            temperature=temperature,
            api_key="lm-studio",
            base_url=base_url,
        )


def make_embeddings_model(server_type, base_url, model_name):
    if server_type == "ollama":
        return OllamaEmbeddings(base_url=base_url, model=model_name)
    else:
        return OpenAIEmbeddings(
            disallowed_special=(),
            base_url=base_url,
            api_key="lm-studio",
            model=model_name,
        )


if not using_open_source:
    embeddings = OpenAIEmbeddings(disallowed_special=())
    model = ChatOpenAI(model=raw_model_name, temperature=0)
    path_prefix = "GPT-4"
else:
    assert (
        raw_model_name is not None
    ), "Please set the model name in the .env file. Do so by adding a line 'MODEL_NAME=your_model_name'."

    server_type = os.getenv("OLLM_SERVER_TYPE")

    if server_type == "ollama":
        from ollama_python.endpoints import ModelManagementAPI

        api = ModelManagementAPI(base_url=base_url + "/api")
        if not any(
            [model.name == raw_model_name for model in api.list_local_models().models]
        ):
            print(f"{raw_model_name} not present in the server. Pulling it.")
            api.pull(raw_model_name)

        embeddings = OllamaEmbeddings(base_url=base_url, model=raw_model_name)
        model = ChatOllama(
            base_url=base_url,
            model=raw_model_name,
            temperature=temperature,
            num_ctx=8196,
        )
        completion_model = Ollama(
            model=raw_model_name, temperature=temperature, base_url=base_url
        )

        if raw_model_name.startswith("llama3"):
            model = model.bind(stop=["<|eot_id|>"])
    else:
        embeddings = OpenAIEmbeddings(
            disallowed_special=(), base_url=base_url, api_key="lm-studio"
        )
        model = ChatOpenAI(
            model=raw_model_name,
            temperature=temperature,
            api_key="lm-studio",
            base_url=base_url,
        )
        completion_model = OpenAI(
            model_name=raw_model_name,
            temperature=temperature,
            api_key="lm-studio",
            base_url=base_url,
        )


def ask_llm(messages: List[str], verbose=False, **kwargs):
    client = OpenAI(
        base_url=base_url,
        api_key="lm-studio" if os.getenv("USE_OPEN_SOURCE") == "1" else None,
    )

    completion = client.chat.completions.create(
        model=raw_model_name,
        messages=[{"role": "user", "content": m} for m in messages],
        temperature=0,
        seed=0,
        **kwargs,
    )
    if verbose == True:
        print(completion.usage)

    return completion.choices[0].message.content
