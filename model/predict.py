# model/predict.py  (Hybrid ML + Keyword) - replace your existing predict.py with this

import os
import re
import pickle
import logging

import nltk
from nltk.corpus import stopwords

# ensure stopwords (quiet)
nltk.download('stopwords', quiet=True)
stop_words = set(stopwords.words('english'))

# -----------------------
# Offensive words (try to reuse your utils.cleaning)
# -----------------------
try:
    from utils.cleaning import OFFENSIVE_WORDS as GLOBAL_OFFENSIVE
    OFFENSIVE_SET = set(w.lower() for w in GLOBAL_OFFENSIVE) if GLOBAL_OFFENSIVE else set()
except Exception:
    OFFENSIVE_SET = set()

# === Load from offensive_words.txt in model folder ===
OFFENSIVE_TXT_PATH = os.path.join(os.path.dirname(__file__), "offensive_words.txt")
if os.path.exists(OFFENSIVE_TXT_PATH):
    try:
        with open(OFFENSIVE_TXT_PATH, "r", encoding="utf-8") as f:
            file_words = [w.strip().lower() for w in f if w.strip()]
        OFFENSIVE_SET.update(file_words)
    except Exception as e:
        logging.warning(f"Could not read offensive_words.txt: {e}")

# fallback list (only if set is still empty)
if not OFFENSIVE_SET:
    OFFENSIVE_SET = set([
        "stupid","idiot","dumb","moron","loser","trash","ugly","jerk","freak",
        "sucks","hate","kill","die","bastard","asshole","bitch","scum","trash","shut"
    ])

# -----------------------
# Cleaner (keeps behavior similar to your previous function but a bit more robust)
# -----------------------
def clean_text(text):
    if not text:
        return ""
    txt = str(text).replace('\n', ' ').replace('\r', ' ')
    txt = txt.lower()
    txt = re.sub(r'http\S+|www\S+|https\S+', '', txt, flags=re.MULTILINE)         # remove urls
    txt = re.sub(r'@\w+|\#\w+', '', txt)   # remove mentions/hashtags
    txt = re.sub(r'[^a-z0-9\s]', ' ', txt) # keep letters, digits and spaces
    toks = [w for w in txt.split() if w and w not in stop_words]
    return ' '.join(toks).strip()

# -----------------------
# Load models safely
# -----------------------
sentiment_vectorizer = None
sentiment_model = None
hate_vectorizer = None
hate_model = None

MODEL_DIR = "model"

def _safe_load(path):
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        logging.warning(f"Could not load {path}: {e}")
        return None

_s = _safe_load(os.path.join(MODEL_DIR, "sentiment_model.pkl"))
if _s:
    try:
        sentiment_vectorizer, sentiment_model = _s
    except Exception:
        sentiment_vectorizer = None
        sentiment_model = None

_h = _safe_load(os.path.join(MODEL_DIR, "hate_model.pkl"))
if _h:
    try:
        hate_vectorizer, hate_model = _h
    except Exception:
        hate_vectorizer = None
        hate_model = None

# -----------------------
# Helpers: mapping raw model outputs -> canonical labels
# -----------------------
def _map_sentiment_label(raw):
    if raw is None:
        return "Neutral"
    r = str(raw).strip().lower()
    if r in ("positive","pos","p","1","2","positive"):
        return "Positive"
    if r in ("negative","neg","n","-1"):
        return "Negative"
    if r in ("neutral","neu","0","none"):
        return "Neutral"
    if "pos" in r:
        return "Positive"
    if "neg" in r:
        return "Negative"
    if "neu" in r:
        return "Neutral"
    return "Neutral"

