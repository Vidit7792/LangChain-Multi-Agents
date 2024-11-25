from fastapi import APIRouter
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException
from utils.model_classes import ExceptionMessageEnum , ValidateSkills, User , LoginCredentials, UserProfile
from http import HTTPStatus
from utils.model_classes import Job, StatusEnum,Status,ResultStatus,Message,SkillMapper
from fastapi.security.api_key import APIKey
import authentication.auth as auth
from dotenv import load_dotenv
from utils.config import log_entry_exit
import logging
from features import knowledge,enrichment,extract_text_utils
from fastapi import File, UploadFile
from langchain.schema import HumanMessage,AIMessage, messages_from_dict, messages_to_dict
from langchain.memory.chat_message_histories.in_memory import ChatMessageHistory
from langchain.schema import HumanMessage,AIMessage
from langchain_community.chat_models import ChatOpenAI
from langchain.memory import ConversationSummaryBufferMemory
import json
from langchain.chains import LLMChain
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
)

import base64
from integration import neo4j_integration, azur_blob_storage
from utils import neo_utils
from utils.common import get_user_details
from fastapi import HTTPException
load_dotenv()


job_object = {}

default_router = APIRouter()


def get_transaction_id_details(userid: str):
   
    query = f"MATCH (u:User {{userid: '{userid}'}}) RETURN u.transaction_id as transaction_id "
    result = neo4j_integration.get_neo4j_response(query)
    
    # Retrieve the first record from the result
    record = result[0]
    if record:
        return {
            "transaction_id": record["transaction_id"]
        }
    else:
        raise HTTPException(status_code=404, detail="User not found")


@log_entry_exit
def enrich_graph(pdf_file, job):
    '''
    Enrich Graph
    '''
    try:
        # Process and cleanse conversation Inputs
        res = enrichment.process_data(pdf_file)
        # Update job result and status
        job_object[job.job_uuid.__str__()].result = json.dumps(res)
        job_object[job.job_uuid.__str__()].status = StatusEnum.SUCCESS
    except Exception as e:
        logging.error(ExceptionMessageEnum.DATA_CLEANSING_ERROR.value.format(e))
        job_object[job.job_uuid.__str__()].result = ExceptionMessageEnum.DATA_CLEANSING_ERROR.value.format(e)
        job_object[job.job_uuid.__str__()].status = StatusEnum.ERROR

@log_entry_exit
@default_router.post("/knowledge_graph/enrich", response_model=Status, status_code=HTTPStatus.ACCEPTED)
async def graph_enrichment(background_tasks: BackgroundTasks, pdf_file: UploadFile = File(...), api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to enrich graph
    '''
    try:
        # Create a new job and add it to the job_object
        enrichment_job = Job()
        job_uuid = enrichment_job.job_uuid.__str__()
        job_object[job_uuid] = enrichment_job
        # Add a background task to run data cleansing asynchronously
        background_tasks.add_task(enrich_graph, pdf_file.file, enrichment_job)
        return Status(transaction_id=job_uuid, status=enrichment_job.status)
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))

@log_entry_exit
@default_router.get("/knowledge_graph/enrich/{transaction_id}", response_model=ResultStatus)
def graph_enrichment_status(transaction_id: str, api_key: APIKey = Depends(auth.get_api_key)):
    '''
     API to check upload status
    '''
    try:
        job = job_object.get(transaction_id)
        if job:
            return ResultStatus(transaction_id=transaction_id, status=job.status, result=job.result)
        else:
            return ResultStatus(transaction_id=transaction_id, status=StatusEnum.NOT_FOUND, result="NA")
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))

    
@log_entry_exit
@default_router.get("/knowledge_graph/fetch")
def fetch_knowledge_graph(user_id : str, api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Fetch Entire KG
    '''
    try:
        res = knowledge.fetch_profile(user_id) 
        return res
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))


@log_entry_exit
@default_router.get("/knowledge_graph/query")
def query_knowledge_graph(Query : str, api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Query KG
    '''
    try:
        res = knowledge.fetch_graph(Query)  
        return res
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
    
@log_entry_exit
@default_router.get("/knowledge_graph/fetch_megaskills")
def query_knowledge_graph(job : str, seniority:str, api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Query KG
    '''
    try:
        res = 'Not Implemented Yet'
        return res
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))

@log_entry_exit
@default_router.get("/knowledge_graph/job_categories")
def fetch_job_categories(api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Query KG
    '''
    try:
        res = knowledge.fetch_job_categories_admin()  
        return res
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
    
@log_entry_exit
@default_router.delete("/knowledge_graph/job_categories")
def delete_job_categories(job_category : str, seniority:str, api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Query KG
    '''
    try:
        res = knowledge.delete_enrichments(job_category, seniority)  
        return res
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))

    

