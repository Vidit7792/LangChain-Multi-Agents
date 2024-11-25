from openai import OpenAI
import os
import json
from utils.config import log_entry_exit
from langchain_core.prompts.chat import ChatPromptTemplate
import time
from dotenv import load_dotenv
load_dotenv()

from langchain_openai import AzureChatOpenAI

llm = AzureChatOpenAI(
    openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_deployment=os.getenv("AZURE_OPENAI_GPT4O_DEPLOYMENT_NAME"),
    temperature=0,
    max_tokens=16384,
)


@log_entry_exit
def get_openai_response(system_msg, user_msg):

    chat_template = ChatPromptTemplate.from_messages(
        [
            ("system", system_msg),
            ("human", "{user_input}" ),
            
        ]
    )
    messages = chat_template.format_messages(
    user_input=user_msg
    )
    ai_message = llm.invoke(messages)
    return ai_message.content


EMBEDDING_MODEL = os.environ.get('EMBEDDING_MODEL')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)

@log_entry_exit
def get_embedding(text, model=EMBEDDING_MODEL):
   text = text.replace("\n", " ")
   return client.embeddings.create(input = [text], model=model).data[0].embedding