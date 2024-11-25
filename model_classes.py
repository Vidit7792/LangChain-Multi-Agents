from enum import Enum
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from typing import Dict, List, Optional
from pydantic import EmailStr


class ValidateSkills(BaseModel):
    megaskills: Dict[str, List[str]]

class Message(BaseModel):
    content: str

class Input(BaseModel):
    text: str

class DictResponse(BaseModel):
    response: dict

class ListResponse(BaseModel):
    response: list


class StatusEnum(Enum):
    IN_PROGRESS = "In progress"
    SUCCESS = "Success"
    FAILURE = "Failure"
    NOT_FOUND = "Not found"
    ERROR = "Error"

class Status(BaseModel):
    transaction_id: str
    status: StatusEnum

class ResultStatus(BaseModel):
    transaction_id: str
    status: StatusEnum
    result : str


class Job(BaseModel):
    job_uuid: UUID = Field(default_factory=uuid4)
    status: StatusEnum = StatusEnum.IN_PROGRESS
    result: str = "No Data"

class SkillMapper(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    seniority: Optional[str] = None
    salary: Optional[str] = None
    experience: Optional[str] = None
    projects: Dict = {}
    document_type: Optional[str] = None
    education: List = []
    certificates: List = []
    achievements: List = []
    contact_info: Dict = {}
    languages: List = []
    skills: List = []
    other_skills: Dict = {}
    mapped_skills: Dict = {}
    system_prompt: Optional[str] = None
    user_id: Optional[UUID] = None
    filename: Optional[str] = None
    job_uuid: UUID = Field(default_factory=uuid4)
    status: StatusEnum = StatusEnum.IN_PROGRESS


class ExceptionMessageEnum(Enum):
    INPUT_LIMIT_REACHED = "Cannot process more than 35000 thousand tokens at one go! Tokens:{token}"
    LLM_CONNECTION_EXCEPTION = "Exception occurred while connecting to LLM Platform{}"
    LLM_GENERATE_TEXT_EXCEPTION = "Exception occurred while generating text from LLM Platform{}"
    ERROR_RESPONSE = "Exception Occurred while generating API Response:{}"
    VALIDATION_ERROR = "Validation Error Occurred:{}"
    DATA_CLEANSING_ERROR = "Error Occurred While Invoking Cleansing Data API:{}"
    USER_NOT_FOUND = "User not found"
    TRANSACTION_ID_NOT_FOUND = "Transaction ID not found"
    GRAPH_ENRICHMENT_ERROR = "Error occurred during graph enrichment"
    UPLOAD_ERROR = "Error occurred during file upload"
    CHAT_INITIATION_ERROR = "Error occurred during chat initiation"
    CHAT_ARCHIVE_ERROR = "Error occurred while fetching chat archive"
    JOB_CATEGORY_FETCH_ERROR = "Error occurred while fetching job categories"
    JOB_CATEGORY_DELETE_ERROR = "Error occurred while deleting job categories"
    PERSONAL_KNOWLEDGE_GRAPH_DELETE_ERROR = "Error occurred while deleting personal knowledge graph"
    SKILL_VALIDATION_ERROR = "Error occurred during skill validation"
    COURSE_FETCH_ERROR = "Error occurred while fetching courses"
    LEARNING_PATH_UPDATE_ERROR = "Error occurred while updating learning path"
    STATUS_FETCH_ERROR = "Error occurred while fetching status"
    TOP_SKILLS_FETCH_ERROR = "Error occurred while fetching top skills"
    TIMELINE_FETCH_ERROR = "Error occurred while fetching timeline"
    SUMMARY_UPDATE_ERROR = "Error occurred while updating summary"
    INTRO_UPDATE_ERROR = "Error occurred while updating introduction"
    USER_PROFILE_UPDATE_ERROR = "Error occurred while updating user profile"
    USER_LOGIN_ERROR = "Error occurred during user login"
    USER_ADD_ERROR = "Error occurred while adding user"
    PASSWORD_RESET_ERROR = "Error occurred while resetting password"
    INDUSTRY_CLASSIFICATION_ERROR = "Error occurred while classifying industry"
    FRAMEWORK_GENERATION_ERROR = "Error occurred while generating framework"
    FILE_EXTRACTION_ERROR = "Error occurred while extracting text from file"
    INVALID_FILE_FORMAT = "Invalid File Format:{}"

class CustomException(Exception):
    def __init__(self, error_code, message="Default custom exception message"):
        self.error_code = error_code
        self.message = message
        super().__init__(self.message)
    

class User(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    mobile_number: str
    is_student: bool


class LoginCredentials(BaseModel):
    email: EmailStr
    password: str

class UserProfile(BaseModel):
    first_name: str
    last_name: str
    mobile_number: str
    linkedin: str
    github: str
    kaggle: str
    behance: str
    other_link1: str
    other_link2: str
    