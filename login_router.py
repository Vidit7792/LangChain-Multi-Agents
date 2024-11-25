from fastapi import APIRouter
from fastapi import Depends, HTTPException
from utils.model_classes import User, LoginCredentials, UserProfile
from fastapi.security.api_key import APIKey
import authentication.auth as auth
from dotenv import load_dotenv
from utils.config import log_entry_exit
import logging

from integration import neo4j_integration
from utils import neo_utils

from pydantic import EmailStr
from uuid import uuid4
import time
load_dotenv()

router = APIRouter()

def get_user_details(userid: str):
    query = f"MATCH (u:UserAuth {{userid: '{userid}'}}) RETURN u.email AS email, u.first_name AS first_name, u.last_name AS last_name, u.mobile_number AS mobile, u.linkedin as linkedin, u.github as github, u.kaggle as kaggle, u.behance as behance, u.other_link1 as other_link1, u.other_link2 as other_link2 "
    result = neo4j_integration.get_neo4j_response(query)
    
    record = result[0]
    if record:
        return {
            "email": record["email"],
            "first_name": record["first_name"],
            "last_name": record["last_name"],
            "mobile": record["mobile"],
            "linkedin": record["linkedin"],
            "github": record["github"],
            "behance": record["behance"],
            "kaggle": record["kaggle"],
            "other_link1": record["other_link1"],
            "other_link2": record["other_link2"]
        }
    else:
        raise HTTPException(status_code=404, detail="User not found")

@router.post("/user/add")
def add_user(user: User, api_key: APIKey = Depends(auth.get_api_key)):
    try:
        query_check_duplicate = f"""
        MATCH (u:UserAuth)
        WHERE u.email = '{user.email}' OR u.mobile_number = '{user.mobile_number}'
        RETURN count(u) AS count
        """
        result = neo4j_integration.get_neo4j_response(query_check_duplicate)
        count = result[0]["count"]
        if count > 0:
            return HTTPException(status_code=400, detail="User with the same email or mobile number already exists")

        query_create_user = """
        CREATE (u:UserAuth {{
            userid: '{userid}',
            email: '{email}',
            password: '{password}',
            first_name: '{first_name}',
            last_name: '{last_name}',
            mobile_number: '{mobile_number}',
            is_student: '{is_student}'
        }})
        """
        query_create_user = query_create_user.format(userid=str(uuid4()), email=user.email, password=user.password,
                     first_name=user.first_name, last_name=user.last_name, mobile_number=user.mobile_number, is_student=user.is_student)
        neo_utils.execute_queries([query_create_user])
    except Exception as e:
        return e
    return {"message": "User added successfully"}

@router.post("/user/login")
def login(credentials: LoginCredentials, api_key: APIKey = Depends(auth.get_api_key)):
    query = f"MATCH (u:UserAuth {{email: '{credentials.email}', password: '{credentials.password}'}}) RETURN u.userid AS userid"
    result = neo4j_integration.get_neo4j_response(query)

    if result:
        return {"userid": result[0]["userid"]}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@router.put("/user/update-profile/{userid}")
def update_profile(userid: str, new_profile: UserProfile, api_key: APIKey = Depends(auth.get_api_key)):
    query = """
    MATCH (u:UserAuth {{userid: '{userid}'}})
    SET u.first_name = '{first_name}', u.last_name = '{last_name}', u.mobile_number = '{mobile_number}', u.linkedin = '{linkedin}', u.github = '{github}', u.kaggle = '{kaggle}', u.behance = '{behance}', u.other_link1 = '{other_link1}', u.other_link2 = '{other_link2}' 
    """
    query = query.format(
        userid=userid,
        first_name=new_profile.first_name,
        last_name=new_profile.last_name,
        mobile_number=new_profile.mobile_number,
        linkedin=new_profile.linkedin,
        github=new_profile.github,
        kaggle=new_profile.kaggle,
        behance=new_profile.behance,
        other_link1=new_profile.other_link1,
        other_link2=new_profile.other_link2
    )
    result = neo_utils.execute_queries([query])
    if result:
        return get_user_details(userid)
    else:
        raise HTTPException(status_code=404, detail="User not found")

@router.get("/user/{userid}")
def get_user(userid: str, api_key: APIKey = Depends(auth.get_api_key)):
    return get_user_details(userid)

import hashlib
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def generate_reset_token(email):
    timestamp = str(int(time.time()))
    token = hashlib.sha256(f"{email}{timestamp}".encode()).hexdigest()
    expiration_time = int(time.time()) + 3600  # 1 hour expiration
    return token, expiration_time

def store_reset_token(email, token, expiration_time):
    query = f"""
    MATCH (u:UserAuth {{email: '{email}'}})
    SET u.reset_token = '{token}', u.reset_token_expiration = '{expiration_time}'
    """
    neo_utils.execute_queries([query])

@router.post("/user/forgot-password")
async def forgot_password(email: EmailStr, api_key: APIKey = Depends(auth.get_api_key)):
    query = f"MATCH (u:UserAuth {{email: '{email}'}}) RETURN u"
    result = neo4j_integration.get_neo4j_response(query)

    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    token, expiration_time = generate_reset_token(email)
    store_reset_token(email, token, expiration_time)

    reset_link = f"https://idea-tribe.web.app/user/reset-password?token={token}"
    send_reset_email(email, reset_link)

    return {"message": "Password reset instructions sent to your email"}

@router.put("/user/reset-password")
def reset_password(token: str, new_password: str):
    query = f"MATCH (u:UserAuth {{reset_token: '{token}'}}) RETURN u as User"
    result = neo4j_integration.get_neo4j_response(query)

    if not result:
        raise HTTPException(status_code=400, detail="Invalid token")

    user = result[0]['User']

    if int(user['reset_token_expiration']) < int(time.time()):
        raise HTTPException(status_code=400, detail="Token expired")

    query = f"MATCH (u:UserAuth {{reset_token: '{token}'}}) SET u.password = '{new_password}', u.reset_token = NULL, u.reset_token_expiration = NULL"
    neo_utils.execute_queries([query])
    return {"message": "Password reset successfully"}

def send_reset_email(email, reset_link):
    try:
        smtp_server = 'smtp.gmail.com'
        smtp_port = 587
        smtp_user = 'ideatribepilot@gmail.com'
        smtp_password = 'mvow njvu oswd ricy'

        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = email
        msg['Subject'] = 'Password Reset Request'
        body = f"Please click the link below to reset your password:\n\n{reset_link}"
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        text = msg.as_string()
        server.sendmail(smtp_user, email, text)
        server.quit()

        print(f"Password reset email sent to {email}")
    except Exception as e:
        print(f"Failed to send email: {e}")
        raise HTTPException(status_code=500, detail="Failed to send email")

@router.put("/user/change-password")
def change_password(userid: str, old_password: str, new_password: str, api_key: APIKey = Depends(auth.get_api_key)):
    query = f"MATCH (u:UserAuth {{userid: '{userid}', password: '{old_password}'}}) RETURN u"
    result = neo4j_integration.get_neo4j_response(query)

    if not result:
        raise HTTPException(status_code=401, detail="Old password is incorrect")

    query = f"MATCH (u:UserAuth {{userid: '{userid}'}}) SET u.password = '{new_password}'"
    neo_utils.execute_queries([query])
    return {"message": "Password changed successfully"}