import PyPDF2
import json
import utils.neo_utils as neo_utils
from integration.openai_integration import get_openai_response
from features.similarity import skill_mapper,task_mapper
from features.knowledge import save_resume_summary
from integration import openai_integration,neo4j_integration
from utils.config import log_entry_exit
from operator import itemgetter
from utils.neo_utils import execute_queries
from integration.openai_integration import get_openai_response
from integration.neo4j_integration import get_neo4j_response
from utils.config import log_entry_exit


@log_entry_exit
def extract_text_from_pdf(pdf_file):
    text = ""
    try:
        pdf_file.seek(0)  # Ensure the file pointer is at the beginning
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        for page in pdf_reader.pages:
            text += page.extract_text()
    except Exception as e:
        print(f"Error reading PDF file: {e}")
    return text

@log_entry_exit
def delete_job_roles_for_user(user_id):
    query = f"""match (m:Personal:JobRole{{user_id: "{user_id}"}}) detach delete m"""
    execute_queries([query])

def store_intro(user_id, resume_text):
    
    
    intro = get_openai_response("""You are a fluent job assistant tasked with providing a brief, 50-word introduction about the candidate's profile""", 
                                    f"""From the provided resume, summarize the candidate's name, area of experience, total years of experience, and relevant companies only if available. Don't include anything which is not available in resume.. 
                                    Avoid mentioning specific skills.
                                
                                    ##Candidate Resume: {resume_text}
                                
                                    Note : Skip things which are not there in resume , dont include any placeholders
                                """)
        
    intro = intro.replace('"', r'\"')
    intro = intro.replace("'", '')
    intro_query = f"""Merge (u:User{{ userid : '{user_id}'}}) SET u.intro = '{intro}' """  
    execute_queries([intro_query])

