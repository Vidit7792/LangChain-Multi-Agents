from integration import neo4j_integration
from fastapi import HTTPException

def get_user_details(userid: str):
   
    query = f"MATCH (u:UserAuth {{userid: '{userid}'}}) RETURN u.email AS email, u.first_name AS first_name, u.last_name AS last_name, u.mobile_number AS mobile, u.linkedin as linkedin, u.github as github, u.kaggle as kaggle, u.behance as behance, u.other_link1 as other_link1, u.other_link2 as other_link2 "
    result = neo4j_integration.get_neo4j_response(query)
    
    # Retrieve the first record from the result
    record = result[0]
    if record:
        return {
            "email": record["email"],
            "first_name": record["first_name"],
            "last_name": record["last_name"],
            "mobile": record["mobile"],
            "linkedin": record["linkedin"],
            "github": record["github"],
            "behance":record["behance"],
            "kaggle":record["kaggle"],
            "other_link1":record["other_link1"],
            "other_link2":record["other_link2"]
        }
    else:
        raise HTTPException(status_code=404, detail="User not found")
