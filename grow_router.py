from fastapi import APIRouter
from fastapi import Depends, HTTPException
from utils.model_classes import ExceptionMessageEnum
from fastapi.security.api_key import APIKey
import authentication.auth as auth
from dotenv import load_dotenv
from utils.config import log_entry_exit
import logging
from features import knowledge

import base64
from integration import neo4j_integration
from utils import neo_utils
from fastapi import HTTPException
load_dotenv()


job_object = {}

grow_router = APIRouter()

@log_entry_exit
@grow_router.get("/grow/job_categories")
def fetch_job_categories(user_id, api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Query KG
    '''
    try:
        res = knowledge.fetch_job_categories(user_id)  
        return res
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        
@log_entry_exit
@grow_router.get("/grow/fetch_megaskills/v1")
def fetch_megaskills_grow(job : str, seniority:str, user_id: str , location:str = 'Singapore',  api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Query KG
    '''
    try:
        res = knowledge.fetch_skill_for_grow_v1(user_id, job, seniority, location )  
        return res
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
    

@log_entry_exit
@grow_router.get("/grow/jobs")
def fetch_megaskills_grow(job : str, seniority:str, user_id: str ,location:str = 'Singapore', api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Query KG
    '''
    try:

        query = f'''MATCH (jp:JobPosting)--(t:Task)
                        WHERE jp.location = '{location}'
                        WITH jp.positionName AS posting_name, 
                            COLLECT(DISTINCT t.name) AS job_posting_tasks, 
                            SIZE(COLLECT(DISTINCT t.name)) AS total_jobs, 
                            jp.seniority AS job_seniority, 
                            jp.company AS company_name, 
                            jp.description AS job_description, 
                            jp.externalApplyLink AS job_link, 
                            TOSTRING(DATE(jp.postingDateParsed)) AS published_date

                    MATCH (t1:Task {{user_id: '{user_id}'}})
                    WHERE t1.name_id IN job_posting_tasks
                    WITH posting_name, 
                        SIZE(COLLECT(t1.name_id)) AS personal_tasks, 
                        t1.seniority AS user_seniority, 
                        total_jobs, 
                        job_seniority, 
                        company_name, 
                        job_description, 
                        job_link, 
                        published_date

                    WITH posting_name, 
                        personal_tasks, 
                        total_jobs, 
                        job_seniority, 
                        user_seniority, 
                        company_name, 
                        job_description, 
                        job_link, 
                        published_date,
                        CASE 
                            WHEN job_seniority = user_seniority THEN 1.0 
                            WHEN job_seniority = 'Junior' AND user_seniority = 'Mid Level' THEN 0.75 
                            WHEN job_seniority = 'Senior' AND user_seniority = 'Mid Level' THEN 0.5
                            WHEN job_seniority = 'Junior' AND user_seniority = 'Senior' THEN 0.5 
                            WHEN job_seniority = 'Mid Level' AND user_seniority = 'Senior' THEN 0.75
                            WHEN job_seniority = 'Mid Level' AND user_seniority = 'Junior' THEN 0.75 
                            WHEN job_seniority = 'Senior' AND user_seniority = 'Junior' THEN 0.5 
                            
                            ELSE 0.0 
                        END AS seniority_weight

                        RETURN posting_name AS job_role, 
                            job_seniority AS seniority, 
                            company_name, 
                            published_date, 
                            job_description, 
                            job_link, 
                            ROUND(TOFLOAT(personal_tasks) / total_jobs * seniority_weight, 2) AS similarity_score 
                        ORDER BY similarity_score DESC

                    '''

        print(query)

        res = neo4j_integration.get_neo4j_response(query)
        return res
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))

@log_entry_exit
def persist_skills(skills_dict: dict):

    user_id = skills_dict['user_id']
    query1 = f'''match (micro:Microskill) where micro.user_id = "{user_id}" set micro.selected = "No" '''

    skill_query = []
    skill_query.append(query1)
    for skill, nodes in skills_dict['skills'].items():
 
        disc = nodes["discipline"]
        mega = nodes["megaskill"]
        micro = skill

        print("nodes",disc, mega, micro)
        query = f"""
        MERGE (discipline:Discipline:Personal{{name_id: '{disc}', user_id: '{user_id}' , type: 'Discipline' , value: 8}}) 
        MERGE (megaskill:Megaskill:Personal{{name_id: '{mega}',  user_id: '{user_id}' ,  type: 'Megaskill', value: 6}}) 
        MERGE (microskill:Microskill:Personal{{name_id: '{micro}', user_id: '{user_id}' , type: 'Microskill', validation_status: 'Selected for Aquiring', value: 3 }}) 
        MERGE (discipline)-[:REQUIRES_MEGASKILL]->(megaskill) 
        MERGE (megaskill)-[:REQUIRES_MICROSKILL]->(microskill)"""

        skill_query.append(query)
        skill_query.append(f"""Match (micro:Microskill) where micro.user_id = "{user_id}" and micro.name_id = '{micro}' set micro.selected = "Yes" """)
    
    updated_intro = neo_utils.execute_queries(skill_query)
    return updated_intro    


def get_encoded_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


@log_entry_exit
@grow_router.post("/grow/save_selected_skills")
def persist_selected_skills( skills: dict , api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to save selected skills
    '''
    try:
        
        persist_skills(skills)
        return "Skills Saved"
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))


