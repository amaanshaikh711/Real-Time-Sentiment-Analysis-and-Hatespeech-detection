# config.py
import os
from dotenv import load_dotenv

# Load .env file located next to this config.py file so env vars are available
# regardless of the current working directory used to start the server.
base_dir = os.path.abspath(os.path.dirname(__file__))
dotenv_path = os.path.join(base_dir, '.env')
if os.path.exists(dotenv_path):
	load_dotenv(dotenv_path)
else:
	# Fallback to default loader which will search the cwd and parents
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
# Apify API token (set in environment or .env as APIFY_TOKEN)
# Support a few common env var names and tolerant parsing in case the .env value was written like
# "apify api key=..." or similar by the user. Strip surrounding quotes and whitespace.
def _get_env_token(names):
	for n in names:
		v = os.environ.get(n)
		if v:
			v = v.strip().strip('"').strip("'")
			# if the user pasted a key with a label like 'apify api key-<token>' try to extract last token
			if '=' in v:
				v = v.split('=')[-1].strip()
			if '-' in v and v.lower().startswith('apify'):
				# accept patterns like 'apify_api_key-<token>' or 'apify api key-<token>'
				parts = v.split('-')
				if len(parts) > 1:
					v = parts[-1].strip()
			if v:
				return v
	return None

APIFY_TOKEN = _get_env_token(['APIFY_TOKEN', 'APIFY_API_TOKEN', 'APIFY_API_KEY', 'APIFY_KEY', 'APIFY'])
