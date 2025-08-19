# model/train_models.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from utils.cleaning import load_and_clean_sentiment_data, load_and_clean_hate_data

print("Starting training script...")

# === Load and prepare datasets ===
sentiment_df = load_and_clean_sentiment_data('../data/sentiment/test.csv')
hate_df = load_and_clean_hate_data('../data/hated speech/labeled_data.csv')

# === Vectorizers (separate for both models) ===
vectorizer_s = TfidfVectorizer(max_features=5000)
vectorizer_h = TfidfVectorizer(max_features=5000)

# === Sentiment Model ===
X_sentiment = vectorizer_s.fit_transform(sentiment_df['clean_text'])
y_sentiment = sentiment_df['sentiment']

X_train_s, X_test_s, y_train_s, y_test_s = train_test_split(X_sentiment, y_sentiment, test_size=0.2, random_state=42)

model_s = LogisticRegression()
model_s.fit(X_train_s, y_train_s)

print("✅ Sentiment model trained.")

# === Hate Speech Model ===
X_hate = vectorizer_h.fit_transform(hate_df['clean_text'])
y_hate = hate_df['class']  # Assuming class: 0 = hate speech, 1 = offensive, 2 = neither

X_train_h, X_test_h, y_train_h, y_test_h = train_test_split(X_hate, y_hate, test_size=0.2, random_state=42)

model_h = LogisticRegression()
model_h.fit(X_train_h, y_train_h)

print("✅ Hate speech model trained.")

# === Ensure model directory exists ===
model_dir = 'model'
if not os.path.exists(model_dir):
    os.makedirs(model_dir)

# === Save models ===
with open(os.path.join(model_dir, 'sentiment_model.pkl'), 'wb') as f:
    pickle.dump((vectorizer_s, model_s), f)

with open(os.path.join(model_dir, 'hate_model.pkl'), 'wb') as f:
    pickle.dump((vectorizer_h, model_h), f)

print("✅ Models saved to 'model/' folder.")
print("🎉 Training script completed successfully.")
