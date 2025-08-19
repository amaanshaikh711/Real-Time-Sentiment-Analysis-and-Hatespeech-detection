# helpers/analysis.py — robust, app.py-compatible

from collections import Counter, defaultdict
from datetime import datetime
import re

# Try to reuse your global list if available; else use a safe fallback
try:
    from utils.cleaning import OFFENSIVE_WORDS as _GLOBAL_OFFENSIVE
except Exception:
    _GLOBAL_OFFENSIVE = set()

# Minimal fallbacks so analysis never crashes
FALLBACK_NEG = {
    "bad","sad","angry","hate","terrible","worst","awful","trash","stupid","idiot",
    "dumb","ugly","loser","moron","sucks","disgusting","pathetic","toxic","nonsense",
    "shut","kill","die","garbage","cringe","trash"
}
FALLBACK_POS = {
    "good","great","love","awesome","amazing","excellent","nice","cool","wow","brilliant",
    "best","super","fantastic","helpful","enjoy","like","beautiful","perfect","solid","clean"
}
FALLBACK_OFFENSIVE = {
    "stupid","idiot","dumb","moron","loser","trash","ugly","jerk","freak","shut up","sucks"
}

OFFENSIVE_SET = set(_GLOBAL_OFFENSIVE) if _GLOBAL_OFFENSIVE else FALLBACK_OFFENSIVE

_EXPECTED_SENTIMENTS = {"Positive","Neutral","Negative"}

def _safe_lower_words(text: str):
    return re.findall(r"[a-zA-Z']+", (text or "").lower())

def _infer_sentiment(text: str) -> str:
    """
    Very lightweight lexicon-based fallback if comment doesn't carry a sentiment.
    """
    toks = _safe_lower_words(text)
    if not toks:
        return "Neutral"
    pos = sum(1 for t in toks if t in FALLBACK_POS)
    neg = sum(1 for t in toks if t in FALLBACK_NEG)
    if neg - pos >= 1:
        return "Negative"
    if pos - neg >= 1:
        return "Positive"
    return "Neutral"

def _infer_hate(text: str) -> str:
    """
    Simple heuristic: if any offensive word appears → 'Hate Speech' else 'Safe Content'.
    (This is a placeholder until you plug your ML model here.)
    """
    toks = _safe_lower_words(text)
    if any(t in OFFENSIVE_SET for t in toks):
        return "Hate Speech"
    return "Safe Content"

def _normalize_sentiment(value, text):
    """
    Accepts many shapes; maps to Positive/Neutral/Negative with fallback inference.
    """
    label = (value or "").strip().title()
    if label in _EXPECTED_SENTIMENTS:
        return label
    # also accept synonyms
    if label in {"Pos", "Positive 🙂", "Positivo"}:
        return "Positive"
    if label in {"Neg", "Negative 🙁", "Negativo"}:
        return "Negative"
    if label in {"Neu", "Neutral 😐", "Neutro"}:
        return "Neutral"
    # fallback inference
    return _infer_sentiment(text)

def _normalize_hate(value, text):
    """
    Maps to {'Hate Speech','Safe Content'} with fallback inference.
    """
    v = (value or "").strip().lower()
    if v.startswith("hate"):
        return "Hate Speech"
    if v in {"safe","clean","none","not hate","no hate","ok"}:
        return "Safe Content"
    # fallback
    return _infer_hate(text)

def _parse_date_any(date_str: str) -> str:
    """
    Accepts common ISO/RFC3339 shapes and returns YYYY-MM-DD.
    Falls back to today's UTC date if parsing fails.
    """
    s = (date_str or "").strip()
    if not s:
        return datetime.utcnow().strftime("%Y-%m-%d")
    # Common YouTube format: 2025-08-12T14:32:05Z
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass
    # Try Python's fromisoformat on the date part
    try:
        base = s.replace("Z","").split("T")[0]
        dt = datetime.fromisoformat(base)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return datetime.utcnow().strftime("%Y-%m-%d")

# ------------------------------------------------------------------------------------
# 1) MAIN: analyze_comments_sentiment_hate
#     - INPUT: list of dicts from your fetch layer (may or may not include sentiment/hate)
#     - OUTPUT: normalized list (ONLY the list! matches your app.py usage)
# ------------------------------------------------------------------------------------
def analyze_comments_sentiment_hate(comments):
    """
    comments: [
      { 'text': str, 'username': str, 'date': 'YYYY-MM-DD or ISO', 'likes': int,
        'sentiment': optional, 'hate_speech': optional }, ...
    ]
    returns: analyzed_comments (list of normalized dicts)
    """
    analyzed = []
    for c in (comments or []):
        text = c.get("text", "") or ""
        username = c.get("username") or "Unknown"
        likes = c.get("likes")
        try:
            likes = int(likes) if likes is not None else 0
        except Exception:
            likes = 0

        # Normalize fields with robust fallbacks
        sentiment = _normalize_sentiment(c.get("sentiment"), text)
        hate = _normalize_hate(c.get("hate_speech"), text)
        date_out = _parse_date_any(c.get("date"))

        analyzed.append({
            "text": text,
            "username": username,
            "date": date_out,           # guaranteed YYYY-MM-DD
            "likes": likes,
            "sentiment": sentiment,     # Positive/Neutral/Negative
            "hate_speech": hate         # Hate Speech / Safe Content
        })
    return analyzed

