import os
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import GraphCypherQAChain
from langchain_community.graphs import Neo4jGraph
from integration.openai_integration import get_openai_response
from integration.neo4j_integration import get_neo4j_response
from utils.config import log_entry_exit
from utils.neo_utils import execute_queries 
import random
import json

import os
from dotenv import load_dotenv
load_dotenv()


NEO4J_URL = os.getenv("NEO4J_URI", None)
NEO4J_USER = os.getenv("NEO4J_USERNAME", None)
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", None)

graph = Neo4jGraph(
    url=NEO4J_URL, 
    username=NEO4J_USER, 
    password=NEO4J_PASSWORD)

chain = GraphCypherQAChain.from_llm(
    ChatOpenAI(temperature=0,model_name='gpt-3.5-turbo-1106'), graph=graph, verbose=True,return_intermediate_steps=True
)


@log_entry_exit
def fetch_validation_json(user, user_id):

    query = f"""
                MATCH (disc:Personal:Discipline {{user: '{user}', user_id: '{user_id}'}})--(mega:Megaskill)--(m:Microskill)
                WITH disc, mega, COLLECT(DISTINCT {{name_id: m.name_id, validation_status: m.validation_status}}) AS microskills
                WITH disc,  COLLECT(DISTINCT {{name_id: mega.name_id, validation_status: mega.validation_status, microskills: microskills}}) AS megaskills
                RETURN COLLECT(DISTINCT {{
                    id: disc.name_id,
                    Megaskills: megaskills
                }}) 
                AS Discipline
                            """
    
    data = get_neo4j_response(query)

    overall_status =  'Validated'
    descipline_status = 'Validated'

    for descipline_data in data[0]['Discipline']:
        descipline_name = descipline_data['id']
        for megaskill in descipline_data['Megaskills']:
            
            print(megaskill)
            if megaskill['validation_status'] is not None:
                descipline_status = megaskill['validation_status']
            else:
                descipline_status = 'Not Validated'

            if descipline_status == 'Not Validated':
                break

        descipline_data['validation_status'] = descipline_status
        

    for descipline in data[0]['Discipline']:
        #this overwrites status to Not Validated even if any one of the descipline is not validated
        overall_status = descipline['validation_status']
        if overall_status == 'Not Validated':
            break

    res = {
        "data" : data,
        "validation_status" : overall_status
    }

    return res


def set_similarity(user_id):
    query = f"""
    Match (cj:JobRole:Personal{{user_id:'{user_id}'}}) 
    With cj.salary as min_salary
    MATCH (j:JobRole) WHERE NOT j:Personal and j.salary > min_salary return distinct j.name as job_role, j.seniority as seniority"""
    result = get_neo4j_response(query)

    similarity_jobs = []
    for item in result:
        job_role = item['job_role']
        seniority = item['seniority']
        matched_tasks = 0
        total_tasks = 0
        skill_response = fetch_skill_for_grow_v1(user_id, job_role, seniority)
        total_tasks = skill_response['total_skill_count']
        matched_tasks = skill_response['skill_gap']
                        
        percentage_similarity = (matched_tasks/total_tasks)*100
        percentage_similarity = round(percentage_similarity,2)
        similarity_jobs.append({
            'Job_Category' : job_role,
            'Seniority' : seniority,
            'similairty' : percentage_similarity
        })

    sorted_data = sorted(similarity_jobs, key=lambda x: (x["Seniority"], -x["similairty"]))

    # Keep track of seen job roles
    seen_job_roles = set()
    top_results = []

    for item in sorted_data:
        if item["Job_Category"] not in seen_job_roles:
            top_results.append(item)
            seen_job_roles.add(item["Job_Category"])
        if len(top_results) == 6:
            break


    possible_job_cat = ['Data Scientist',
                            'AI Architect',
                            'AI Developer',
                            'Data Analyst',
                            'Machine Learning Engineer',
                            'Research Scientist',]

    for job in possible_job_cat:
        if job not in seen_job_roles:
            top_results.append({
            'Job_Category' : job,
            'Seniority' : 'NA',
            'similairty' : 0
        })


    print("top results",top_results)                     
    top_results = json.dumps(top_results)
    
    set_query = f"""Merge (u:User{{ userid : '{user_id}'}})  SET u.similar_jobs = '{top_results}' """
    execute_queries([set_query])
    # return top_results


