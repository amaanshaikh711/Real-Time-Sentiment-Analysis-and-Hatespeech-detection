# config.py
import os
from dotenv import load_dotenv

# Load .env file explicitly
base_dir = os.path.abspath(os.path.dirname(__file__))
dotenv_path = os.path.join(base_dir, '.env')

if os.path.exists(dotenv_path):
    print(f"[INFO] Loading .env from {dotenv_path}")
    load_dotenv(dotenv_path, override=True)
else:
    print("[WARNING] .env file not found!")
    # Fallback
    load_dotenv()

# YouTube Data API v3 Configuration
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', 'AIzaSyDrJRCcmTjIWREWOOyYZUo9NYVlGwQFO1Y')

# Flask Configuration
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Clerk Configuration
# Try multiple possible key names and clean them
def get_env_clean(key):
    val = os.environ.get(key)
    if val:
        return val.strip().strip("'").strip('"')
    return None

CLERK_PUBLISHABLE_KEY = get_env_clean("CLERK_PUBLISHABLE_KEY") or get_env_clean("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY")
CLERK_SECRET_KEY = get_env_clean("CLERK_SECRET_KEY")

if CLERK_PUBLISHABLE_KEY:
    print(f"[INFO] Clerk Publishable Key Found: {CLERK_PUBLISHABLE_KEY[:10]}...")
else:
    print("[ERROR] Clerk Publishable Key NOT found in environment variables.")

# Other configuration settings
DEBUG = os.environ.get('FLASK_ENV') == 'development'

# Apify API token
def _get_env_token(names):
    for n in names:
        v = os.environ.get(n)
        if v:
            v = v.strip().strip('"').strip("'")
            if '=' in v:
                v = v.split('=')[-1].strip()
            if '-' in v and v.lower().startswith('apify'):
                parts = v.split('-')
                if len(parts) > 1:
                    v = parts[-1].strip()
            if v:
                return v
    return None

APIFY_TOKEN = _get_env_token(['APIFY_TOKEN', 'APIFY_API_TOKEN', 'APIFY_API_KEY', 'APIFY_KEY', 'APIFY'])
