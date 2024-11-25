from fastapi import APIRouter
from fastapi import BackgroundTasks, Depends, HTTPException
from utils.model_classes import ExceptionMessageEnum
from http import HTTPStatus
from utils.model_classes import StatusEnum,Status,Message,SkillMapper
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

from integration import azur_blob_storage, neo4j_integration
from fastapi import HTTPException
from utils.common import get_user_details
load_dotenv()


job_object = {}

build_router = APIRouter()


@log_entry_exit
@build_router.delete("/build/personal_knowledge_graph")
def delete_personal_knowledge_graph(user_id: str, api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Query KG
    '''
    try:
        res = knowledge.personal_knowledge_graph(user_id)  
        return res
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))


@log_entry_exit
def update_pg(text, job):
    '''
    Method takes uncleansed Inputs as input and returns cleansed Input as output
    '''
    try:
        # Process and cleanse conversation Inputs
        user_id = job_object[job.job_uuid.__str__()].user_id
        user_name = job_object[job.job_uuid.__str__()].name

        name_, role_, seniority_, salary_, experience_,  skills, projects, other_skills, mapped_skills_after_chat, system_prompt = enrichment.upload_docs(user_id, user_name, text, False)

        role = job_object[job.job_uuid.__str__()].role 
        seniority = job_object[job.job_uuid.__str__()].seniority 
        salary = job_object[job.job_uuid.__str__()].salary 
        experience = job_object[job.job_uuid.__str__()].experience 
        
        
        enrichment.create_personal_graph(mapped_skills_after_chat, user_name, user_id, role, json.dumps(experience), seniority, salary)
        knowledge.set_similarity(user_id)
        job_object[job.job_uuid.__str__()].status = StatusEnum.SUCCESS

    except Exception as e:
        logging.error(ExceptionMessageEnum.DATA_CLEANSING_ERROR.value.format(e))
        job_object[job.job_uuid.__str__()].status = StatusEnum.ERROR




@log_entry_exit
def resume_upload(pdf_file, job):
    '''
    Method takes uncleansed Inputs as input and returns cleansed Input as output
    '''
    try:
        # Process and cleanse conversation Inputs
        user_id = job_object[job.job_uuid.__str__()].user_id
        user_name = job_object[job.job_uuid.__str__()].name

        name, role, seniority, salary, experience,  skills, projects, other_skills, mapped_skills, system_prompt = enrichment.upload_docs(user_id, user_name, pdf_file)
       
        # Update job result and status
        # job_object[job.job_uuid.__str__()].name = name
        job_object[job.job_uuid.__str__()].role = role
        job_object[job.job_uuid.__str__()].seniority = seniority
        job_object[job.job_uuid.__str__()].salary = salary
        job_object[job.job_uuid.__str__()].experience = experience
        job_object[job.job_uuid.__str__()].skills = skills
        job_object[job.job_uuid.__str__()].projects = projects
        job_object[job.job_uuid.__str__()].other_skills = other_skills
        job_object[job.job_uuid.__str__()].mapped_skills = mapped_skills
        job_object[job.job_uuid.__str__()].system_prompt = system_prompt
        job_object[job.job_uuid.__str__()].status = StatusEnum.SUCCESS


        knowledge.reset_chat_status(user_id, job.job_uuid.__str__(),job_object[job.job_uuid.__str__()].filename)
        enrichment.create_personal_graph(mapped_skills, user_name, user_id, role, json.dumps(experience), seniority, salary)
        knowledge.set_similarity(user_id)
        knowledge.store_timeline(user_id, experience)

        job_object[job.job_uuid.__str__()].status = StatusEnum.SUCCESS
        azur_blob_storage.upload_file_to_blob(job.job_uuid.__str__(), job_object[job.job_uuid.__str__()], user_name=user_name, user_id=user_id)

    except Exception as e:
        logging.error(ExceptionMessageEnum.DATA_CLEANSING_ERROR.value.format(e))
        job_object[job.job_uuid.__str__()].status = StatusEnum.ERROR




@log_entry_exit
@build_router.post("/build/upload", response_model=Status, status_code=HTTPStatus.ACCEPTED)
async def upload_resume(background_tasks: BackgroundTasks, user_id: str, pdf_file: UploadFile = File(...), api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Create Personal Knowledge Graph
    '''
    try:
        # Create a new job and add it to the job_object

        enrichment_job = SkillMapper()
        job_uuid = str(enrichment_job.job_uuid.__str__())
        job_object[job_uuid] = enrichment_job
        job_object[job_uuid].user_id = str(user_id)
        job_object[job_uuid].filename = pdf_file.filename

        user_details = get_user_details(user_id)
        user_name = user_details['first_name']+' '+ user_details['last_name']
        job_object[job_uuid].name = user_name

        azur_blob_storage.upload_file_to_blob(job_uuid, job_object[job_uuid], user_name=user_name, user_id=user_id)

        # Add a background task to run data cleansing asynchronously
        background_tasks.add_task(resume_upload, pdf_file.file, enrichment_job)
        return Status(transaction_id=job_uuid, status=enrichment_job.status)
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))