def fetch_skill_for_grow_v1(user_id, job_role, seniority, location='Singapore'):

    
    master_graph_query = f"""MATCH (disc:Discipline )--(mega:Megaskill)--(m:Microskill)--(t:Task)--(j:JobRole {{name: '{job_role}'}})
                    WHERE NOT disc:Personal AND j.seniority='{seniority}'
                    WITH disc, mega, m, COLLECT(DISTINCT t.name) AS task_list, j as JOB
                    WITH disc, mega, COLLECT(DISTINCT {{name_id: m.name, validation_status: COALESCE(m.validation_status, 'Not Acquired'), declining_skill: COALESCE(m.declining_skill, 'No'), task_list: task_list, estimated_hours : toInteger(2 + toInteger(rand() * 5))}}) AS microskills, JOB
                    WITH disc, COLLECT(DISTINCT {{name_id: mega.name, validation_status: COALESCE(mega.validation_status, 'Not Acquired'), microskills: microskills}}) AS megaskills, JOB
                    RETURN COLLECT(DISTINCT {{
                        id: disc.name, 
                        Megaskills: megaskills}}) 
                    AS Discipline
                    """

    #selected filter is added to remove Selected for Aquiring skills but which were added to pkg for persistence purposes
    personal_graph_query = f"""MATCH (disc:Personal:Discipline {{ user_id: '{user_id}'}})--(mega:Megaskill)--(m:Microskill) where  (m.selected is NULL or m.selected = 'No') and m.validation_status <> 'Selected for Aquiring'
                            return collect(distinct m.name_id) as microskills"""
    
    selected_microskill_query = f"""MATCH (disc:Personal:Discipline {{ user_id: '{user_id}'}})--(mega:Megaskill)--(m:Microskill) where m.selected = 'Yes'
                            return collect(distinct m.name_id) as microskills"""

    
    master_graph = get_neo4j_response(master_graph_query)
    response = get_neo4j_response(personal_graph_query)
    microskill_list = response[0]['microskills']
    print(microskill_list)

    response = get_neo4j_response(selected_microskill_query)
    selected_microskill_list = response[0]['microskills']


    neo4j_query = f"""Match (j:JobRole {{name: '{job_role}'}})
                        WHERE NOT j:Personal AND j.seniority='{seniority}' return j.salary_range_india as salary limit 1"""
    if location == 'Singapore':
        neo4j_query = f"""Match (j:JobRole {{name: '{job_role}'}})
                        WHERE NOT j:Personal AND j.seniority='{seniority}' return j.salary_range_singapore as salary limit 1"""
        
    
    print(neo4j_query)
    neo4j_response = get_neo4j_response(neo4j_query)
    salary = neo4j_response[0]['salary']
    
    declining_count = 0
    matched_tasks = 0
    total_tasks = 0
    for first_discipline in master_graph[0]['Discipline']:
        for first_megaskill in first_discipline['Megaskills']:
                for microskill in first_megaskill['microskills']:
                    task_count = len(microskill['task_list'])
                    if microskill['name_id'] in microskill_list:
                        print(microskill['name_id'])
                        task_count = len(microskill['task_list'])
                        microskill['validation_status'] = 'Not Validated'
                        matched_tasks+=task_count
                    if microskill['name_id'] in selected_microskill_list:
                        microskill['selected'] = 'Yes'
                        microskill['validation_status'] = 'Selected for Aquiring'
                    total_tasks+=task_count    
    

                    if microskill['declining_skill'] == 'Yes':
                        declining_count+=1


    neo4j_job_query = f"""Match (j:JobRole {{name: '{job_role}'}})--(jp:JobPosting)
                    WHERE NOT j:Personal AND jp.location='{location}' return count(jp) as job_count"""
    neo4j_job_response = get_neo4j_response(neo4j_job_query)
    job_count = neo4j_job_response[0]['job_count']


    return {
                "skills": master_graph,
                "total_skill_count" : total_tasks, 
                "skill_gap" : matched_tasks,
                "emerging_skill_count" : matched_tasks + random.randint(1,4),
                "declining_skill_count" : declining_count,
                "salary" : salary,
                "job_count" : job_count
    }
                


