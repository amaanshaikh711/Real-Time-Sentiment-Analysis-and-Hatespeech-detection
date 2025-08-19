# utils/cleaning.py
import re
import csv
import string
import pandas as pd
from nltk.corpus import stopwords
import nltk

nltk.download('stopwords', quiet=True)
STOPWORDS = set(stopwords.words('english'))

# -------------------------
# 1. Offensive Words Loader
# -------------------------
def load_offensive_words(filepath='model/offensive_words.txt'):
    """Load offensive words from text file."""
    offensive_words = set()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip().lower()
                if word:
                    offensive_words.add(word)
        print(f"[INFO] Loaded {len(offensive_words)} offensive words from {filepath}")
    except FileNotFoundError:
        print(f"[WARNING] Offensive words file not found: {filepath}")
    return offensive_words

OFFENSIVE_WORDS = load_offensive_words()

def count_offensive_words(text):
    """Count how many offensive words are in a given text."""
    words = re.findall(r'\b\w+\b', str(text).lower())
    count = sum(1 for w in words if w in OFFENSIVE_WORDS)
    return count

# -------------------------
# 2. Text Cleaning Function
# -------------------------
def clean_text(text):
    """Clean text by removing punctuation, numbers, stopwords, and extra spaces."""
    if not isinstance(text, str):
        text = str(text)
    text = text.lower()
    text = re.sub(r"http\S+|www\S+|https\S+", '', text)  # remove URLs
    text = re.sub(r'\d+', '', text)  # remove numbers
    text = text.translate(str.maketrans('', '', string.punctuation))  # remove punctuation
    words = [w for w in text.split() if w not in STOPWORDS]
    return " ".join(words)

# -------------------------
# 3. Load & Clean Sentiment Data
# -------------------------
def load_and_clean_sentiment_data(filepath='data/sentiment/test.csv'):
    """Load sentiment dataset and clean the text."""
    df = pd.read_csv(filepath)
    if 'text' not in df.columns or ('label' not in df.columns and 'sentiment' not in df.columns):
        raise ValueError("Sentiment dataset must have 'text' and 'label' or 'sentiment' column")

    # internally keep 'sentiment' as column for training
    if 'label' in df.columns:
        df = df.rename(columns={'label': 'sentiment'})
    
    df['clean_text'] = df['text'].apply(clean_text)
    return df

# -------------------------
# 4. Load & Clean Hate Speech Data
# -------------------------
def load_and_clean_hate_data(filepath='data/hated speech/labeled_data.csv'):
    """Load hate speech dataset and clean the text."""
    df = pd.read_csv(filepath)
    if 'tweet' not in df.columns or 'class' not in df.columns:
        raise ValueError("Hate speech dataset must have 'tweet' and 'class' columns")
    df['clean_text'] = df['tweet'].apply(clean_text)
    df['offensive_count'] = df['tweet'].apply(count_offensive_words)
    return df

# -------------------------
# 5. Vulgarity Level Calculator
# -------------------------
def calculate_vulgarity_level(offensive_counts, total_words_in_text=100):
    """Calculate vulgarity level percentage and label."""
    total_offensive = offensive_counts.get('total', 0) if isinstance(offensive_counts, dict) else offensive_counts
    total_words = total_words_in_text if total_words_in_text > 0 else 100
    percentage = (total_offensive / total_words) * 100

    if percentage <= 30:
        label = "Mild"
    elif percentage <= 70:
        label = "Moderate"
    else:
        label = "Severe"
    
    return round(percentage, 2), label
