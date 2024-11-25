from fastapi import APIRouter
from fastapi import HTTPException
from dotenv import load_dotenv
import logging
from integration import neo4j_integration
from fastapi import UploadFile, File
import PyPDF2
import docx
import json
from integration.prompt import get_industry_classification, get_framework_generator, get_final_framework
from pydantic import BaseModel
from typing import List
from utils.config import log_entry_exit
from features.extract_text_utils import extract_text

class JobDescription(BaseModel):
    industry: str
    discipline: str
    text: List[str]


load_dotenv()

framework_router = APIRouter()


def fetch_industries(industry):
    return ["Information Technology"]

# Extracted functions from app_streamlit.py
@log_entry_exit
def step_1(state):
    industry = get_industry_classification(state["input"])
    return industry

@log_entry_exit
def step_3(state):
    print("entering step 3")
    framework = get_framework_generator(state["user_feedback"], state["framework"])
    print("exiting step 3")
    return framework


@log_entry_exit
def fetch_relevant_framework(indsutry, discipline):

    if discipline == 'AI & Machine Learning':
        discipline = 'Artificial Intelligence'

    graph_query = f"""MATCH (ind:Industry)--(disc:Discipline )--(mega:Megaskill)--(m:Microskill)--(t:Task)
                    WHERE NOT disc:Personal and ind.name = '{indsutry}' and disc.name = '{discipline}'
                    WITH disc, mega, m, COLLECT(DISTINCT t.name) AS task_list
                    WITH disc, mega, COLLECT(DISTINCT {{name_id: m.name,  task_list: task_list}}) AS microskills
                    WITH disc, COLLECT(DISTINCT {{name_id: mega.name, microskills: microskills}}) AS megaskills
                    RETURN COLLECT(DISTINCT {{
                        id: disc.name, 
                        Megaskills: megaskills}}) 
                    AS Discipline
                    """

    print(graph_query)
    return neo4j_integration.get_neo4j_response(graph_query)

@log_entry_exit
def fetch_industry_framework(indsutry):


    graph_query = f"""MATCH (ind:Industry)--(disc:Discipline )--(mega:Megaskill)--(m:Microskill)--(t:Task)
                    WHERE NOT disc:Personal and ind.name = '{indsutry}'
                    WITH disc, mega, m, COLLECT(DISTINCT t.name) AS task_list
                    WITH disc, mega, COLLECT(DISTINCT {{name_id: m.name,  task_list: task_list}}) AS microskills
                    WITH disc, COLLECT(DISTINCT {{name_id: mega.name, microskills: microskills}}) AS megaskills
                    RETURN COLLECT(DISTINCT {{
                        id: disc.name, 
                        Megaskills: megaskills}}) 
                    AS Discipline
                    """

    print(graph_query)
    return neo4j_integration.get_neo4j_response(graph_query)


# Request models
from pydantic import BaseModel
from integration import bert_classfier

class ClassificationRequest(BaseModel):
    file: UploadFile
    file_type: str

# New API for classification
@framework_router.post("/classify")
async def classify(file: UploadFile = File(...), file_type: str = "pdf"):
    try:
        print("Extracting text from file")
        job_description = extract_text(file.file.read(), file_type)
        print("Extracted text:", job_description[:100])  # Print first 100 characters for brevity

        state = {"input": job_description}
        print("State initialized:", state)

        industry = step_1(state)
        if isinstance(industry, str):
            industry = json.loads(industry)
            
        print("Classified industry:", industry)

        existing_industry_list = fetch_industries(industry)
        print("Fetched industries:", existing_industry_list)

        existing_industry_dict =  {}
        new_industry_list = []

        for a_industry in industry:
            industry_name = a_industry['industry']
            discipline = a_industry['discipline']
            texts_alone = a_industry['text']
            texts = []
            for text in texts_alone:
                texts.append(text+f":{discipline}")

            if industry_name in existing_industry_list:
                if industry_name not in existing_industry_dict:
                    existing_industry_dict[industry_name] = []
                existing_industry_dict[industry_name].extend(texts)
            else:
                new_industry_list.append(a_industry)
        
        discipline_classified_list = []
        for ind, texts in existing_industry_dict.items():
            discipline_classified_list.extend(bert_classfier.group_sentences_by_class(ind, texts))

       
        print("Discipline classified list:", discipline_classified_list)

        overall_industry_list = discipline_classified_list + new_industry_list
        print("Overall industry list:", overall_industry_list)

        if isinstance(overall_industry_list, str):
            return json.loads(overall_industry_list)
        else:
            return overall_industry_list
    except Exception as e:
        print("Error occurred:", str(e))
        raise HTTPException(status_code=500, detail=str(e))


# New API for framework generation
@framework_router.post("/generate_framework")
async def generate_framework(request: list[JobDescription] ):
    try:
        industry = request[0].industry
        print(industry)
        discipline = request[0].discipline
        print(discipline)
        existing_framework = fetch_relevant_framework(industry, discipline)
        print(existing_framework)
    
        state = {"user_feedback": [job.dict() for job in request], "framework": existing_framework}
        print(state)
        framework = step_3(state)
        print(framework)

        try:
            return json.loads(framework)
        except:
            return framework

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format in user feedback.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@framework_router.post("/final_framework")
async def generate_framework(request: list[dict] ):
    try:
        industry_dict = {}
        existing_framework = {}
        for items in request:
            if items['Industry'] not in industry_dict:
                industry_dict[items['Industry']] = []
                existing_framework[items['Industry']] = fetch_industry_framework(items['Industry'])
  
            industry_dict[items['Industry']].append(items)

        return get_final_framework(industry_dict, existing_framework)

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format in user feedback.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))