@log_entry_exit
def fetch_dashboard_json(user, user_id):

    query = f"""
                MATCH (disc:Personal:Discipline {{user: '{user}', user_id: '{user_id}'}})--(mega:Megaskill)--(m:Microskill)
                WITH disc, mega, COLLECT(DISTINCT {{name_id: m.name_id, count: 11}}) AS microskills
                WITH disc,  COLLECT(DISTINCT {{name_id: mega.name_id , microskills: microskills}}) AS megaskills
                RETURN COLLECT(DISTINCT {{
                    id: disc.name_id,
                    Megaskills: megaskills
                }}) 
                AS Discipline
                            """
    
    res = get_neo4j_response(query)

    return res


@log_entry_exit
def fetch_discipline_with_validation_status(user_id):

    query = f"""
                MATCH (disc:Personal:Discipline {{user_id: '{user_id}'}})--(mega:Megaskill)--(m:Microskill)--(t:Task)--(j:JobRole)
                WITH disc, mega, m, COLLECT(distinct properties(t)) AS tasks
                WITH disc, mega, COLLECT(distinct {{ Microskill: m.name_id, level:COALESCE(m.level,2) , Validation_Status:COALESCE(m.validation_status,'Not Validated') , Tasks: tasks }}) AS microskills
                WITH disc, COLLECT(distinct {{ Megaskill: mega.name_id, Validation_Status:COALESCE(mega.validation_status,'Not Validated'), Microskills: microskills }}) AS megaskills
                RETURN  collect(distinct {{
                    id: disc.name_id,
                    Megaskills: megaskills
                }}) AS Discipline;
                            """

    return get_neo4j_response(query)


@log_entry_exit
def fetch_archives(user, user_id):

    query = f"""
                MATCH (disc:Personal:Discipline {{user: '{user}', user_id: '{user_id}'}})--(mega:Megaskill)--(m:Microskill)--(t:Task)
                WITH disc, mega, m, COLLECT(distinct properties(t)) AS tasks
                WITH disc, mega, COLLECT(distinct {{ Microskill: m.name_id, level:COALESCE(m.level,2) , Validation_Status:COALESCE(m.validation_status,'Not Validated') , Tasks: tasks }}) AS microskills
                WITH disc, COLLECT(distinct {{ Megaskill: mega.name_id, Validation_Status:COALESCE(mega.validation_status,'Not Validated'), Microskills: microskills }}) AS megaskills
                RETURN  collect(distinct {{
                    id: disc.name_id,
                    Megaskills: megaskills
                }}) AS Discipline;
                            """
    print(query)
    return get_neo4j_response(query)



def fetch_job_categories_admin():

    query = f"""MATCH (j:JobRole) where j.name is not null return distinct j.name as Job_Category , j.seniority as Seniority order by Job_Category, Seniority"""
    return get_neo4j_response(query)



def fetch_job_categories(user_id):
    
    
    query = f"""Match (u:User{{ userid : '{user_id}'}})  return u.similar_jobs as similar_jobs """

    similar_jobs =  json.loads(get_neo4j_response(query)[0]['similar_jobs'])

    currr_query = f""" MATCH (p:JobRole:Personal {{user_id: '{user_id}'}}) return p.name_id as current_job_role, p.seniority as current_seniority limit 1"""

    print(currr_query)
    curren_job = get_neo4j_response(currr_query)

    return {
        "current_job_role" : curren_job[0]['current_job_role'],
        "current_seniority" : curren_job[0]["current_seniority"],
        "similar_job_roles" : similar_jobs
    }



@log_entry_exit
def delete_enrichments(job_category='All', seniority='All'):

    if job_category == 'All':
        query = f"""MATCH (j{{source:'enrichment'}}) detach delete j"""
    else:
        query = [f"""MATCH (j:JobRole{{name:'{job_category}', seniority : '{seniority}', source:'enrichment'}})-->(t:Task{{source:'enrichment'}}) detach delete j,t""",
                 f"""MATCH (j:JobRole{{name:'{job_category}', seniority : '{seniority}', source:'enrichment'}}) detach delete j"""]

    
    print(query)
    return execute_queries(query)

