import sys
import time

sys.path.append('/Users/hemantparashar/Slivers/slivers-demo_api/slivers')

from sentence_transformers import SentenceTransformer, util
import json
import torch
from integration import neo4j_integration
from openai import OpenAI

import os
from dotenv import load_dotenv
load_dotenv()


EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL",None)
OPENAI_KEY =  os.getenv("OPENAI_API_KEY",None)
NEO4J_URL = os.getenv("NEO4J_URI", None)
NEO4J_USER = os.getenv("NEO4J_USERNAME", None)
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", None)


client = OpenAI(api_key=OPENAI_KEY)
def get_embedding(text, model="text-embedding-3-large"):
   text = text.replace("\n", " ")
   return client.embeddings.create(input = [text], model=model).data[0].embedding


# kg_data = neo4j_integration.get_neo4j_response('match (h:Task) where h.name is NOT NULL return  h.name as Task')
data = neo4j_integration.get_neo4j_response('match (m:Industry)-->(n:Discipline)-->(k:Megaskill)-->(j:Microskill)-->(h:Task) where m.name is not NULL and not m:Personal return m.name as Industry, n.name as Discipline, k.name as Megaskill,k.id as Megaskill_ID, j.name as Microskill ,j.id as Microskill_ID , h.name as Task,h.level as Level, h.description as TaskDescription')

sentences = data

print(sentences)

# Compute and store embeddings
embeddings = {}
decoded_sentences = []  # List to store the decoded sentences

for idx, sent in enumerate(sentences):
    print(idx,sent)
    # input_text = json.dumps(sent['Task'])
    input_text = json.dumps(sent)
    # embedding = model.encode(input_text, convert_to_tensor=True)
    embedding = get_embedding(input_text,EMBEDDING_MODEL)
    # embeddings[idx] = embedding.tolist()
    embeddings[idx] = embedding
    decoded_sentences.append(input_text)  # Store the decoded sentence

# Save embeddings and decoded sentences to a file
with open('embeddings.json', 'w') as f:
    json.dump(embeddings, f)

with open('decoded_sentences.json', 'w') as f:
    json.dump(decoded_sentences, f)

# Load embeddings and decoded sentences from files
with open('embeddings.json', 'r') as f:
    loaded_embeddings = json.load(f)

with open('decoded_sentences.json', 'r') as f:
    loaded_decoded_sentences = json.load(f)

# Convert loaded embeddings back to torch tensors
loaded_embeddings = {int(idx): torch.tensor(embedding) for idx, embedding in loaded_embeddings.items()}

# Example: calculate cosine similarity for the first sentence
embedding_1 = loaded_embeddings[0]
# embedding_2 = model.encode("Python", convert_to_tensor=True)
embedding_2 = get_embedding('Python',EMBEDDING_MODEL)
similarity = util.pytorch_cos_sim(embedding_1, embedding_2)
print(similarity)

# Example: retrieve the decoding of the first sentence
decoded_sentence_1 = loaded_decoded_sentences[0]
print(decoded_sentence_1)