#chat APIs

class ConversationManager:
    def __init__(self):
        self.conversation = {}

conversation_manager = ConversationManager()

@log_entry_exit
def initiate_chat(job , prompt = None, memory_chat = None):

    system_prompt_msg = None
    if prompt == None:
        system_prompt_msg = job.system_prompt.replace("{", "").replace("}", "")   
    else:
        system_prompt_msg = prompt.replace("{", "").replace("}", "") 
        
    system_prompt = ChatPromptTemplate(
        messages=[
            SystemMessagePromptTemplate.from_template( system_prompt_msg ),
            # The `variable_name` here is what must align with memory
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessagePromptTemplate.from_template("{content}"),
        ]
    )

    model = ChatOpenAI(model='gpt-3.5-turbo-1106')
    if not memory_chat:
        memory_chat = ConversationSummaryBufferMemory(llm=model, memory_key="chat_history", return_messages=True)
  
    conversation = LLMChain(
    llm=model,
    prompt=system_prompt,
    memory=memory_chat,
    verbose=True
    )

    return conversation


@log_entry_exit
def store_chat_memory_in_storage(memory_object, transaction_id):

    '''
    Store chat memory in Azure blob
    '''

    extracted_messages = memory_object.memory.chat_memory.messages

    ingest_to_db = messages_to_dict(extracted_messages)

    azur_blob_storage.upload_file_to_blob(f'{transaction_id}_CM', ingest_to_db)



@log_entry_exit
def retrieve_chat_memory_from_storage(transaction_id):

    '''
    Retrieve chat memory from Azure blob
    '''
    try:

        retrieve_from_db = azur_blob_storage.download_file_from_blob(f'{transaction_id}_CM.pkl')
        retrieve_from_db = json.loads(json.dumps(retrieve_from_db))

        retrieved_messages = messages_from_dict(retrieve_from_db)
        retrieved_chat_history = ChatMessageHistory(messages=retrieved_messages)

        model = ChatOpenAI(model='gpt-3.5-turbo-1106')
        retrieved_memory = ConversationSummaryBufferMemory(llm=model, memory_key="chat_history", return_messages=True, chat_memory=retrieved_chat_history)
        return retrieved_memory
    except Exception as ex:
        logging.error(f"Exception occurred: {ex}")
        return None

      


@log_entry_exit
@build_router.get("/build/upload/{transaction_id}")
def upload_resume_status(transaction_id: str, api_key: APIKey = Depends(auth.get_api_key)):
    '''
     API to check upload status
    '''
    try:
        if transaction_id in job_object:
            job = job_object.get(transaction_id)
        else:
            job = azur_blob_storage.download_file_from_blob(f"{transaction_id}.pkl")
            job_object[transaction_id] = job
        if job:
            if job.status == StatusEnum.SUCCESS:
                conversation_manager.conversation[f'{transaction_id}'] = initiate_chat(job)

            return job
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))


