# helpers/youtube_fetch.py — full rebuild

import os
import re
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import YOUTUBE_API_KEY as FALLBACK_KEY
import requests

# -----------------------------
# Helper functions
# -----------------------------
def _get_service():
    """Build a YouTube Data API client with resilient discovery fallback.

    Tries default (may target youtube.googleapis.com), then falls back to
    discovery over www.googleapis.com which is more widely resolvable.
    Returns (service, api_key). If both attempts fail, returns (None, api_key)
    so callers can use plain REST fallback.
    """
    api_key = os.getenv('YOUTUBE_API_KEY') or FALLBACK_KEY
    if not api_key or api_key.strip().lower().startswith('your'):
        raise RuntimeError("YouTube API key is missing. Set YOUTUBE_API_KEY in environment or config.py")

    # Attempt default discovery first
    try:
        svc = build('youtube', 'v3', developerKey=api_key, cache_discovery=False)
        return svc, api_key
    except Exception:
        pass

    # Fallback: use discovery from www.googleapis.com explicitly
    try:
        svc = build(
            'youtube', 'v3', developerKey=api_key, cache_discovery=False,
            discoveryServiceUrl='https://www.googleapis.com/discovery/v1/apis/{api}/{apiVersion}/rest'
        )
        return svc, api_key
    except Exception:
        # Last resort: caller should use REST
        return None, api_key

def _iso_days_ago(days):
    dt = datetime.utcnow() - timedelta(days=int(days or 7))
    return dt.isoformat("T") + "Z"

# -----------------------------
# Extraction functions
# -----------------------------
def extract_video_id(url):
    """
    Extracts YouTube video ID from URL.
    Example: https://www.youtube.com/watch?v=abcd -> abcd
    """
    match = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', url)
    return match.group(1) if match else None

def extract_channel_id(url):
    """
    Extracts YouTube channel ID from URL.
    Example: https://www.youtube.com/channel/UCabcd -> UCabcd
    """
    match = re.search(r'channel/([a-zA-Z0-9_-]+)', url)
    return match.group(1) if match else None

# -----------------------------
# Comment fetching functions
# -----------------------------
def get_comments_by_video(video_id, past_days=7, max_items=500):
    """
    Returns list of comment dicts with: text, username, date(YYYY-MM-DD), likes
    """
    service, api_key = _get_service()
    published_after = _iso_days_ago(past_days)
    out = []

    try:
        if service is not None:
            req = service.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=100,
                order="time",
                textFormat="plainText"
            )
            while req and len(out) < max_items:
                res = req.execute()
                for item in res.get('items', []):
                    sn = item['snippet']['topLevelComment']['snippet']
                    out.append({
                        'text': sn.get('textDisplay', ''),
                        'username': sn.get('authorDisplayName', 'Unknown'),
                        'date': sn.get('publishedAt', '')[:10],
                        'likes': sn.get('likeCount', 0)
                    })
                req = service.commentThreads().list_next(req, res)
        else:
            # Plain REST fallback via www.googleapis.com
            url = 'https://www.googleapis.com/youtube/v3/commentThreads'
            params = {
                'part': 'snippet',
                'videoId': video_id,
                'maxResults': 100,
                'order': 'time',
                'textFormat': 'plainText',
                'key': api_key
            }
            page_token = None
            while len(out) < max_items:
                if page_token:
                    params['pageToken'] = page_token
                resp = requests.get(url, params=params, timeout=15)
                if resp.status_code != 200:
                    return {'error': f"YouTube REST error: {resp.status_code} {resp.text[:200]}"}
                data = resp.json()
                for item in data.get('items', []):
                    sn = item['snippet']['topLevelComment']['snippet']
                    out.append({
                        'text': sn.get('textDisplay', ''),
                        'username': sn.get('authorDisplayName', 'Unknown'),
                        'date': sn.get('publishedAt', '')[:10],
                        'likes': sn.get('likeCount', 0)
                    })
                page_token = data.get('nextPageToken')
                if not page_token:
                    break
                if len(out) >= max_items:
                    break
    except HttpError as e:
        return {'error': f"YouTube API error: {e}"}
    except Exception as e:
        return {'error': f"Failed to fetch video comments: {e}"}
    return out

def get_comments_by_channel(channel_id, past_days=7, max_items=800):
    """
    Fetch recent videos in window, then aggregate their comments.
    """
    service, api_key = _get_service()
    published_after = _iso_days_ago(past_days)
    comments = []

    try:
        videos = []
        if service is not None:
            # 1) recent uploads via client
            vreq = service.search().list(
                part="snippet",
                channelId=channel_id,
                order="date",
                publishedAfter=published_after,
                type="video",
                maxResults=50
            )
            while vreq and len(videos) < 50:
                vres = vreq.execute()
                for it in vres.get('items', []):
                    videos.append(it['id']['videoId'])
                vreq = service.search().list_next(vreq, vres)
        else:
            # 1) recent uploads via REST fallback
            url = 'https://www.googleapis.com/youtube/v3/search'
            params = {
                'part': 'snippet',
                'channelId': channel_id,
                'order': 'date',
                'publishedAfter': published_after,
                'type': 'video',
                'maxResults': 50,
                'key': api_key
            }
            page_token = None
            while len(videos) < 50:
                if page_token:
                    params['pageToken'] = page_token
                resp = requests.get(url, params=params, timeout=15)
                if resp.status_code != 200:
                    return {'error': f"YouTube REST error: {resp.status_code} {resp.text[:200]}"}
                data = resp.json()
                for it in data.get('items', []):
                    vid = ((it.get('id') or {}).get('videoId'))
                    if vid:
                        videos.append(vid)
                page_token = data.get('nextPageToken')
                if not page_token:
                    break

        # 2) comments per video
        for vid in videos:
            chunk = get_comments_by_video(
                vid, past_days=past_days, max_items=max(0, max_items - len(comments))
            )
            if isinstance(chunk, dict) and 'error' in chunk:
                return chunk
            comments.extend(chunk)
            if len(comments) >= max_items:
                break

    except HttpError as e:
        return {'error': f"YouTube API error: {e}"}
    except Exception as e:
        return {'error': f"Failed to fetch channel comments: {e}"}

    return comments
 