def _map_hate_label_from_classes(raw, classes=None, proba=None):
    if proba is not None:
        try:
            return "Hate Speech" if float(proba) >= 0.5 else "Safe Content"
        except Exception:
            pass

    if raw is None:
        return "Safe Content"

    try:
        raw_int = None
        try:
            raw_int = int(str(raw))
        except Exception:
            raw_int = None

        if classes:
            cls_list = [str(x).strip().lower() for x in classes]
            if all(re.match(r'^\d+$', c) for c in cls_list):
                if raw_int is not None:
                    if raw_int in (0,1):
                        return "Hate Speech"
                    else:
                        return "Safe Content"
            for c in cls_list:
                if 'hate' in c or 'offen' in c or 'abuse' in c:
                    if str(raw).strip().lower() == c:
                        return "Hate Speech"
    except Exception:
        pass

    r = str(raw).strip().lower()
    if r in ("hate","hate speech","offensive","abusive","1","true"):
        return "Hate Speech"
    if r in ("safe","clean","none","0","false","2"):
        return "Safe Content"
    if "hate" in r or "abuse" in r or "offen" in r:
        return "Hate Speech"
    return "Safe Content"

# -----------------------
# Keyword check (fast)
# -----------------------
def contains_offensive_word(text):
    if not text:
        return False
    toks = re.findall(r"[a-z0-9']+", text.lower())
    for t in toks:
        if t in OFFENSIVE_SET:
            return True
    return False

# -----------------------
# Lexicon fallback for sentiment
# -----------------------
FALLBACK_POS = set(["good","great","love","awesome","nice","best","amazing","happy","like","excellent","cool"])
FALLBACK_NEG = set(["bad","hate","terrible","awful","worst","stupid","idiot","dumb","sucks","angry","disgusting"])

def _infer_sentiment_lexicon(text):
    toks = re.findall(r"[a-z0-9']+", (text or "").lower())
    if not toks:
        return "Neutral"
    pos = sum(1 for t in toks if t in FALLBACK_POS)
    neg = sum(1 for t in toks if t in FALLBACK_NEG)
    if pos > neg:
        return "Positive"
    if neg > pos:
        return "Negative"
    return "Neutral"

# -----------------------
# Public predict()
# -----------------------
def predict(text, mode='sentiment'):
    cleaned = clean_text(text)

    if mode == 'sentiment':
        if sentiment_model is not None and sentiment_vectorizer is not None:
            try:
                X = sentiment_vectorizer.transform([cleaned])
                raw = sentiment_model.predict(X)[0]
                proba = None
                if hasattr(sentiment_model, "predict_proba"):
                    try:
                        pvals = sentiment_model.predict_proba(X)[0]
                        idx = int(pvals.argmax())
                        if hasattr(sentiment_model, "classes_"):
                            raw = sentiment_model.classes_[idx]
                        proba = float(pvals[idx])
                    except Exception:
                        proba = None
                label = _map_sentiment_label(raw)
                if proba is not None and proba < 0.55 and label == "Neutral":
                    return _infer_sentiment_lexicon(text)
                return label
            except Exception as e:
                logging.warning(f"Sentiment model error: {e}")
                return _infer_sentiment_lexicon(text)
        else:
            return _infer_sentiment_lexicon(text)

    elif mode == 'hate':
        if contains_offensive_word(text):
            return "Hate Speech"

        if hate_model is not None and hate_vectorizer is not None:
            try:
                Xh = hate_vectorizer.transform([cleaned])
                rawh = hate_model.predict(Xh)[0]
                proba_h = None
                if hasattr(hate_model, "predict_proba"):
                    try:
                        pvals = hate_model.predict_proba(Xh)[0]
                        idx = int(pvals.argmax())
                        if hasattr(hate_model, "classes_"):
                            rawh = hate_model.classes_[idx]
                        proba_h = float(pvals[idx])
                    except Exception:
                        proba_h = None
                classes = getattr(hate_model, "classes_", None)
                return _map_hate_label_from_classes(rawh, classes=classes, proba=proba_h)
            except Exception as e:
                logging.warning(f"Hate model error: {e}")
                return "Hate Speech" if contains_offensive_word(text) else "Safe Content"
        else:
            return "Hate Speech" if contains_offensive_word(text) else "Safe Content"
    else:
        raise ValueError("Invalid mode for predict(): use 'sentiment' or 'hate'")