def save_chat( transaction_id, user_id, filename, chat_status, conversation):

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

    knowledge.store_in_db( transaction_id, user_id, filename, chat_status, json.dumps(chat_history_formatted) )  

    

@log_entry_exit
@build_router.post("/build/chat/")
# def chat(transaction_id: str , message: Message):
async def chat(background_tasks: BackgroundTasks, transaction_id: str , message: Message):
    chat_memory = retrieve_chat_memory_from_storage(transaction_id) 
    if chat_memory is None and transaction_id not in conversation_manager.conversation:
        raise HTTPException(status_code=400, detail="Conversation not initialized")

    if transaction_id is not None:
        
        # job = job_object.get(transaction_id)
        if transaction_id not in job_object:
            job = azur_blob_storage.download_file_from_blob(f"{transaction_id}.pkl")
            job_object[transaction_id] = job
        else:
            job = job_object.get(transaction_id)
        if transaction_id not in conversation_manager.conversation:
            logging.info("Downloading conversation memory from cloud storage...")
            conversation_manager.conversation[f'{transaction_id}'] = initiate_chat(job, memory_chat=chat_memory)
        
        archive_conversation = conversation_manager.conversation[f'{transaction_id}']
        
        if 'end chat' in message.content.lower():
            chat_response = ""
        if 'retart the chat' in message.content.lower() or 'restart the chat' in message.content.lower():
            conversation_manager.conversation[f'{transaction_id}'] = initiate_chat(job)
            chat_response = conversation_manager.conversation[f'{transaction_id}']({"content": 'Hi'})['text']
        else:
            chat_response = archive_conversation({"content": message.content})['text']

        if 'bye' in chat_response.lower() or 'end chat' in message.content.lower():
            status = 'Completed'
            chat_response += ' Please click on X to end chat'
            chat_history = dict(archive_conversation.memory.chat_memory)['messages']
            background_tasks.add_task(update_pg, chat_history, job)
            background_tasks.add_task(save_chat, transaction_id , job.user_id , job.filename, status , archive_conversation)
            store_chat_memory_in_storage(conversation_manager.conversation[f'{transaction_id}'], transaction_id)
        else:
            status = 'Completed'

        print("conversaation manager",conversation_manager)
        return chat_response

    else:
        return "Please upload resume to start the chat"



    
@log_entry_exit
@build_router.get("/build/chat/archive/v1")
def query_knowledge_graph(user_id : str, api_key: APIKey = Depends(auth.get_api_key)):
    '''
    Fetch All Chat History for a User
    '''
    try:
        res = knowledge.retrieve_chat_v1(user_id)  
        return res
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
    

@log_entry_exit
@build_router.get("/build/summary")
def build_summary(user_id : str, api_key: APIKey = Depends(auth.get_api_key)):
    '''
    Fetch All Chat History for a Userr
    '''
    try:
        res = knowledge.retrieve_summary(user_id)  
        return res
    
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
    
@log_entry_exit
@build_router.get("/build/discipline")
def query_knowledge_graph(user_id : str, api_key: APIKey = Depends(auth.get_api_key)):
    '''
    Fetch All Details of Discipline and All Levels under it
    '''
    try:
        res = knowledge.fetch_discipline_with_validation_status(user_id)  
        return res
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
    
