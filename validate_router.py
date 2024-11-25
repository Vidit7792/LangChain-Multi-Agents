from fastapi import APIRouter
from fastapi import BackgroundTasks, Depends, HTTPException
from utils.model_classes import ExceptionMessageEnum , ValidateSkills
from utils.model_classes import Message
from fastapi.security.api_key import APIKey
import authentication.auth as auth
from dotenv import load_dotenv
from utils.config import log_entry_exit
import logging
from features import knowledge
from langchain.schema import HumanMessage,AIMessage
from langchain.schema import HumanMessage,AIMessage
import json

from fastapi import HTTPException
from utils.common import get_user_details
from utils.prompt import global_system_prompt
from .build_router import initiate_chat
load_dotenv()


job_object = {}

validate_router = APIRouter()


class ConversationManager:
    def __init__(self):
        self.conversation = {}

conversation_manager = ConversationManager()

@log_entry_exit
@validate_router.get("/validate/skills")
def query_knowledge_graph(user_id : str, api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Query KG
    '''
    try:
        user_details = get_user_details(user_id)
        user_name = user_details['first_name']+' '+ user_details['last_name']
        res = knowledge.fetch_validation_json(user_name, user_id)  
        return res
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))


@log_entry_exit
@validate_router.post("/initiate/chat")
def initiate_validate_chat(user_id : str, skill : ValidateSkills,api_key: APIKey = Depends(auth.get_api_key)):
    '''
    Initiate Chat
    '''
    try:
    
        user_details = get_user_details(user_id)
        user_name = user_details['first_name']+' '+ user_details['last_name']
        

        system_prompt = global_system_prompt.format(skills_json = json.dumps(skill.json()))
        
        conversation_manager.conversation[f'{user_id}'] = initiate_chat(user_name,system_prompt)
        
        return skill
    
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))


def save_status( user_id, skill, status, conversation):
    user_details = get_user_details(user_id)
    user_name = user_details['first_name']+' '+ user_details['last_name']


    chat_history = dict(conversation.memory.chat_memory)['messages']
    chat_history_formatted = []
    for msg in chat_history:
        msg_dict = {}
        if type(msg) == HumanMessage:
            msg_dict[f'{user_name}'] = msg.content
        if type(msg) == AIMessage:
            msg_dict['Skillo'] = msg.content

        chat_history_formatted.append(msg_dict)

    knowledge.store_status( user_id, skill, status, json.dumps(chat_history_formatted) )  

    

@log_entry_exit
@validate_router.post("/validate/chat")
def chat(background_tasks: BackgroundTasks, user_id : str, skill : str, message: Message):
    if conversation_manager.conversation[f'{user_id}'] is None:
        raise HTTPException(status_code=400, detail="Conversation not initialized or deleted")
    
    chat_response = conversation_manager.conversation[f'{user_id}']({"content": message.content})['text']

    status = ''
    if 'bye' in chat_response.lower() or 'goodbye' in chat_response.lower() or 'successful' in chat_response.lower():
        print("Bye")
        if 'successful' in chat_response.lower():
            status = 'Validated'
        else:
            status = 'Not Validated'

        background_tasks.add_task(save_status, user_id , json.loads(skill), status, conversation_manager.conversation[f'{user_id}'] )
        
        chat_response = f'Skill is {status}!! ' + chat_response + ' Please click on X to end chat'


    print("chat response received")

    return chat_response


@log_entry_exit
@validate_router.get("/validate/chat/archive")
def query_knowledge_graph(user_id : str, api_key: APIKey = Depends(auth.get_api_key)):
    '''
    Fetch All Chat History for a User
    '''
    try:
        res = knowledge.retrieve_validation_chat(user_id)  
        return res
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))


