import uuid
from neo4j import GraphDatabase
import json
from features.similarity import skill_mapper,task_mapper
from utils.config import log_entry_exit
import time
from dotenv import load_dotenv
import os

load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI", None)
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", None)
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", None)

@log_entry_exit
def create_queries(jobRoleName,seniority, industryName, tasks):
    jobRoleId = str(uuid.uuid4())
    industryId = str(uuid.uuid4())

    mapping_response = task_mapper(tasks)
    print(1)
    matched_task_list = mapping_response['matched_path']
    new_tasks_list = mapping_response['unmatched_tasks']

    tasks = matched_task_list + new_tasks_list

    if isinstance(jobRoleName, list):
        jobRoleName = jobRoleName[0]

    if isinstance(industryName, list):
        industryName = industryName[0]

    industryName = 'Information Technology'
    # Create job role node with attributes and label
    node_rel_query = (
        f'MERGE (jobRole:JobRole {{ name: "{jobRoleName}",seniority:"{seniority}" }})'
        f'ON CREATE SET jobRole.id = "{jobRoleId}" , jobRole.source = "enrichment"'
        f'MERGE (industry:Industry {{ name: "{industryName}" }})'
        f'ON CREATE SET industry.id = "{industryId}" , industry.source = "enrichment" '
        f'MERGE (jobRole)-[:IN_INDUSTRY]->(industry)'
        f'MERGE (jobRole)<-[:children]-(industry)'
    )

    # Create task nodes with attributes, label, and relationships to job role
    task_queries = [
        f'MERGE (task:Task {{name: "{task_name}"}})'
        f'ON CREATE SET task.id = "{uuid.uuid4()}", task.source = "enrichment"'
        f'MERGE (jobRole:JobRole {{ name: "{jobRoleName}",seniority:"{seniority}" }})'
        f'ON CREATE SET jobRole.id = "{jobRoleId}" , jobRole.source = "enrichment" '
        f'MERGE (jobRole)-[:HAS_SUBTASK]->(task)'
        f'MERGE (jobRole)-[:children]->(task);'
        for task_name in tasks
    ]

    set_rel_query = [
        f'Match (t:Task) where not t:Personal set t.value = 20',
        f'Match (j:JobRole) where not j:Personal set j.value = 75'
    ]

    return [node_rel_query] + task_queries + set_rel_query

@log_entry_exit
def execute_queries(queries):

    uri = NEO4J_URI
    username = NEO4J_USERNAME
    password = NEO4J_PASSWORD

    with GraphDatabase.driver(uri, auth=(username, password)) as driver:
        with driver.session() as session:
            for query in queries:
                r = session.run(query)
                summary = r.consume()
                counters = summary.counters
                
                print(f"Query:{query}")
                if counters.nodes_created:
                    print(f"{counters.nodes_created} nodes were created.")
                if counters.relationships_created:
                    print(f"{counters.relationships_created} relationships were created.")

    return "success"

@log_entry_exit
def enrich_neo4j(jobRoleName,seniority, industryName, tasks):
    group1_queries = create_queries(jobRoleName,seniority, industryName, tasks)
    print(group1_queries)
    execute_queries(group1_queries)
    print("Nodes Added")


@log_entry_exit
def create_course_queries(course):

    courseId = str(uuid.uuid4())

    contents = course['Course Content'].split(';')
    if len(contents) == 1:
        contents = course['Course Content'].split(',')

    content_task = []
    for task in contents:
        content_task.append({"task":task, "proficiency_level": "mid" })

    mapping_response = task_mapper(content_task)

    matched_task_list = mapping_response['matched_path']
    new_tasks_list = mapping_response['unmatched_tasks']

    tasks = matched_task_list + new_tasks_list

    # Create course node with attributes and label
    course_name = course['Course Name']
    duration = course['Course Duration']
    rating = course['Course Rating']
    url = course['Course URL']
    course_description = course['Course Description']

    node_rel_query = (
        f'MERGE (course:course {{ name: "{course_name}" }})'
        f'ON CREATE SET course.id = "{courseId}" , course.source = "enrichment", course.url = "{url}", course.duration = "{duration}", course.rating = "{rating}", course.description = "{course_description}" '
    )

    # Create task nodes with attributes, label, and relationships to course
    
    task_queries = [
        f'MERGE (task:Task {{name: "{task_name}"}})'
        f'ON CREATE SET task.id = "{uuid.uuid4()}", task.source = "enrichment"'
        f'MERGE (course:course {{ name: "{course_name}" }})'
        f'ON CREATE SET course.id = "{courseId}" , course.source = "enrichment", course.url = "{url}", course.duration = "{duration}", course.rating = "{rating}" , course.description = "{course_description}" '
        f'MERGE (course)-[:HAS_TASK]->(task)'
        for task_name in tasks
    ]


    return [node_rel_query] + task_queries 


