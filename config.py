# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# YouTube Data API v3 Configuration
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', 'AIzaSyDrJRCcmTjIWREWOOyYZUo9NYVlGwQFO1Y')

# Flask Configuration
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Supabase Configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://tlnsqotkisihceilmnng.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')

# Other configuration settings can be added here
DEBUG = os.environ.get('FLASK_ENV') == 'development'