@log_entry_exit
def personal_knowledge_graph(user_id):
    try:
        user_query = f"""Match (u:User{{ userid : '{user_id}'}}) remove u.chat_status, u.transaction_id, u.filename """
        pkg_query = f"""Match (p:Personal{{ user_id : '{user_id}'}}) detach delete p"""
        execute_queries([user_query, pkg_query])
        return 'Success'
    except Exception as e:
        return e


@log_entry_exit
def reset_chat_status(user_id, trans_id, filename):
    query = f"""Merge (u:User{{ userid : '{user_id}'}})  SET u.chat_status = 'Completed', u.transaction_id = '{trans_id}', u.filename =  '{filename}' """
    execute_queries([query])

import time

@log_entry_exit
def store_in_db(trans_id, user_id, filename, status, chat):
    chat = chat.replace('"', r'\"')
    chat = chat.replace("'", '')

    timestamp = int(time.time())

    # Append timestamp to trans_id
    trans_id_with_timestamp = f"{timestamp}_{trans_id}"
    
    query = f"""Merge (u:User{{ userid : '{user_id}'}})  SET u.chat_status = '{status}', u.transaction_id = '{trans_id}', u.filename =  '{filename}'
                Merge (m:Conversation{{ id : '{trans_id_with_timestamp}'}}) SET m.chat_archive = '{chat}', m.filename =  '{filename}', m.chat_status = '{status}', m.transaction_id = '{trans_id}' 
                Merge (u)-[:HAD_CONVERSATION]->(m)
              """   

    execute_queries([query])

    # if status == 'Completed':
    #     summary = get_openai_response("""You are an fluent assistant tasked with analyzing a candidates's skills based on their resume and chat conversations""",
    #                                  f""" Your goal is to offer an analysis, around 100 words, focusing solely on the skills of the user in a second person narrative style using elegant language. 
    #                                         Even if the user doesn't engage in a conversation, you're expected to generate a summary based on the resume alone. Avoid revealing the method behind your analysis. Do not mention a skill framework, skill levels or specific projects details. 

    #                                         Keep the structure of the summary as follows - 
    #                                         1. Mention what are the technical skill, business skill and 21st century skill where the candidate is most proficient in.
    #                                         2. At the end mention that "You can get a detailed view by clicking on the skill map link. 
                                            
    #                                         ##context starts here : {chat}
                                            
    #                                         Note : provide summary in third person , use He/she instead of You""")
        
    #     summary = summary.replace('"', r'\"')
    #     summary = summary.replace("'", '')
    #     summary_query = f"""Merge (u:User{{ userid : '{user_id}'}}) SET u.summary = '{summary}', u.profile_summary = '{summary}' """  
    #     execute_queries([summary_query])


@log_entry_exit
def save_resume_summary(user_id, resume):
    summary = get_openai_response("""You are an fluent assistant tasked with analyzing a candidates's skills based on their resume and chat conversations""",
                                    f""" Your goal is to offer an analysis, around 100 words, focusing solely on the skills of the user in a second person narrative style using elegant language. 
                                        Even if the user doesn't engage in a conversation, you're expected to generate a summary based on the resume alone. Avoid revealing the method behind your analysis. Do not mention a skill framework, skill levels or specific projects details. 

                                        Keep the structure of the summary as follows - 
                                        1. Mention what are the technical skill, business skill and 21st century skill where the candidate is most proficient in.
                                        2. At the end mention that "You can get a detailed view by clicking on the skill map link. 
                                        
                                        ##context starts here : {resume}
                                        
                                        Note : provide summary in third person , use He/she instead of You""")
    
    summary = summary.replace('"', r'\"')
    summary = summary.replace("'", '')
    summary_query = f"""Merge (u:User{{ userid : '{user_id}'}}) SET u.summary = '{summary}', u.profile_summary = '{summary}' """  
    execute_queries([summary_query])


@log_entry_exit
def store_timeline(user_id, timeline):
    timeline = json.dumps(timeline)
    summary_query = f"""Merge (u:User{{ userid : '{user_id}'}}) SET u.timeline = '{timeline}' """  
    execute_queries([summary_query])