@log_entry_exit
def process_data(uploaded_pdf):
    
    #invalidate cache before enrichment
    # openai_integration.clear_cache()
    
    print("Process PDF and Manipulate Neo4j Graph")
    prompt = """
            Find which Job role from the following does the Input Text Job Description belongs to. 
            Create a new Job Role in case the Job Description is very different from the ones in the list

                                -   Data scientist
                                -   AI Developer
                                -   AI Architect
                                -   Machine Learning Engineer
                                -   Data Analyst
                                -   Research Scientist
                                -   Prompt Engineer

        
            Notes:
            Don't prefix or suffix Job role with it's seniority level,  Job Role can be only one of the six mentioned above. 

            Also Fetch:
            - seniority level: Job role seniority level. It must be one of the ( Junior , Mid Level or Senior)  
            - identify the Industry Job role falls into out of Information Technology, Banking,Telecom, Oil & gas, Healthcare, Manufacturing, Entertainment, Education, Automotive, Real Estate. 
            - tasks: relevant tasks needed to perform a Job role from the given job description along with a proficincy level. 

            The tasks need be a readable sentence. Eg. "Analyse information and data and uncover patterns, opportunities and impacts". 
            The tasks which might not be directly mentioned but could be related to the soft skills needed in the areas of such as Building Inclusivity, Collaboration, Communication, Customer Orientation, Developing People, Influence, Adaptability, Self Management, Digital Fluency, Global Perspective, Learning Agility, Problem Solving, Decision Making, Creative Thinking, Transdisciplinary Thinking, Sense Making should also be included
            Do not include multiple tasks into a single task. Make them granular. 
            Proficiency levels can be defined as follows:
            - Level Expert – Planning and Leading strategic work
            - Level Experienced – Managing and Executing operational activities 
            - Level Beginner - Supporting operational activities

            The soft skills are described as:
            Building Inclusivity: Collaborate with stakeholders from different backgrounds or with different abilities, including diversity dimensions such as race, ethnicity, religion, gender orientation, age, physical and learning ability, education, socio-economic status and political belief, to understand the interests of diverse groups and build an inclusive work environment.
            Collaboration: Manage relationships and work effectively with others to achieve goals
            Communication: Convey and exchange thoughts, ideas and information effectively through various mediums and approaches
            Customer Orientation: Identify the needs of customers, both internal and external, to deliver an effective customer experience
            Developing People: Empower others to learn and develop their capabilities to enhance their performance and achieve personal or professional goals
            Influence: Influence behaviours, beliefs or attitudes in order to achieve desired outcomes and solutions
            Adaptability: Exercise flexibility in behaviours or approaches to respond to changes and evolving contexts
            Self Management: Take ownership of managing one’s personal effectiveness, personal brand and holistic physical, mental, emotional and social well-being
            Digital Fluency: Leverage digital technology tools, systems, and software across work processes and activities to solve problems, drive efficiency and facilitate information sharing
            Global Perspective: Operate in cross-cultural environments, demonstrating an awareness of the wider global context and markets to identify potential opportunities and risks
            Learning agility: Deploy different learning approaches which enable continuous learning across different contexts to drive self-development and the achievement of long-term career goals
            Problem Solving: Generate effective and efficient solutions to solve problems and capitalise on new opportunities 
            Decision Making: Choose a course of action from several alternatives developed through a structured process in order to achieve intended goals
            Creative Thinking: Adopt diverse perspectives in combining ideas or information and making connections between different fields to create different ideas, improvements and solutions
            Transdisciplinary Thinking: Adopt diverse perspectives in combining ideas or information and making connections between different fields to create different ideas, improvements and solutions
            Sense Making: Leverage sources of qualitative and quantitative information and data to recognise patterns, spot opportunities, infer insights and inform

            Important Note - Do not provide any other information. No Description is needed.
                        
            Output should only contain a flat Json I repeat FLAT JSON with four keys :
                        
            **job_role** which should have the classified job category and 
            **industry** and 
            **seniority**. 
            **tasks** with proficiency level like Beginner, Experienced and Expert based on the task and also on seniority of the role

            This is a sample JSON structure of the output

            {
            "job_role": "Job Role",
            "industry": "Indsutry",
            "seniority": "seniority",
            "tasks": [
            {"task": "Task description", "proficiency_level": "level"},
            ]
            }

            Not even a single word before or end of the JSON is needed. No Explanation is needed. Only JSON should be the output. 
            Tasks should always be accompanied with level from list ( Beginner, Experienced or Expert )       

            **Input Text** : 

 """
        
    system_msg = 'You are helpful assistant which can undertand Job posting and fetch relevant information about a Job role. Job Roles are mentioned at the begining of Job Posting'
    
    if uploaded_pdf is not None:
        # Extracted text from PDF
        extracted_text = extract_text_from_pdf(uploaded_pdf)
        generated_data = get_openai_response(system_msg, prompt + extracted_text)
        print(generated_data)
        fetched_data = json.loads(generated_data)

    neo_utils.enrich_neo4j(fetched_data['job_role'],fetched_data['seniority'],fetched_data['industry'], fetched_data['tasks'])
    
    return create_enrichment_response(fetched_data['job_role'],fetched_data['seniority'])

import pandas as pd
@log_entry_exit
def process_course_data(uploaded_csv):
    
    if uploaded_csv is not None:
        # Extracted text from PDF
        extracted_data = pd.read_csv(uploaded_csv)
        extracted_data_dict = extracted_data.to_dict(orient='records')

        for course in extracted_data_dict:
            neo_utils.enrich_neo4j_with_courses(course)
    
    # return create_enrichment_response(course)

# process_course_data('/Users/hemantparashar/Downloads/Udemy_ds_courses (2).csv')


@log_entry_exit
def job_posting_summary():
    query = "match (m:JobPosting) return m.id as job_id, m.description as job_description"
    response = get_neo4j_response(query)
    for item in response:
        summary = get_openai_response("Create a 3 line summary of job discription", item['job_description'])
        summary = summary.replace('"', r'\"')
        summary = summary.replace("'", '')
        print(item['job_id'], summary)
        print("*************")

        query= f"match(m:JobPosting) where m.id = '{item['job_id']}' set m.job_summary = '{summary}' "
        neo_utils.execute_queries([query])

