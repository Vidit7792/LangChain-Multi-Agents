import os
import subprocess
import numpy as np
import pandas as pd
import torch
from transformers import BertTokenizer
from scipy.special import softmax
from sklearn.preprocessing import LabelEncoder
import pprint
import io
from utils.config import log_entry_exit

@log_entry_exit
def download_and_load_bert_model(url):
    result = subprocess.run(['curl', '-s', url], capture_output=True, check=True)
    model = torch.load(io.BytesIO(result.stdout), map_location=torch.device('cpu'))
    return model

# Define the URL
model_url = 'https://csg1003200310f6dbaa.blob.core.windows.net/idea-tribe-blob/bert_model?sp=r&st=2024-10-23T04:19:55Z&se=2025-01-01T12:19:55Z&spr=https&sv=2022-11-02&sr=b&sig=iQSKazytYI7m2a6xmbaahKUBRlWRh2tYxGwNaBiTq9o%3D'

# Download and load the model
model = download_and_load_bert_model(model_url)

max_len = 512  # Define the maximum length for padding/truncation
# Load tokenizer and model
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased', do_lower_case=True)


# Label encoding
df = pd.read_csv("slivers/integration/high_quality_training_data.csv")
sents = df['Job Description'].values
labels = df['Category'].values

# Create a label encoder
label_encoder = LabelEncoder()

# Fit the encoder to your labels
label_encoder.fit(labels)

# Transform your labels into numerical representations
labels = label_encoder.transform(labels)
labels = torch.tensor(labels)

# Function to predict the label for a given sentence
@log_entry_exit
def predict_sentence(sentence, model, tokenizer, max_len, label_encoder):
    model.eval()  # Set the model to evaluation mode
    encoded_dict = tokenizer.encode_plus(
        sentence,
        add_special_tokens=True,  # Add '[CLS]' and '[SEP]'
        max_length=max_len,  # Pad & truncate all sentences.
        padding='max_length',
        return_attention_mask=True,  # Construct attn. masks.
        return_tensors='pt',  # Return pytorch tensors.
    )

    input_ids = encoded_dict['input_ids']
    attention_mask = encoded_dict['attention_mask']

    with torch.no_grad():
        output = model(input_ids, token_type_ids=None, attention_mask=attention_mask)
        logits = output.logits

    logits = logits.detach().cpu().numpy()

    # Apply softmax to get probabilities
    probabilities = softmax(logits, axis=1)[0]

    predicted_label_index = np.argmax(logits, axis=1)[0]
    predicted_label = label_encoder.inverse_transform([predicted_label_index])[0]

    # Get the confidence score
    confidence_score = probabilities[predicted_label_index]

    return predicted_label, confidence_score

@log_entry_exit
def group_sentences_by_class(industry, sentences):
    grouped_sentences = {}
    
    for sentence in sentences:
        predicted_label, confidence_score = predict_sentence(sentence, model, tokenizer, max_len, label_encoder)
        
        if predicted_label not in grouped_sentences:
            grouped_sentences[predicted_label] = []
        
        grouped_sentences[predicted_label].append(sentence.split(':')[0] + f" (Confidence: {confidence_score:.4f})")
        print(f"{sentence}: {predicted_label} (Confidence: {confidence_score:.4f})")
    
    result = []
    for discipline, texts in grouped_sentences.items():
        result.append({
            "industry": industry,
            "discipline": discipline,
            "text": texts
        })
    
    return result