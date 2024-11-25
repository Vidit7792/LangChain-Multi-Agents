
import sys
from integration.openai_integration import  get_openai_response
from utils.config import log_entry_exit

Industry_Classifier = """

You are a top-tier algorithm for a skill intelligence platform which can carefully classify each relevant senetence of following Text into the most accurate Industry and Discipline combination from the predefined list of Industries and their respective disciplines below. 

Goal:
Given a text document that is potentially relevant to this activity and a list of Industries and Disciplines, identify all Industries and Discipline for each sentence within the text.

Steps:
1. Chunk the text into sentences
2. For each identified sentence, extract the following information:
- Industry: Name of the Industry
- Discipline: Name of the Discipline

Instructions:
Accuracy is critical, so consider the specific terms, topics, and context of the text when selecting an Industry and please mention "Other" as an Industry if you do not have a good confidence in any of the Industries in the pre-defined list.
It's important that you only classify sentences which contain a skill a person could have to do a job or a job related task - these are the only relevant sentences for you. Any generic sentence can be put in the "NA" class.
21st century skills are very important and should not be put in "Cross Industry " instead of the "Other" class.

Text:
{job_description}

Industries and their respective disciplines:
1. Information Technology
    Software Development & Engineering
    Data Science & Analytics
    Artificial Intelligence & Machine Learning
    Cybersecurity
    Cloud Computing
    IT Project Management
    Digital Technologies
    Networking & Telecommunications
    Enterprise Architecture
    IT Support and Operations
    Database Management
    UX/UI Design
    IoT
    Business Analysis
2. Healthcare
	Medical Practice
	Nursing
	Healthcare Administration
	Pharmaceuticals
	Telemedicine
	Biomedical Engineering
3. Financial Services
	Investment Banking
	Financial Analysis
	Risk Management
	Fintech
	Accounting
	Audit & Compliance
4. Manufacturing
	General Manufacturing
	Precision Engineering
	Biopharmaceuticals Manufacturing:
	Electronics:
	Food Manufacturing:
5. Retail & E-commerce 
	Merchandising
	Customer Service
	Supply Chain Management
	E-commerce Platforms
	Digital Marketing
6. Energy & Utilities
	Renewable Energy
	Oil & Gas
	Energy Management
	Utility Operations
	Environmental Engineering
7. Education & Training
	Curriculum Development
	Educational Technology
	Instructional Design
	Corporate Training
	Research & Development
	Higher Education
	Early Childhood
	Child Development
8. Telecommunications
	Network Engineering
	Telecom Infrastructure
	Customer Support
	Wireless Communications
	Internet of Things (IoT)
9. Construction & Real Estate
	Project Management
	Civil Engineering
	Architecture
	Urban Planning
	Facility Management
10. Logistics & Transportation
	Supply Chain Management
	Fleet Management
	Logistics Planning
	Warehousing
	Transportation Management
11. Media & Entertainment
	Content Creation
	Digital Marketing
	Broadcasting
	Game Development
	Media Production
12. Hospitality & Tourism
	Hotel Management
	Event Planning
	Travel Services
	Food & Beverage Management
	Customer Experience Management
13. Government & Public Sector
	Public Policy
	Administration
	Law Enforcement
	Urban Planning
	Public Health
14. Agriculture & Food Production
	Agronomy
	Farm Management
	Food Safety
	Agribusiness
	Sustainable Farming
15. Apparel & Footwear
	Design & Product Development
	Textile Engineering
	Fashion Merchandising
	Supply Chain Management
	Quality Control
	Retail Management
	Sustainability Practices
	Brand Management
	E-commerce
	Trend Forecasting
16. Automotive
	Automotive Engineering
	Vehicle Design
	Electric Vehicles
	Supply Chain Management
	After-Sales Service
17. Aerospace & Defense
	Aerospace Engineering
	Defense Technology
	Project Management
	Compliance & Regulation
	Cybersecurity
18. Legal Services
	Corporate Law
	Intellectual Property
	Litigation
	Contract Law
	Compliance & Ethics
19. Human Resources
	Talent Acquisition
	Learning & Development
	Employee Relations
	Compensation & Benefits
	Diversity & Inclusion
20. Marine and Offshore
	Marine Engineering
	Offshore Operations
	Naval Architecture
	Shipbuilding
	Marine Safety
21. Security
	Security Management
	Surveillance & Monitoring
	Risk Assessment
	Cybersecurity
	Law Enforcement
22. Workplace Safety and Health 
	Occupational Safety
	Health Regulations
	Risk Management
	Incident Response
	Compliance
23. Design
	Product Design
	Graphic Design
	User Experience (UX) Design
	Fashion Design
	Architectural Design
24. Landscape   
	Horticulture
	Landscape Design
	Urban Green Spaces
	Environmental Sustainability
	Park Management
25. Cross Industry
        21st Century Skills    
            Interacting with Others
            Staying Relevant
            Thinking Critically

            
Response Format:

[
{{
     "industry": "industry1",
     "discipline": "discipline1",
     "text" : ["sentence1","sentence2"]
}},
{{
     "industry": "industry2",
     "discipline": "discipline2",
     "text" : ["sentence1","sentence2"]
}},
{{
     "industry": "Cross Industry",
     "discipline": "21st Century Skills",
     "text" : ["sentence1","sentence2"]
}},
{{
     "industry": "Other",
     "discipline": "Other",
     "text" : ["sentence1","sentence2"]
}},

]

Note: Don't include any backtick or word json in your response. All the sentences in the same industry should be grouped together. In case of Industry "Other" all the sentences should be grouped together and discipline should be "Other" for all the sentences."""