@log_entry_exit
def job_posting_seniority():
    query = "match (m:JobPosting) return m.id as job_id, m.description as job_description"
    response = get_neo4j_response(query)
    for item in response:
        summary = get_openai_response("identify seniority level of job from job description if experience is more than 10 years then only senior, 5 to 10 year is Mid Level from Senior, Mid Level, Junior. Output should be either Senior, Mid Level, Junior ", item['job_description'])
        summary = summary.replace('"', r'\"')
        summary = summary.replace("'", '')
        print(item['job_id'], summary)
        print("*************")

        query= f"match(m:JobPosting) where m.id = '{item['job_id']}' set m.llm_seniority = '{summary}' "
        neo_utils.execute_queries([query])

import uuid
import time

@log_entry_exit
def job_posting_tasks():
    query = "match (m:JobPosting) return m.id as job_id, m.description as job_description"
    response = get_neo4j_response(query)
    for item in response:
        

        try:
            tasks = get_openai_response("""Fetch one line tasks which are related to data science from given job description of job, output response format : [{"task": "Task description", "proficiency_level": "level"},{"task": "Task description", "proficiency_level": "level"}] """, item['job_description'])
            tasks = json.loads(tasks)
            print("*************",tasks)
            mapping_response = task_mapper(tasks,0.3)
            matched_path_list = mapping_response['matched_path']
            new_tasks_list = mapping_response['unmatched_tasks']

            print(matched_path_list)
            print(new_tasks_list)


            job_id = item['job_id']

            matched_task_queries = [
                f'MERGE (task:Task {{name: "{task_name}"}})'
                f'ON CREATE SET task.id = "{uuid.uuid4()}" '
                f'Merge (job:JobPosting {{ id : "{job_id}" }}) '
                f'MERGE (job)-[:HAS_TASK]->(task)'
                for task_name in matched_path_list
            ]

            new_task_queries = [
                f'MERGE (task:Task {{name: "{task_name}"}})'
                f'ON CREATE SET task.id = "{uuid.uuid4()}", task.source = "enrichment"'
                f'Merge (job:JobPosting {{ id : "{job_id}" }}) '
                f'MERGE (job)-[:HAS_TASK]->(task)'
                for task_name in new_tasks_list
            ]


            neo_utils.execute_queries(matched_task_queries + new_task_queries)
        except:
            pass

# job_posting_tasks()
# job_posting_summary()
# job_posting_seniority()

@log_entry_exit
def create_enrichment_response(job_role,seniority):

    aligned_query = f"""MATCH (disc:Discipline )--(mega:Megaskill)--(m:Microskill)--(t:Task)--(j:JobRole {{name: '{job_role}'}})
                    WHERE NOT disc:Personal AND j.seniority='{seniority}'
                    WITH disc, mega, m, COLLECT(t.name) AS task_list, COLLECT(t.level) AS task_level
                    WITH disc, mega, m, apoc.map.fromLists(task_list, task_level) AS task_map
                    WITH disc, mega, COLLECT(DISTINCT {{name_id: m.name, declining_skill: COALESCE(m.declining_skill, 'No'), task_list: task_map}}) AS microskills
                    WITH disc, COLLECT(DISTINCT {{name_id: mega.name, microskills: microskills}}) AS megaskills
                    RETURN COLLECT(DISTINCT {{
                        id: disc.name, 
                        Megaskills: megaskills}}) 
                    AS Discipline
                    """
    
    unaligned_query = f"""MATCH (j:JobRole {{name: '{job_role}', seniority: '{seniority}'}})--(t:Task)
                        where t.source = 'enrichment'
                        return 
                        distinct t.name as `Unaligned Task`"""

    new_tasks = []
    for item in neo4j_integration.get_neo4j_response(unaligned_query):
        new_tasks.append(item['Unaligned Task'])

    data = {
        'Job Category' : f'{job_role}',
        'Seniority' : f'{seniority}',
        'Aligned Tasks' : neo4j_integration.get_neo4j_response(aligned_query)
    }

    return { 'Aligned_Tasks' : data , 'Unaligned_Tasks' : new_tasks }


