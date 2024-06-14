from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import Optional
from langchain.output_parsers import RetryOutputParser
from dotenv import load_dotenv
import os

load_dotenv('.env')
# Define your desired data structure.
class CommitMessage(BaseModel):
    type: str = Field(description="The software maintenance activity type of the commit")
    subject: str = Field(description="The subject of the commit message", max_length=75)
    body: Optional[str] = Field(description="The body of the commit message") 

zeroshot_parser = JsonOutputParser(pydantic_object=CommitMessage)

if os.getenv('USE_OPEN_SOURCE') == '0':
    from langchain_openai import OpenAI
    llm = OpenAI(temperature=0)
else:
    from langchain.llms.ollama import Ollama
    llm = Ollama(model=os.getenv('MODEL_NAME'), temperature=0)

retry_parser = RetryOutputParser.from_llm(parser=zeroshot_parser, llm=llm)