Framework_Generator_New = """
You are a top-tier algorithm designed for extracting information in structured formats to build a Skill and Competency framework.
It's critical that the goal of this framework is to outline the core competencies (knowledge, skills, and abilities) required by practitioners in the technical, business, and human domains
It's vital to not include Tasks or Subtasks for learners of the competencies, for example, "Learn something" or "Familiarize with something".
Try to capture as much information from the text as possible without sacrificing accuracy. Do not add any information that is not explicitly mentioned in the text.

The Competency framework is represented as a hierarchy in the following order:

Industry - The primary industry or sector where the skills are applied, for example, Information Technology, Healthcare.
Discipline - A broad classification that defines a category of skills, for example, "Cyber Security", "Artificial Intelligence", and other specialized fields.
Megaskill - A Discipline is further divided into focused Themes using nouns, like "Supervised Learning", to categorize skills into specific subject areas. 
Microskill - The core set of knowledge, skills, and abilities required for practitioners, such as "Managing a supervised learning framework".
Levels - The Microskill proficiency of practitioners for child tasks and subtasks is categorized into three levels, with Level 1 being the lowest and Level 3 being the highest.
Tasks - Essential supporting skills necessary to demonstrate the Microskill, such as "Dividing data into training, testing, and validation sets".
Subtask - The most granular level of the framework, describing specific actions needed to fulfill main and supporting skills, such as "Applying K-fold validation".

The JSON format of the Skill framework is:

{{
  "Industry": "industry",
  "Disciplines": [
    {{
      "name": "discipline",
      "Megaskills": [
        {{
          "name": "Supervised Learning",
          "Microskills": [
            {{
              "name": "Manage a supervised learning framework",
              "Levels": [
                {{
                  "Level": 1,
                  "Description": "Basic understanding",
                  "Tasks": [
                    {{
                      "name": "Understand supervised learning basics",
                      "Subtasks": [
                        {{
                          "name": "Learn supervised learning algorithms"
                        }},
                        {{
                          "name": "Familiarize with data preprocessing"
                        }}
                      ]
                    }}
                  ]
                }},
                {{
                  "Level": 2,
                  "Description": "Practical application",
                  "Tasks": [
                    {{
                      "name": "Implement supervised learning models",
                      "Subtasks": [
                        {{
                          "name": "Split data into training and testing sets"
                        }},
                        {{
                          "name": "Train and evaluate models"
                        }}
                      ]
                    }}
                  ]
                }},
                {{
                  "Level": 3,
                  "Description": "Expertise",
                  "Tasks": [
                    {{
                      "name": "Optimize supervised learning models",
                      "Subtasks": [
                        {{
                          "name": "Tune hyperparameters"
                        }},
                        {{
                          "name": "Implement ensemble methods"
                        }}
                      ]
                    }}
                  ]
                }}
              ]
            }}
          ]
        }}
      ]
    }}
  ]
}}

Make sure to answer in the same format as that of skill framewrok and do not include any explanations. Ensure that Skill framework should be coherent and easily understandable. 
Using this knowledge can you create the JSON format skill framework of using the following input:

Industry: {industry_name}
Discipline: {discipline_name}
{text}

"""

