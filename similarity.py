from sentence_transformers import SentenceTransformer, util
import json
import torch
import os
from pathlib import Path
from utils.config import log_entry_exit
import time
import pandas as pd
from integration import openai_integration
import time

EMBEDDING_MODEL = "text-embedding-3-large"

@log_entry_exit 
def encode_sentence(sentence, model):
    return model.encode(sentence, convert_to_tensor=True)

@log_entry_exit
def load_embeddings(file_path):
    with open(file_path, 'r') as f:
        loaded_embeddings = json.load(f)
    return {int(idx): torch.tensor(embedding) for idx, embedding in loaded_embeddings.items()}

@log_entry_exit
def load_decoded_sentences(file_path):
    with open(file_path, 'r') as f:
        loaded_decoded_sentences = json.load(f)
    return loaded_decoded_sentences

@log_entry_exit
def skill_mapper(skills):

    parent_dir = Path(os.getcwd()) / 'slivers' / 'data'
    embeddings_path = parent_dir / "embeddings.json"
    decoded_sentences_path = parent_dir / 'decoded_sentences.json'

    loaded_embeddings = load_embeddings(embeddings_path)
    loaded_decoded_sentences = load_decoded_sentences(decoded_sentences_path)

    matching_skills = []
    response = {}

    for user_input in skills:
        if user_input:
            # Encode user input
            user_input = json.dumps(user_input)
            user_embedding = openai_integration.get_embedding(user_input,EMBEDDING_MODEL)

            # Find the most similar sentence
            most_similar_idx = max(loaded_embeddings.keys(), key=lambda idx: util.pytorch_cos_sim(user_embedding, loaded_embeddings[idx]))
            
            # Display the most similar sentence
            res = loaded_decoded_sentences[most_similar_idx]
            matching_skills.append(res)

            response[user_input] = res


    # Assuming skills, loaded_embeddings, and loaded_decoded_sentences are already defined
    # matching_skills = []
    # response = {}

    # for user_input in skills:
    #     if user_input:
    #         # Encode user input
    #         user_input_encoded = json.dumps(user_input)
    #         user_embedding = openai_integration.get_embedding(user_input_encoded, EMBEDDING_MODEL)

    #         # Calculate similarities
    #         similarities = [(idx, util.pytorch_cos_sim(user_embedding, embedding)) for idx, embedding in loaded_embeddings.items()]

    #         # Sort by similarity score in descending order and fetch the top 5
    #         top_5_similar = sorted(similarities, key=lambda x: x[1], reverse=True)[:5]

    #         # Extract the indices for the top 5
    #         top_5_indices = [idx for idx, score in top_5_similar]

    #         # Get the most similar sentences
    #         top_5_sentences = [loaded_decoded_sentences[idx] for idx in top_5_indices]

    #         # Store the results
    #         matching_skills.extend(top_5_sentences)
    #         response[user_input] = top_5_sentences

    #         # Print or log the results (optional)
    #         print(f"User input: {user_input}")
    #         for sentence in top_5_sentences:
    #             print(f" - {sentence}")


    with open("mappings.json", 'w') as json_file:
        json.dump(response, json_file, indent=2)

    return matching_skills

@log_entry_exit
def task_mapper(skills, similarity_threshold=0.2):
    try:
        parent_dir = Path(os.getcwd()) / 'slivers' / 'data'
        embeddings_path = parent_dir / "task_embeddings.json"
        decoded_sentences_path = parent_dir / 'task_decoded_sentences.json'

        loaded_embeddings = load_embeddings(embeddings_path)
        loaded_decoded_sentences = load_decoded_sentences(decoded_sentences_path)

        matching_skills = []
        new_skills = []
        response = []

        for user_input in skills:
            if user_input:
                # Encode user input
                user_input = json.dumps(user_input)
                # user_embedding = encode_sentence(user_input, model)
                user_embedding = openai_integration.get_embedding(user_input,EMBEDDING_MODEL)

                # Find sentences with similarity above the threshold
                print(1)
                similar_sentences = [
                    (idx, util.pytorch_cos_sim(user_embedding, loaded_embeddings[idx]))
                    for idx in loaded_embeddings.keys()
                    if util.pytorch_cos_sim(user_embedding, loaded_embeddings[idx]) >= similarity_threshold
                ]
                print(2)
                print(similar_sentences)
                if similar_sentences:
                    # Sort sentences by similarity in descending order
                    similar_sentences.sort(key=lambda x: x[1], reverse=True)
                    print(3)
                    # Display the most similar sentence above the threshold
                    for most_similar_idx, similarity_score in similar_sentences[0:15]:
                        if similarity_score >= similarity_threshold:
                            res = loaded_decoded_sentences[most_similar_idx]
                            matching_skills.append(res)
                            print(matching_skills , user_input)
                            print(4)
                            temp_dict = {}
                            temp_dict['similarity score'] = similarity_score
                            temp_dict['fetched task'] = json.loads(user_input)['task']
                            temp_dict['proficiency'] = json.loads(user_input)['proficiency_level']
                            temp_dict['mapped task'] = res
                            response.append(temp_dict)
                            print(5)
                        else:
                            new_skills.append(json.loads(user_input)['task'])
                            print(6)
                else:
                    print(7)
                    print(user_input)
                    new_skills.append(json.loads(user_input)['task'])
                    print(new_skills)
    

        df = pd.DataFrame(response)
        df.to_csv("task_mapper.csv")
        print(8)


        print(f"matched:{len(matching_skills)} and new tasks:{len(new_skills)}")
        
        return { "matched_path" : matching_skills , "unmatched_tasks": new_skills}
    except Exception as e:
        print(e)
