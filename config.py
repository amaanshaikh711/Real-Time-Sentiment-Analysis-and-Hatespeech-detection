# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# YouTube Data API v3 Configuration
# Replace 'YOUR_API_KEY_HERE' with your actual YouTube Data API v3 key
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', 'AIzaSyDrJRCcmTjIWREWOOyYZUo9NYVlGwQFO1Y')

# Flask Configuration
SECRET_KEY = os.environ.get('SECRET_KEY', 'AIzaSyDrJRCcmTjIWREWOOyYZUo9NYVlGwQFO1Y1')

# Other configuration settings can be added here
DEBUG = os.environ.get('FLASK_ENV') == 'development'