@log_entry_exit
def create_enrichment_response_v1(fetched_data):
    fetched_tasks = fetched_data['tasks']
    
    mapping_response = task_mapper(fetched_tasks)
    matched_path_list = mapping_response['matched_path']
    new_tasks_list = mapping_response['unmatched_tasks']
    
    mapped_tasks=[]
    for mapped_path_str in matched_path_list:
        mapped_path = json.loads(mapped_path_str)
        task_name = mapped_path['Task']
        mapped_tasks.append(task_name)

    aligned_skills = []

    for mapped_skill_str in matched_path_list:
        mapped_skill = json.loads(mapped_skill_str)
        
        del mapped_skill['TaskDescription']
        del mapped_skill['Level']
        del mapped_skill['Task']

        temp_dict = {}
        temp_dict['Job_Role'] = fetched_data['job_role']
        temp_dict['Seniority'] = fetched_data['seniority']
        for key,value in mapped_skill.items():
            temp_dict[key]=value

        aligned_skills.append(temp_dict)


    print(1)
    keys_to_sort_by = ['Industry', 'Discipline', 'Megaskill','Microskill']
    sorted_skills = sorted(aligned_skills, key=itemgetter(*keys_to_sort_by))

    print(1)
    return { 'Aligned_Tasks' : sorted_skills , 'Unaligned_Tasks' : new_tasks_list }


