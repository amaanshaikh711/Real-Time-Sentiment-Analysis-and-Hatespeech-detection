# model/predict.py

import os
import re
import pickle
import nltk
from nltk.corpus import stopwords

nltk.download('stopwords')
stop_words = set(stopwords.words('english'))

# === Clean Text Function ===
def clean_text(text):
    text = text.lower()
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)  # Remove URLs
    text = re.sub(r'\@w+|\#', '', text)  # Remove mentions/hashtags
    text = re.sub(r'[^A-Za-z\s]', '', text)  # Keep only letters and spaces
    text = ' '.join([word for word in text.split() if word not in stop_words])
    return text

# === Load models (they include vectorizers) ===
with open("model/sentiment_model.pkl", "rb") as f:
    sentiment_vectorizer, sentiment_model = pickle.load(f)

with open("model/hate_model.pkl", "rb") as f:
    hate_vectorizer, hate_model = pickle.load(f)

# === Prediction Function ===
def predict(text, mode='sentiment'):
    cleaned = clean_text(text)
    
    if mode == 'sentiment':
        X = sentiment_vectorizer.transform([cleaned])
        return sentiment_model.predict(X)[0]
    elif mode == 'hate':
        X = hate_vectorizer.transform([cleaned])
        return hate_model.predict(X)[0]
    else:
        raise ValueError("Invalid mode. Use 'sentiment' or 'hate'")
