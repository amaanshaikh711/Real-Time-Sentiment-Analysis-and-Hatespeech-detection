import os
import tweepy
import json
import hashlib
from datetime import datetime, timedelta

def fetch_tweets(query, max_results=30):
    """
    Fetch recent tweets for a query using Twitter API v2 via Tweepy.
    Requires TWITTER_BEARER_TOKEN env var.
    Returns list of dicts: {"id": ..., "text": ..., "created_at": ...}
    """
    bearer = os.environ.get("TWITTER_BEARER_TOKEN")
    if not bearer:
        raise RuntimeError("TWITTER_BEARER_TOKEN environment variable is not set.")

    # Don't sleep-block on rate limits here; instead let the caller receive a clear error
    client = tweepy.Client(bearer_token=bearer, wait_on_rate_limit=False)
    # Exclude retweets and fetch English tweets by default
    q = f"{query} -is:retweet lang:en"
    # clamp results to Twitter API limits
    max_results = max(5, min(int(max_results or 30), 100))
    try:
        resp = client.search_recent_tweets(query=q, tweet_fields=["created_at", "lang"], max_results=max_results)
    except Exception as e:
        # Tweepy may raise a TooManyRequests or other exceptions when rate-limited or when the API fails.
        # Raise a RuntimeError so the caller can handle the error and fall back to cache/mock.
        raise RuntimeError(f"Error fetching tweets from Twitter API: {e}")

    tweets = []
    if resp and getattr(resp, 'data', None):
        for t in resp.data:
            created = getattr(t, "created_at", None)
            tweets.append({
                "id": str(t.id),
                "text": t.text,
                "created_at": created.isoformat() if created else None,
            })
    return tweets


def _cache_path_for_query(query):
    safe = hashlib.sha1(query.encode('utf-8')).hexdigest()
    base = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'cache')
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, f"twitter_{safe}.json")


def save_tweets_cache(query, tweets):
    path = _cache_path_for_query(query)
    payload = {
        'query': query,
        'fetched_at': datetime.utcnow().isoformat(),
        'tweets': tweets
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False)


def load_tweets_cache(query, max_age_minutes=60):
    path = _cache_path_for_query(query)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            payload = json.load(f)
        fetched = datetime.fromisoformat(payload.get('fetched_at'))
        if datetime.utcnow() - fetched > timedelta(minutes=max_age_minutes):
            return None
        return payload.get('tweets', [])
    except Exception:
        return None


def mock_tweets(query, count=10):
    # Simple mocked tweets for offline testing and fallback
    samples = [
        f"Sample tweet {i+1} for {query}: This is a test tweet used as mock data." for i in range(count)
    ]
    result = []
    for i, t in enumerate(samples):
        result.append({
            'id': f'mock-{i+1}',
            'text': t,
            'created_at': datetime.utcnow().isoformat(),
            'username': f'mock_user_{i+1}',
        })
    return result


def fetch_tweets_resilient(query, max_results=30, use_cache=True, allow_mock=True):
    """Try to fetch tweets from Twitter API. On failure, return cached results if available, otherwise return mock data if allowed.

    Returns tuple: (tweets_list, source) where source is 'live', 'cache', or 'mock'.
    """
    try:
        tweets = fetch_tweets(query, max_results=max_results)
        if tweets:
            try:
                save_tweets_cache(query, tweets)
            except Exception:
                pass
            return tweets, 'live'
    except Exception as e:
        # log to console (the caller will handle user-visible messages)
        print(f"[twitter_utils] fetch error: {e}")

    if use_cache:
        cached = load_tweets_cache(query)
        if cached:
            return cached, 'cache'

    if allow_mock:
        return mock_tweets(query, count=min(10, int(max_results or 10))), 'mock'

    return [], 'empty'