#upload resume to add personal knowledge graph
@log_entry_exit
def upload_docs(user_id, name , uploaded_pdf, is_pdf=True):
    # openai_integration.clear_cache()

    try:
        print("Process Resume")

        if uploaded_pdf is not None:

            # Extracted text from PDF
            # Extracted text from PDF

            if is_pdf:
                extracted_text = extract_text_from_pdf(uploaded_pdf)
            else:
                extracted_text = uploaded_pdf

            generated_json = get_scope(extracted_text)
            save_resume_summary(user_id, generated_json)
            
            try:
                store_intro(user_id, extracted_text)
            except Exception as e:
                print("Error in storing intorduction",e)
                pass

            role = generated_json['Job Role']
            seniority = generated_json['Seniority'] 
            salary = generated_json['Expected Salary']
            experience = generated_json['Total Experience']
            skills = generated_json['Technical Skills']
            projects = generated_json['Projects']
            other_skills = generated_json['Other Important Skills']
            

            mapped_skills = skill_mapper(skills + other_skills)

            mapped_skills_jsonl = []
            for skill in mapped_skills:
                skill_json = json.loads(skill)
                del skill_json['TaskDescription']
                mapped_skills_jsonl.append(skill_json)

            system_prompt = f"""
                As Skillio, your role is that of a mentor in an interview conversation focused on gathering information about a candidate's skills and validating them according to the skill framework mentioned later. 

                    Following is the highlight of the Resume of the candidate: 
                                
                    Following is the highlight of the Resume of the candidate: 

                    role : {role}
                    Seniority: {seniority}
                    experience : {experience}
                    skills : {skills}
                    projects : {projects}
                    buniness_skills : {other_skills}
            

                    <Skill Framework Starts Here>
                                    CoreSkills:
                                        {mapped_skills_jsonl}  
                    </Skill Framework Ends Here>            



                    Very Important: Ask only one question at a time. 
                    Very Important: Limit the number of questions to 10.
                    Very Important: Ask 3 Multiple Choice Questions out of the 10 Questions during the conversation.

                    Important: Do not mention the skill framework or a framework in any of your questions. 
                    Important: Do not mention skill levels or proficiency in your statements or questions. 
                    Important: Do not ask more than 2 question on a single topic. Move to the next topic.

                    During the conversation: 

                    1. Keep your questions limited to a maximum of 10, and ask them one at a time.
                    2. Encourage the student to elaborate and clarify their thoughts.
                    3. Prompt introspection and foster personal growth.
                    4. Maintain openness to different viewpoints, demonstrating intellectual humility.
                    5. Engage in dialectic exchange to refine ideas through dialogue.
                    6. Personalize your approach according to the learner's unique needs and abilities.
                    7. Value the process of inquiry above simply arriving at correct answers.
                    8. Stimulate the learner to pose their own questions and foster curiosity.
                    9. Keep your questions concise, with none exceeding two sentences and its important that you do not repeat or summarize parts of the last response from the candidate.
                                        

                    First discuss about a skill where the candidate has been placed at the highest level of proficiency. This is to give the candidate confidence in a space he or she is familiar with and to give the candidate the confidence that I know my stuff as an interviewer. It is a serious interview. So, Begin by trying to confirm that the skill level is indeed correct. Ask the candidate to expand on the work they have done specific to the skill to  confirm the skill level. Else, the candidate another question on the same skill before moving to the next question

                    Next ask a 21st century skill question, present it as a mini-challenge or a behavioural question. Do not ask verbatim from the examples below, be creative. 
                            For example: 
                            a. Share a challenge you had with a client during a project?. How did you handle it?
                            b. You're assigned a project with a tight deadline, and suddenly one of your key team members resigns. How would you handle this situation to ensure the project's success?
                            c. Imagine you're part of a remote team spread across different time zones. One team member consistently misses deadlines, affecting the entire team's progress. How would you address this issue and ensure effective collaboration?
                            d. You've been working on a project using a specific software for months, and suddenly the company decides to switch to a different platform. How would you adapt to this change and ensure a smooth transition while minimizing disruptions to the project?
                            e. Describe a specific situation where you had to work closely with a diverse team to achieve a common goal. What role did you play, and how did you contribute to the team's success?
                            f. Share an example of a complex problem you faced at work or in a project. How did you approach it, and what steps did you take to analyze and solve the issue? What were the outcomes?
                            g. Tell us about a time when you had to quickly adapt to unexpected changes in a project or work environment. How did you handle the situation, and what did you learn from the experience?
                            h. Describe a situation where you took on a leadership role, formal or informal, to guide a team or project. How did you inspire and motivate others, and what impact did your leadership have on the final outcome?
                            i. Reflect on a project or task that required you to work with individuals from different cultural backgrounds. How did you navigate cultural differences and ensure effective collaboration?

                    Next go to the 'cat on the wall' skills - The recent skills which are mapped at "Level 1",  to ensure that we confirm as many skills as possible and disregarding the ones that candidate does not have. focused on identifying the skills or discarding them. 

                    Intersperse the technical or functional questions with the 21st century core skills. Always present a problem or a situation and ask her for her response.

                    Ask her for additional information about her that the artifacts and resume do not cover. Can be Certifications or industry experience. If her response is again 'cat on the wall', ask a further question to confirm.

                    Evaluate their skills based on their responses, moving to the next topic if correct, and posing related questions if their response is unclear or if they answer 'I don't know.'

                    Conclude the discussion with a summary of their skill level according to the provided framework. In relation to the resume, address a project, skills, and overall experience.

                    Ensure you incorporate a skill assessment framework with 10 questions, covering at least one question per level. Connect one of these questions to the student's current or desired job role mentioned in the resume.


                    Important Note - End chat gracefully by thanking and asking to have a look of Personal Skill Map generated after the chat
                    Last sentence should always be - Good Bye.

            """    
            print("7")
            return name, role, seniority, salary, experience, skills, projects, other_skills, mapped_skills, system_prompt

    except Exception as e:
        print(e)
        raise e
    
@log_entry_exit
def create_personal_graph(mapped_skills,name,user_id, role, experience, seniority, salary):
    print("creating pg")
    neo_utils.create_pg(mapped_skills, name, user_id,role, experience, seniority, salary)