@log_entry_exit
def get_build_status(user_id):

    try:
        query = f"Match (u:User{{ userid : '{user_id}'}}) return u.chat_status as chat_status  limit 1"
        print(query)
        build_status = neo4j_integration.get_neo4j_response(query)[0]["chat_status"] == 'Completed'
        print(build_status)
        return build_status
    except:
        return False
   
@log_entry_exit
def get_validate_status(user_id):
    return False

@log_entry_exit
def get_grow_status(user_id):
    return False


@log_entry_exit
@default_router.get("/status")
def query_knowledge_graph( user_id: str ,api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Query KG
    '''
    try:
        res = {
            'build' : get_build_status(user_id),
            'validate': get_validate_status(user_id),
            'grow': get_grow_status(user_id)
        }  
        return res
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
    


@log_entry_exit
def get_top_skills(user_id):
    tech_query = f"match (mega:Personal:Megaskill{{ user_id : '{user_id}'}})--(m:Personal:Microskill{{ user_id : '{user_id}'}})--(n:Task) where m.microskill_id starts with 'MT' or m.microskill_id starts with 'MB' return distinct mega.name_id as Skill, n.level as Level order by n.level  DESC limit 3"
    tech_skills = neo4j_integration.get_neo4j_response(tech_query)
    
    buss_query = f"match (mega:Personal:Megaskill{{ user_id : '{user_id}'}})--(m:Personal:Microskill{{ user_id : '{user_id}'}})--(n:Task) where m.microskill_id starts with 'MC'  return distinct mega.name_id as Skill, n.level as Level order by n.level  DESC limit 3"
    buss_skills = neo4j_integration.get_neo4j_response(buss_query)

    print(buss_skills, tech_query)

    return {
        'top_technical_skills' : tech_skills,
        'top_business_skills' : buss_skills
    }

@log_entry_exit
def get_timeline(user_id):
    query = f"Match (u:User{{ userid : '{user_id}'}}) return u.timeline as timeline, u.intro as introduction, u.profile_summary as summary limit 1"
    timeline = neo4j_integration.get_neo4j_response(query)
    user_details = get_user_details(user_id)
   
    return {
        "timeline" : timeline,
        "user_details" : user_details
    }


@log_entry_exit
@default_router.get("/share/timeline")
def query_knowledge_graph( user_id: str ,api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Query KG
    '''
    try:
        return get_timeline(user_id)
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))


@log_entry_exit
def update_summary(user_id: str, new_summary: str):
    query = f"MATCH (u:User{{ userid : '{user_id}'}}) SET u.profile_summary = '{new_summary}' RETURN u.profile_summary as summary"
    updated_intro = neo_utils.execute_queries([query])
    return updated_intro

@log_entry_exit
def update_intro(user_id: str, new_intro: str):
    query = f"MATCH (u:User{{ userid : '{user_id}'}}) SET u.intro = '{new_intro}' RETURN u.intro as intro"
    updated_intro = neo_utils.execute_queries([query])
    return updated_intro

@log_entry_exit
@default_router.put("/share/skill_summary/{user_id}")
def update_introduction(user_id: str, new_summary: str, api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Update User Introduction
    '''
    try:
        return update_summary(user_id, new_summary)
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))


@log_entry_exit
@default_router.put("/share/intro/{user_id}")
def update_introduction(user_id: str, intro: str, api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Update User Introduction
    '''
    try:
        return update_intro(user_id, intro)
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))


@log_entry_exit
@default_router.get("/share/top_skills")
def query_knowledge_graph_for_skills( user_id: str ,api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Query KG
    '''
    try:
        return get_top_skills(user_id)
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))

@log_entry_exit
@default_router.get("/dashboard/top_skills")
def query_knowledge_graph( user_id: str ,api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Query KG
    '''
    try:
        return {
            'Technical Skills' : ['Data Handling And Manipulation','AI Fundamentals','Software Development'],
            '21st Century Skills' : ['Problem Solving','Communication','Adaptability']
            
        }
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
    

@log_entry_exit
@default_router.get("/dashboard/count")
def query_knowledge_graph( user_id: str ,api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Query KG
    '''
    try:
        return {
            'Registered Users' : '14',
            'Build' : '95%',
            'Validate' : '59%',
            'Grow' : '51%',
            'Share' : '0%'
        }
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
    

@log_entry_exit
@default_router.get("/dashboard/aggregated_graph")
def query_knowledge_graph( user_id: str ,api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Query KG
    '''
    try:
        return knowledge.fetch_profile(user_id) 
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
    

@log_entry_exit
@default_router.get("/dashboard/skill_count")
def query_knowledge_graph(user_id : str, api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Query KG
    '''
    try:
        user_details = get_user_details(user_id)
        user_name = user_details['first_name']+' '+ user_details['last_name']
        res = knowledge.fetch_dashboard_json(user_name, user_id)  
        return res
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
    

@log_entry_exit
@default_router.get("/dashboard/list")
def query_knowledge_graph( user_id: str ,api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Query KG
    '''
    try:
        return 'API Development In Progress'
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