@log_entry_exit
@grow_router.post("/grow/courses")
def fetch_courses_for_skills( skills: dict , api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Query KG
    '''
    try:

        skill_list = []
        for askill in skills['skills']:
            skill_list.append(askill)

        print(skill_list)
        query = f'''match (micro:Microskill)--(:Task)--(m:course) where micro.name in {skill_list} return distinct m.name as title, m.duration as hours , m.url as udemy_link, m.rating as rating, m.description as course_description'''
        res = neo4j_integration.get_neo4j_response(query)
        
        for item in res:
            item['image'] = get_encoded_image("slivers/images/" + item['title'] + ".jpeg")

        return res
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))



@log_entry_exit
def update_learning_path_neo4j(user_id , courses):
    query = f"MATCH (u:User{{ userid : '{user_id}'}}) SET u.learning_path = {courses} RETURN u.learning_path as learning_path"
    updated_path = neo_utils.execute_queries([query])
    return updated_path

@log_entry_exit
@grow_router.put("/grow/save_learning_path")
def update_learning_path(user_id: str, courses: list, api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Update User Introduction
    '''
    try:
        return update_learning_path_neo4j(user_id, courses)
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))



@log_entry_exit
@grow_router.post("/grow/courses/learning_path")
def fetch_courses_for_skills( user_id: str, api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Query KG
    '''
    try:
        query = f'''MATCH (u:User{{ userid : '{user_id}'}}) with u.learning_path as learning_path
        match (m:course) where m.name in learning_path return distinct m.name as title, m.duration as hours , m.url as udemy_link, m.rating as rating, m.description as course_description'''
        res = neo4j_integration.get_neo4j_response(query)
        
        for item in res:
            item['image'] = get_encoded_image("slivers/images/" + item['title'] + ".jpeg")

        return res
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
    
@log_entry_exit
@grow_router.post("/grow/courses/aligned_skills")
def fetch_courses_for_skills( user_id: str , course: str , api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Query KG
    '''
    try:
        
        query = f''' match (pmicro:Microskill:Personal{{user_id : '{user_id}' }}) where pmicro.selected = 'Yes'
        with collect(pmicro.name_id) as personal_microskill
        match (micro:Microskill)--(:Task)--(m:course) where m.name = '{course}' and micro.name in personal_microskill return collect(distinct micro.name) as aligned_skills'''
        res = neo4j_integration.get_neo4j_response(query)[0]['aligned_skills']
        return res
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