@log_entry_exit
def get_scope(uploaded_pdf):
        
        try:
            prompt = f"""{uploaded_pdf}
                    Given above piece of text containing information about a candidate and a job role, extract the following details in JSON. Keys of JSON Object are:

                        1. **Job Role:**
                        - Assign job role from Data Scientist, Machine Learning Engineer, Research Scientist , Data Analyst, AI Architect , Software Developer. Do not include seniority in Job Role.

                        2. **Candidate Name:**
                        - Identify and return the name of the candidate mentioned in the text.

                        3. **Total Experience:**
                        - Extract and return the Work experience of the candidate in following format
                         example:
                                [ {{
                                        "company_name" : "Company Name",
                                        "description" : "Company Description",
                                        "start_date" : "start date",
                                        "end_date" : "end date"
                                }},
                                {{
                                        "company_name" : "Company Name",
                                        "description" : "Company Description",
                                        "start_date" : "start date",
                                        "end_date" : "end date"
                                }}]
                        

                        4. **Technical Skills:**
                        - Identify and return a list of skills mentioned in the text, Also mention in bracket a short description with each skill, like what that skill is useful for. 
                        some examples technical are:
                            ["Incorporate Libraries", "Improve code performance", "Write code using proper syntax and structure", "Contrast common data types", "Select appropriate data types and structures for a given context", "Contrast common data structures", "List common methods by which datasets are generated", "Identify common applications of data", "Analyze datasets for use in a ML or AI setting", "Distinguish between common types of licenses attached to data and software", "Apply relevant government regulations (such as PIPEDA)", "Adhere to the rights of data producers and responsibilities of data consumers", "Verify consent in data collection and use", "Apply best practices to minimize unintended training bias in models	", "Avoid unintended bias in data", "Improve data quality", "Address privacy concerns", "Assess data quality", "Calculate new properties", "Isolate datasets from within a larger data structure (querying)", "Use common encryption techniques", "Apply the principle of least privilege", "Present data in an easily understandable form", "Interpret data presented graphically", "Report statistical properties", "Interpret data presented as a table", "Process data using descriptive statistics", "Apply probability concepts in random situations", "Quantify relationship between two variables", "Use systems of linear equations", "Determine result of common operations", "Apply differential calculus to problems in AI", "Determine the derivative of a function", "Apply integral calculus to problems in AI", "Determine the integral of a function", "Interpolate data points with cubic splines", "Interpolate data points with polynomials (such as Lagrange, Newton, Neville)", "Fit data points with least-square polynomials (including line)", "Identify the impact of truncation errors", "Solve initial value problems with Euler and Runge-Kutta methods", "Solve two-point boundary problems with finite differences", "Incorporate code requirements in unit tests", "Develop complex applications incrementally", "Implement automated testing through continuous integration", "Employ the basic features of git", "Publish code to a repository", "Ensure code quality", "Define new tables", "Execute complex queries", "Manipulate records", "Execute complex queries", "Create records", "Manipulate records", "Compute features for different types of data (such as categorical, numerical, time series)", "Evaluate features for use in ML models", "Resample large datasets", "Use data structures native to machine learning libraries", "Connect data sources to models", "Tune hyperparameters of classification and regression methods", "Apply correct performance measures for regression, and binary and multi-class classifications", "Divide data into train, test, and validation sets", "Parametrize and apply classification methods", "Parametrize and apply regression methods", "Apply correct performance measures", "Parametrize and apply clustering methods", "Describe architectures for privacy-preserving AI deployments", "Review explainability techniques for AI models (such as SHAP, LIME)", "Identify safety issues with AI models", "Distinguish between technological artifacts that use and do not use AI", "Analyze features that make an entity intelligent", "Discuss the relation between AI models and biology", "Evaluate AI systems for specific applications", "Apply multi-layer neural networks for supervised learning", "Use multi-layer neural networks", "Generate data with deep learning models", "Use data with Convolutional Neural Networks (CNNs)", "Build CNNs and RNNs", "Learn behaviors with deep reinforcement learning (RL)", "Work with file systems", "Process data stored in various file systems", "Manage file systems", "Manage database systems", "Use database systems", "Process data stored in various databases", "Use distributed clusters to train data models", "Use a cluster to carry out ML or AI tasks", "Execute parallel programs", "Contrast multi-threaded single-core CPU, multi-core CPUs, and  Graphical Processing Units (GPUs)", "Contrast Infrastructure as a Service (IaaS) to Platform as a Service (PaaS) and Software as a Service (SaaS)", "Build virtual environments for distribution to cloud", "Scale services depending on workload", "Use services from the main cloud providers (such as AWS, Azure, Google)", "Ensure safety at rest", "Ensure safety in transit"]

                        5. **Seniority:**
                        - Which seniority level candidate belongs to out of Junior, Mid Level or Senior. Return the appropriate label.

                        6. **Projects:**
                        - Extract and return the Projects mentioned in the text in in a json format 

                        7. **Other Important Skills**
                        -Derrive Non Technical skills or Business skills from resume, Also mention in bracket a short description with each skill, like what that skill is useful for
                        some example Non Technical skills or Business skills are:
                        ["Demonstrate sensitivity to the differences in diversity dimensions and perspectives", "Oversee the development and implementation of  processes and practices which build an inclusive work environment and enable diverse groups to work effectively together", "Manage relationships across diverse groups within the organisation", "Contribute to a positive and cooperative working environment by fulfilling own responsibilities, managing interpersonal relationships and providing support to others to achieve goals", "Build relationships and work effectively with internal and external stakeholders to create synergies in working towards shared goals", "Establish team effectiveness and manage partnerships to create a cooperative working environment which enables the achievement of goals", "Communicate with others to share information, respond to general inquiries and obtain specific information", "Tailor communication approaches to audience needs and determine suitable methods to convey and exchange information", "Synthesise information and inputs to communicate an overarching storyline to multiple stakeholders", "Demonstrate an understanding of customer needs or objectives to respond in a way which delivers an effective customer experience", "Foster the creation of an effective customer experience", "Build relationships with customers to anticipate needs and solicit feedback to improve the customer experience", "Foster a conducive environment to enable employees’ professional and personal development, in alignment with the organisation’s objectives and goals", "Develop and coach team members to identify and leverage their strengths to enhance performance", "Create individual career and development plans, and support co-workers in performing their work activities", "Build consensus with stakeholders to achieve desired outcomes on matters of strategic importance", "Demonstrate empathy to understand the feelings and actions of others and communicate in ways that limit misunderstandings and influence others on operational issues", "Develop relationships with stakeholders to build confidence, alignment and communicate desired purpose, goals or objectives", "Foster a culture of flexibility that caters to changes and evolving contexts", "Manage change in evolving contexts", "Modify behaviours and approaches to respond to changes and evolving contexts", "Evaluate strategies to manage own well-being, personal effectiveness and personal brand", "Exercise self-awareness by monitoring own behaviours and ways of working in personal and professional capacities, and implement techniques for improvement", "Analyse own well-being and personal effectiveness to develop strategies to regulate self and build personal brand", "Drive the creation of a digital culture and environment, educating stakeholders across the organisation on the benefits and risks of digital technology tools, systems and software", "Identify opportunities and evaluate risks of integrating digital technology tools, systems and software across work processes and activities", "Perform work processes and activities using identified digital technology tools, systems and software", "Develop global networks and determine impact of global context and trends on the organisation’s vision, objectives and operating climate", "Demonstrate an understanding of global challenges and opportunities to work effectively in a cross-cultural environment", "Lead the resolution of the challenges of operating in a cross-cultural environment and build the organisation’s capabilities to compete in a global environment", "Establish an organisational culture of continuous learning to encourage the adoption of new learning approaches and identification of new learning opportunities", "Deploy various learning approaches in different settings to maximise opportunities for learning and self-reflection and measure their impact on the achievement of career goals", "Identify opportunities and targets for learning to facilitate continuous career development", "Determine underlying causes of problems and collaborate with other stakeholders to implement and evaluate solution", "Determine underlying causes of problems and collaborate with other stakeholders to implement and evaluate solution", "Identify problems and implement guidelines and procedures to solve problems and test solutions", "Define decision making criteria, processes and strategies and evaluate their effectiveness", "Follow processes to make decisions which achieve intended goals using given information and guidelines", "Implement structured decision making processes and analyse multiple sources of information to propose solutions", "Cultivate a culture of innovation and creativity across the organisation to push boundaries and reshape goals and possibilities", "Integrate multiple ideas and information from across various fields to develop solutions and new ways of working which address specific issues and deliver impact", "Connect ideas or information to propose and test ideas, improvements and solutions which challenge current assumptions or ways of working", "Endorse collaboration and the integration of knowledge across disciplines to make decisions and solve problems within and outside the organisation", "Identify opportunities for transdisciplinary collaboration and knowledge transfer to facilitate the integration of knowledge from different disciplines", "Explore concepts from outside one’s field of expertise to supplement one’s knowledge, proficiency and work practices", "Analyse information and data and uncover patterns, opportunities and impacts", "Organise and interpret information to identify relationships and linkages", "Evaluate relationships, patterns and trends to inform actions and generate wider insights", "Evaluate the organizational context", "Map data journey", "Enable decision makers to select a use case", "Analyze the quality and availability of data sources inventory", "Establish a framework based on evaluation factors", "Baseline existing project context (human, data, infrastructure, sponsor)", "Recommend training plan to bridge the skills gap for the project team and involved stakeholders", "Estimate project activities and required effort", "Negotiate Definition of Done (DoD) for deliverables with the project team", "Consolidate the project roadmap", "Lead AI implementations", "Overcome existing and new roadblocks", "Coach individual contributors", "Establish realistic expectations amongst stakeholders", "Manage crisis, hype, and noise around the AI project", "Implement a project status tracking system", "Establish DevOps foundation for AI project lifecycle", "Enable knowledge transfer sessions", "Organize project assets for delivery (such as code and documents)", "Facilitate client discussions and demonstrations", "Provide high-level guidance and recommendations for use case details", "Evaluate organizational context", "Deliver procurement-related information to AI adopters (clients)", "Coordinate internal stakeholders to collect available technical and business information (such as project goals, technical environment, and special requirements)", "Draft documentation for the request for proposal (RFP), request for quotation (RFQ), and request for information (RFI) processes", "Analyze the technological and business contexts of potential partners", "Draft potential synergies based on company activities and gaps", "Define collaboration system for new AI projects", "Analyze technical gaps between the company and the partner", "Translate business-oriented use cases into AI and machine learning (ML) problems", "Link technical AI models and metrics to business goals", "Analyze expected impact of cloud for data and AI activities", "Define the gap between current infrastructure and available options", "Estimate human requirements per technical track (such as science, development)", "Select best infrastructure options based on context", "Choose potential/required tools for data and AI", "Obtain executive support for envisioned expenses", "Draft a multi-category budget for data and AI projects"]
                        
                        8. **Expected Salary**
                        -  Pick a salary from below according to Job Role & Seniority, should be just a number
                            
                            Job Role, Seniority, Salary
                            Data Scientist,Junior,1500000
                            Data Scientist,Mid,5000000
                            Data Scientist,Senior,10000000
                            AI Architect,Junior,1650000
                            AI Architect,Mid,5500000
                            AI Architect,Senior,11000000
                            AI Developer,Junior,1200000
                            AI Developer,Mid,4000000
                            AI Developer,Senior,8000000
                            Data Analyst,Junior,900000
                            Data Analyst,Mid,3000000
                            Data Analyst,Senior,6000000
                            Machine Learning Engineer,Junior,180000
                            Machine Learning Engineer,Mid,6000000
                            Machine Learning Engineer,Senior,12000000
                            Research Scientist,Junior,2025000
                            Research Scientist,Mid,6750000
                            Research Scientist,Senior,13500000

    
                        Ensure that your solution is capable of handling variations in the way information is presented in the text and can provide accurate results even in the presence of noise or ambiguity.
                        You should not provide any bacticks or irrelevant information. Don't mention words like json in your response.
                        Avoid giving any explanation or context in your response. Only provide the required information in the specified format.
                        """
            
            
            extract_skills = openai_integration.get_openai_response("You are a helpful assistant who generates JSON according to prompt",prompt)

            return json.loads(extract_skills)
        except Exception as e:
            raise e
        