Framework_Generator_Existing = """
It's critical that the goal of this framework is to outline the core competencies (knowledge, skills, and abilities) required by practitioners in the technical, business, and human domains
It's vital to not include Tasks or Subtasks for learners of the competencies, for example, "Learn something" or "Familiarize with something".
Try to capture as much information from the text as possible without sacrificing accuracy. Do not add any information that is not explicitly mentioned in the text.

The Competency framework is represented as a hierarchy in the following order:

Industry - The primary industry or sector where the skills are applied, for example, Information Technology, Healthcare.
Discipline - A broad classification that defines a category of skills, for example, "Cyber Security", "Artificial Intelligence", and other specialized fields.
Megaskill - A Discipline is further divided into focused Themes using nouns, like "Supervised Learning", to categorize skills into specific subject areas. 
Microskill - The core set of knowledge, skills, and abilities required for practitioners, such as "Managing a supervised learning framework".
Levels - The Microskill proficiency of practitioners for child tasks and subtasks is categorized into three levels, with Level 1 being the lowest and Level 3 being the highest.
Tasks - Essential supporting skills necessary to demonstrate the Microskill, such as "Dividing data into training, testing, and validation sets".
Subtask - The most granular level of the framework, describing specific actions needed to fulfill main and supporting skills, such as "Applying K-fold validation".

The JSON format of the Skill framework is:

{skill_framework_industry_discipline_combination}

Make sure to answer in the same format as that of skill framewrok and do not include any explanations. Ensure that Skill framework should be coherent and easily understandable. 
Using this knowledge can you update the JSON format skill framework of using the following input:

Industry: {industry_name}
Discipline: {discipline_name}
{text}


"""

Final_Framework_Merger = """
		You are an expert in merging new generated skill framework with existing skill framework.
          
        Existing Skill framework : {existing_framework_industry}
         
           and
        
        New Skills : {new_skills}

        Try to fit existing skills in appropriate places in existing framework, avoid adding duplicate skills which are already present in existing framework.
        Whenever a new skill is added add one attribute source : 'enrichment' to know this is the newly added skill.
        Follow the same format as exisitng framework and Generate a Merged JSON.
        Donot include and backtick, word json or any explanation in your response
"""

@log_entry_exit
def get_industry_classification(job_description):
    return get_openai_response("You are an expert Classifcation agent who can classify industry from given list of Industries for a given Job Discription",Industry_Classifier.format(job_description=job_description))

@log_entry_exit
def get_discipline_classification(job_description, industry):
  industry_discipline_map = {}
  if isinstance(industry, str):
    industry = industry.split(',')
  
  disciplines = []
  for ind in industry:
    print(ind)
    discipline = get_openai_response("You are an expert Classification agent who can classify Discipline from given list of Disciplines for a given Job Description and Industry", Discipline_Classifier.format(job_description=job_description, industry=ind))
    disciplines.append(discipline)
    industry_discipline_map[ind] = discipline

  return industry_discipline_map

@log_entry_exit
def get_job_classification(job_description):
    industry = get_industry_classification(job_description)
    discipline = get_discipline_classification(job_description, industry)
    return industry, discipline

import json
@log_entry_exit
def get_framework_generator(user_feedback, framework ):
	framework = json.dumps(framework)
	user_feedback = user_feedback[0]
	print(user_feedback)
	if not framework:
		print("No Framework")
		return get_openai_response("You are an expert framework creation agent who can generate Framework from given list of Industries, Discipline and sample framework for a given Job Discription, Your Response should not contain any backtick or word json", Framework_Generator_New.format(industry_name=user_feedback['industry'], discipline_name=user_feedback['discipline'], text=user_feedback['text']))
	else:
		print("Framework")
		return get_openai_response("You are an expert framework creation agent who can generate Framework from given list of Industries, Discipline and existing framework for a given Job Discription, Your Response should not contain any backtick or word json", Framework_Generator_Existing.format(industry_name=user_feedback['industry'], discipline_name=user_feedback['discipline'], text=user_feedback['text'], skill_framework_industry_discipline_combination=framework)) 


# @log_entry_exit
# def get_final_framework(industry_dict, existing_framework):
# 	try:
# 		response = []
# 		for industry_name, industry_content in industry_dict.items():
# 			if industry_name != "NA":
# 				print(industry_name, industry_content )
# 				existing_framework_industry = existing_framework[industry_name]
# 				temp_response = json.loads(get_openai_response("You are an expert in merging new generated skill framework with existing skill framework.", Final_Framework_Merger.format(new_skills = industry_content, existing_framework_industry = existing_framework_industry )))
# 				response.append(temp_response)

# 		return response
# 	except Exception as e:
# 		print("Error occurred:", str(e))
# 		raise e
	
import json
import concurrent.futures

@log_entry_exit
def get_final_framework(industry_dict, existing_framework):
    try:
        response = []
        def process_industry(industry_name, industry_content):
            existing_framework_industry = existing_framework[industry_name]
            merged = Final_Framework_Merger.format(
                new_skills=industry_content,
                existing_framework_industry=existing_framework_industry
            )
            temp_response = json.loads(get_openai_response(
                "You are an expert in merging new generated skill framework with existing skill framework.",
                merged
            ))
            return temp_response

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(process_industry, name, content)
                for name, content in industry_dict.items() if name != "NA"
            }
            for future in concurrent.futures.as_completed(futures):
                response.append(future.result())

        return response
    except Exception as e:
        print("Error occurred:", str(e))
        raise e