
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
# from utils.config import log_entry_exit
import os


load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI", None)
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", None)
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", None)

# @log_entry_exit
def connect_to_neo4j():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))    

# @log_entry_exit
def run_query(tx,query):
    result = tx.run(query)
    return result.data()

# @log_entry_exit
def get_neo4j_response(query):
    db = connect_to_neo4j()
    with db.session() as session:
        response = session.read_transaction(run_query,query)
    return response