@log_entry_exit
def store_status( user_id, skill, status, chat):
    
    chat = chat.replace('"', r'\"')
    chat = chat.replace("'", '')


    query_list = []

    if isinstance(skill, str):
        skill = json.loads(skill)

    for megaskill,microskill_list in skill["megaskills"].items():
        for microskill in microskill_list:
            query = f"""match (m:Personal:Microskill{{user_id: "{user_id}", name_id: "{microskill}"}}) set m.validation_status = '{status}'"""
            query_list.append(query)
        
        megaskill_query = f"""match (m:Personal:Megaskill{{user_id: "{user_id}", name_id: "{megaskill}"}})--(n:Microskill) SET m.validation_archive = '{chat}',  m.validation_status = '{status}'""" 
        
        megaskill_query =         f"""MATCH (m:Personal:Megaskill {{user_id: "{user_id}", name_id: "{megaskill}"}})--(n:Microskill)
            WITH m, COLLECT(n.validation_status) AS statuses
            WITH m, statuses, SIZE([status IN statuses WHERE status IS NOT NULL]) AS nonNullCount
            SET m.validation_archive = '{chat}',
                m.validation_status = CASE
                    WHEN 'Not Validated' IN statuses OR nonNullCount = 0 THEN 'Not Validated'
                    ELSE 'Validated'
                END
            """
        

        query_list.append(megaskill_query)  

    execute_queries(query_list)


@log_entry_exit
def retrieve_chat_v1(user_id):
    query = f"Match (u:User{{ userid : '{user_id}'}})--(m:Conversation) return m.transaction_id as chat_id, m.chat_archive as chat_archive, m.filename as uploaded_file , m.chat_status as chat_status  "
    status_query = f"Match (u:User{{ userid : '{user_id}'}}) return u.transaction_id as chat_id, u.chat_status as chat_status , u.filename as filename limit 1"
    
    t_id = get_neo4j_response(status_query)
    chats =  get_neo4j_response(query)

    return {
        'archive' : chats ,
        'status' : t_id
    }

@log_entry_exit
def retrieve_validation_chat(user_id):
    megaskill_query = f"""match (m:Personal:Megaskill{{user_id: "{user_id}"}}) where m.validation_archive is NOT NULL return m.validation_archive as validation_archive,  m.validation_status as validation_status""" 
    return get_neo4j_response(megaskill_query)

@log_entry_exit
def retrieve_summary(user_id):

    summary_query = f"Match (u:User{{ userid : '{user_id}'}}) return u.summary as summary"
    
    summary = get_neo4j_response(summary_query)

    return summary[0]['summary']

@log_entry_exit
def fetch_graph(query):

    if 'MATCH'.lower() in query.lower(): 
        return get_neo4j_response(query)
    
    matched_query = match_predefined_query(query)
    if matched_query == 'NA':
        print("in chain")
        response = chain(f"Query: {query} in tabular format")
        result = response['intermediate_steps'][1]['context']
        return format_response(result)
    else:
        print("in non chain:",matched_query)
        return get_neo4j_response(matched_query)
    
@log_entry_exit
def fetch_profile(user):

    query = None
    if user == 'All':
        query= """MATCH path = (start:Industry)-[:children*]->(end) where start.name is NOT NULL and end.name is NOT NULL
                WITH collect(path) AS paths
                CALL apoc.convert.toTree(paths) YIELD value
                return value"""
    else:
       query =f"""MATCH path = (start:Industry:Personal{{user_id:'{user}'}})-[:children*]->(end) where start.name_id is NOT NULL and end.name_id is NOT NULL
                WITH collect(path) AS paths
                CALL apoc.convert.toTree(paths) YIELD value
                return value"""
       
       print(query)

    response_l = []
    for res in get_neo4j_response(query):
        response_l.append(res['value'])

    return {
        "value" : 0,
        "children" : response_l
    }


@log_entry_exit
def format_response(result):
    formatted_response = []
    for item in result:
        key, value = list(item.items())[0]
        temp_dict = {}
        temp_dict['name'] = key
        temp_dict['value'] = value
        temp_dict['levels'] = random.randint(1,4)
        formatted_response.append(temp_dict)

    return formatted_response