# ------------------------------------------------------------------------------------
# 2) KPIs
# ------------------------------------------------------------------------------------
def calculate_kpis(analyzed_comments):
    total = len(analyzed_comments or [])
    if total == 0:
        return {
            "total_comments": 0,
            "hate_speech_pct": 0.0,
            "positive_pct": 0.0,
            "negative_pct": 0.0,
            "neutral_pct": 0.0,
            "most_active_day": "N/A"
        }

    s = Counter(c["sentiment"] for c in analyzed_comments)
    h = Counter(c["hate_speech"] for c in analyzed_comments)
    day_counter = Counter(c["date"] for c in analyzed_comments)

    kpis = {
        "total_comments": total,
        "hate_speech_pct": round(100.0 * h.get("Hate Speech", 0) / total, 1),
        "positive_pct": round(100.0 * s.get("Positive", 0) / total, 1),
        "negative_pct": round(100.0 * s.get("Negative", 0) / total, 1),
        "neutral_pct": round(100.0 * s.get("Neutral", 0) / total, 1),
        "most_active_day": (day_counter.most_common(1)[0][0] if day_counter else "N/A"),
    }
    return kpis

# ------------------------------------------------------------------------------------
# 3) Timeline (stacked-by-sentiment)
# ------------------------------------------------------------------------------------
def prepare_timeline_data(analyzed_comments, past_days=None):
    """
    Returns structure your template expects:
      {
        'labels': ['2025-08-12', ...],
        'datasets': {
          'positive': [...],
          'negative': [...],
          'neutral':  [...]
        }
      }
    """
    by_date = defaultdict(lambda: {"Positive": 0, "Negative": 0, "Neutral": 0})
    for c in (analyzed_comments or []):
        d = c.get("date") or _parse_date_any(None)
        s = c.get("sentiment") or "Neutral"
        if s not in _EXPECTED_SENTIMENTS:
            s = "Neutral"
        by_date[d][s] += 1

    labels = sorted(by_date.keys())
    # ensure not empty (prevents chart crash)
    if not labels:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        labels = [today]
        by_date[today] = {"Positive": 0, "Negative": 0, "Neutral": 0}

    data = {
        "labels": labels,
        "datasets": {
            "positive": [by_date[d]["Positive"] for d in labels],
            "negative": [by_date[d]["Negative"] for d in labels],
            "neutral":  [by_date[d]["Neutral"]  for d in labels],
        }
    }
    return data

# ------------------------------------------------------------------------------------
# 4) Insights
# ------------------------------------------------------------------------------------
def generate_insights(analyzed_comments, past_days=None):
    """
    Builds simple, clear insights from analyzed comments only (no extra args needed).
    """
    insights = []
    total = len(analyzed_comments or [])
    if total == 0:
        return ["No comments found in the selected window. Try expanding the date range."]

    s = Counter(c["sentiment"] for c in analyzed_comments)
    h = Counter(c["hate_speech"] for c in analyzed_comments)
    pos, neg, neu = s.get("Positive", 0), s.get("Negative", 0), s.get("Neutral", 0)
    hate = h.get("Hate Speech", 0)

    # Sentiment trend
    if pos > neg:
        insights.append("Overall sentiment skews positive.")
    elif neg > pos:
        insights.append("Negative sentiment is higher—address common complaints in recent uploads.")
    else:
        insights.append("Sentiment distribution is balanced.")

    # Hate speech presence
    if hate > 0:
        insights.append(f"Hate speech detected in {hate} comment(s). Consider moderation filters and keyword blocks.")
    else:
        insights.append("No hate speech detected in this period.")

    # Neutral heavy
    if total and (neu / total) > 0.5:
        insights.append("High neutral ratio—ask questions or pin prompts to drive more polarized engagement.")

    # Engagement hint
    high_like = sum(1 for c in analyzed_comments if c.get("likes", 0) >= 10)
    if high_like:
        insights.append(f"{high_like} comment(s) received 10+ likes—highlight top comments to boost engagement.")

    return insights