def docs_upload(file_data, file_name, job):
    '''
    Method takes uncleansed Inputs as input and returns cleansed Input as output
    '''
    try:
        extension = file_name.split('.')[-1]

        user_id = job_object[job.job_uuid.__str__()].user_id
        user_name = job_object[job.job_uuid.__str__()].name

        if extension == 'pdf':
            extracted_text = extract_text_utils.extract_text_from_pdf(file_data)
        elif extension == 'docx' or extension == 'doc':
            extracted_text = extract_text_utils.extract_text_from_docx(file_data)
        elif extension == 'txt':
            extracted_text = extract_text_utils.extract_text_from_txt(file_data)
        elif extension in ['jpg', 'jpeg', 'png']:
            extracted_text = extract_text_utils.extract_text_from_image(file_data)
        else:
            raise Exception(ExceptionMessageEnum.INVALID_FILE_FORMAT.value.format(extension))

        # Update job result and status
        job_object[job.job_uuid.__str__()].skills = extracted_text
        job_object[job.job_uuid.__str__()].status = StatusEnum.IN_PROGRESS
        print("Document Uploaded Successfully")

        # Get skills from the uploaded document using LLM call
        generated_json = extract_text_utils.get_doc_details_llm_call(extracted_text)

        name = generated_json.get('Name', '')
        document_type = generated_json.get('Document Type', '')
        project_info = generated_json.get('Project Information', [])
        certicate_info = generated_json.get('Certification Information', [])
        skills = generated_json.get('Skills', [])
        languages = generated_json.get('Languages Known', [])
        achievements = generated_json.get('Awards & Achievements', [])
        education = generated_json.get('Education', [])
        contact_info = generated_json.get('Contact Information', [])

        # Update the job object -> projects, certificates, achievements
        job_object[job.job_uuid.__str__()].projects = project_info
        job_object[job.job_uuid.__str__()].certificates = certicate_info
        job_object[job.job_uuid.__str__()].achievements = achievements
        job_object[job.job_uuid.__str__()].education = education
        job_object[job.job_uuid.__str__()].contact_info = contact_info
        job_object[job.job_uuid.__str__()].languages = languages
        job_object[job.job_uuid.__str__()].skills = skills
        job_object[job.job_uuid.__str__()].name = name
        job_object[job.job_uuid.__str__()].document_type = document_type

        print("Skills Extracted Successfully")

        # Update the personal knowledge graph with the extracted skills
        enrichment.create_personal_graph(skills, user_name, user_id, '', '', '', '')
        knowledge.set_similarity(user_id)

        job_object[job.job_uuid.__str__()].status = StatusEnum.SUCCESS
    except Exception as e:
        logging.error(ExceptionMessageEnum.DATA_CLEANSING_ERROR.value.format(e))
        job_object[job.job_uuid.__str__()].skills = ExceptionMessageEnum.DATA_CLEANSING_ERROR.value.format(e)
        job_object[job.job_uuid.__str__()].status = StatusEnum.ERROR


@log_entry_exit
@build_router.post("/chat/upload", response_model=Status, status_code=HTTPStatus.ACCEPTED)
def upload_docs(background_tasks: BackgroundTasks, user_id: str, doc: UploadFile = File(...), api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Upload documents from chat to update personal knowledge graph
    '''
    try:
        # Create a new job and add it to the job_object
        job = SkillMapper()
        job_uuid = job.job_uuid.__str__()
        job_object[job_uuid] = job
        job_object[job_uuid].user_id = user_id
        job_object[job_uuid].filename = doc.filename

        # Add a background task to run data cleansing asynchronously
        background_tasks.add_task(docs_upload, doc.file.read(), doc.filename, job)
        return Status(transaction_id=job_uuid, status=job.status)
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))


@log_entry_exit
@build_router.get("/chat/upload/{transaction_id}")
def upload_docs_status(transaction_id: str, api_key: APIKey = Depends(auth.get_api_key)):
    '''
     API to check upload status
    '''
    try:
        job = job_object.get(transaction_id)
        if job:
            return job
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))



@log_entry_exit
@build_router.post("/chat/upload_audio")
def upload_audio(user_id: str, audio_file: UploadFile = File(...), api_key: APIKey = Depends(auth.get_api_key)):
    '''
    API to Upload audio file from chat to update personal knowledge graph
    '''
    try:
        # allow only audio files
        text = extract_text_utils.extract_text_from_audio(audio_file=audio_file.file.read())
        return text
    except Exception as e:
        logging.error(ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
        raise HTTPException(
            status_code=500, detail=ExceptionMessageEnum.ERROR_RESPONSE.value.format(e))
    