@log_entry_exit
def match_predefined_query(query):
    system_msg = {
            "queries": [
                {
                "input": "Show the job roles aligned to the AI discipline",
                "output": """MATCH (m:Discipline)-->(mega:Megaskill)-->(micro:Microskill)-->(t:Task)--(j:JobRole)
                        where m.name = 'Artificial Intelligence' and NOT m:Personal
                        return m.name AS Discipline, j.name AS `JobCategory`, COLLECT(DISTINCT j.seniority) AS Seniority
                        """
                },
                {
                "input": "display the job roles aligned to the AI discipline",
                "output": """MATCH (m:Discipline)-->(mega:Megaskill)-->(micro:Microskill)-->(t:Task)--(j:JobRole)
                        where m.name = 'Artificial Intelligence' and NOT m:Personal
                        return m.name AS Discipline, j.name AS `JobCategory`, COLLECT(DISTINCT j.seniority) AS Seniority
                        """
                },
                {
                "input":"Display the skills aligned to the Machine Learning Engineer job category",
                "output":"""MATCH (j:JobRole {name: 'Machine Learning Engineer'})--(t:Task)--(m:Microskill)--(mega:Megaskill)--(disc:Discipline)
                        return 
                        j.name as Job_Category, 
                        j.seniority as Seniority, 
                        CASE WHEN disc.name = '21st Century Skills' THEN disc.name ELSE 'Functional' END as Megaskill_Type,
                        mega.name as Megaskill, 
                        m.name as Microskill
                        Order by  Seniority , Megaskill_Type, Megaskill, Microskill"""
                },
                {
                "input":"show the skills related to the Machine Learning Engineer job category",
                "output":"""MATCH (j:JobRole {name: 'Machine Learning Engineer'})--(t:Task)--(m:Microskill)--(mega:Megaskill)--(disc:Discipline)
                        return 
                        j.name as Job_Category, 
                        j.seniority as Seniority, 
                        CASE WHEN disc.name = '21st Century Skills' THEN disc.name ELSE 'Functional' END as Megaskill_Type,
                        mega.name as Megaskill, 
                        m.name as Microskill
                        Order by  Seniority , Megaskill_Type, Megaskill, Microskill"""
                },
                {
                "input":"Display the skills aligned to the Machine Learning Engineer Senior",
                "output":"""MATCH (j:JobRole {name: 'Machine Learning Engineer', seniority: 'Senior'})--(t:Task)--(m:Microskill)--(mega:Megaskill)--(disc:Discipline)
                        return 
                        j.name as Job_Category, 
                        j.seniority as Seniority, 
                        CASE WHEN disc.name = '21st Century Skills' THEN disc.name ELSE 'Functional' END as Megaskill_Type,
                        mega.name as Megaskill, 
                        m.name as Microskill
                        Order by  Seniority , Megaskill_Type, Megaskill, Microskill"""
                },
                {
                "input": "Display the multiple programming languages aligned to the microskill titled Programming for AI",
                "output": "MATCH (m:Megaskill{name:'Programming for AI'})--(l:Language) RETURN l.name AS ProgrammingLanguages"
                },
                {
                "input": "Multiple language libraries aligned to the Python programming language",
                "output": "MATCH (m:Language{name:'Python'})--(l:Library) where m.name is NOT NULL RETURN l.name AS Libraries"
                },
                {
                    "input" : "Fetch Unaligned Tasks for Data Scientist Senior",
                    "output" : """MATCH (j:JobRole {name: 'Data Scientist', seniority: 'Senior'})--(t:Task)
                        where t.source = 'enrichment'
                        return 
                        distinct t.name as `Unaligned Task`"""
                },
                {
                "input": "display the job roles related to the AI discipline",
                "output": """MATCH (m:Discipline)-->(mega:Megaskill)-->(micro:Microskill)-->(t:Task)--(j:JobRole)
                        where m.name = 'Artificial Intelligence' and NOT m:Personal
                        return m.name AS Discipline, j.name AS `JobCategory`, COLLECT(DISTINCT j.seniority) AS Seniority
                        """
                }
            ]
            }

    prompt = """You are a Cypher Query Generator who tries to match the input with one of the predefined Cypher Queries and returns output. 
            If there is partial match you modify the closest matched query and return result. Always return a cypher query wih No Explanation"""
    return get_openai_response(prompt+ json.dumps(system_msg), query)