@log_entry_exit
def enrich_neo4j_with_courses(courses):
    group1_queries = create_course_queries(courses)
    print(group1_queries)
    execute_queries(group1_queries)
    print("Nodes Added")


#code to generate queries from mapped skills - for personal kg
@log_entry_exit
def create_pg(mapped_skill_list, _profile , user_id, role, experience, seniority, salary):
    uri = NEO4J_URI
    username = NEO4J_USERNAME
    password = NEO4J_PASSWORD

    def create_nodes_and_relationships(tx, industry_name, discipline_name, megaskill_name, microskill_name, task_name, level, megaskill_id, microskill_id):
        query = (
        "MERGE (industry:Industry:Personal{name_id: $industryName, user: $profile, seniority: $seniority, user_id: $user_id , type: 'Industry' , value: 8}) "
        "MERGE (discipline:Discipline:Personal{name_id: $disciplineName, user: $profile, seniority: $seniority, user_id: $user_id , type: 'Discipline' , value: 8}) "
        "MERGE (megaskill:Megaskill:Personal{name_id: $megaskillName, user: $profile, seniority: $seniority, user_id: $user_id , megaskill_id: $mega_id , type: 'Megaskill', value: 6}) "
        "MERGE (microskill:Microskill:Personal{name_id: $microskillName, user: $profile, seniority: $seniority, experience : $experience, user_id: $user_id , microskill_id: $micro_id , type: 'Microskill', validation_status: 'Not Validated', value: 3 }) "
        "MERGE (task:Task:Personal{name_id: $taskName, user: $profile, seniority: $seniority, user_id: $user_id , level: $level, type: 'Task', value: 1}) "
        "MERGE (job:JobRole:Personal{name_id: $jobName, user: $profile, seniority: $seniority, salary: $salary, user_id: $user_id , type: 'JobRole', value: 1}) "
        "MERGE (industry)-[:HAS_DISCIPLINE]->(discipline) "
        "MERGE (industry)-[:children]->(discipline) "
        "MERGE (discipline)-[:REQUIRES_MEGASKILL]->(megaskill) "
        "MERGE (discipline)-[:children]->(megaskill) "
        "MERGE (megaskill)-[:REQUIRES_MICROSKILL]->(microskill) "
        "MERGE (megaskill)-[:children]->(microskill) "
        "MERGE (microskill)-[:INVOLVES_TASK]->(task) "
        "MERGE (microskill)-[:children]->(task) "
        "MERGE (task)-[:children]->(job) "
        "MERGE (task)<-[:Does]-(job) "
        )


        tx.run(query, industryName=industry_name, disciplineName=discipline_name, megaskillName=megaskill_name,
            microskillName=microskill_name, taskName=task_name, level = level, profile=_profile, user_id = user_id, jobName = role, mega_id = megaskill_id, micro_id = microskill_id, seniority=seniority, salary=salary, experience=experience)

    # Example usage
    for mapped_skill_str in mapped_skill_list:
        mapped_skill = json.loads(mapped_skill_str)
        industry_name = mapped_skill['Industry']
        discipline_name = mapped_skill['Discipline']
        megaskill_name = mapped_skill['Megaskill']
        microskill_name = mapped_skill['Microskill']
        task_name = mapped_skill['Task']
        level = mapped_skill['Level']
        megaskill_id = mapped_skill['Megaskill_ID']
        microskill_id = mapped_skill['Microskill_ID']

        with GraphDatabase.driver(uri, auth=(username, password)) as driver:
            with driver.session() as session:
                session.write_transaction(create_nodes_and_relationships, industry_name, discipline_name, megaskill_name,
                                        microskill_name, task_name, level, megaskill_id, microskill_id)




