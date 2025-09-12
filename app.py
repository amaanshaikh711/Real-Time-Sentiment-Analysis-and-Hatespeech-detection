# app.py (enhanced with Supabase authentication) - Full replacement

from dotenv import load_dotenv
load_dotenv()

import os
import re
import json
import nltk
from functools import wraps
from datetime import datetime, timedelta
import hashlib
import secrets
import warnings

# Suppress scikit-learn version warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

nltk.download('stopwords', quiet=True)

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, g
from markupsafe import Markup
import supabase
from supabase import create_client, Client
from flask_cors import CORS, cross_origin

from model.predict import predict
from utils.cleaning import count_offensive_words, OFFENSIVE_WORDS
import plotly.graph_objects as go
import plotly.io as pio

from helpers.youtube_fetch import (
    get_comments_by_video,
    get_comments_by_channel,
    extract_video_id,
    extract_channel_id
)
from helpers.analysis import (
    analyze_comments_sentiment_hate,
    prepare_timeline_data,
    generate_insights,
    calculate_kpis
)

# Initialize Flask app
template_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'templates')
app = Flask(__name__, static_folder='static', template_folder=template_dir)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['USE_SUPABASE'] = True  # Use app config instead of global

# Ensure cookies are sent in common dev setups (adjust for production)
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True

# Supabase configuration
from config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY

# Use service key for admin operations, anon key for client operations
SUPABASE_ANON_KEY = SUPABASE_KEY or SUPABASE_SERVICE_KEY

# Fallback user storage for testing when Supabase is unavailable
fallback_users = {}

# Initialize USE_SUPABASE from app config
USE_SUPABASE = app.config['USE_SUPABASE']

try:
    supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    print(f"[INFO] Connected to Supabase: {SUPABASE_URL}")
except Exception as e:
    print(f"[WARNING] Failed to connect to Supabase: {e}")
    print("[INFO] Using fallback authentication system for testing")
    supabase_client = None
    app.config['USE_SUPABASE'] = False
    USE_SUPABASE = False

# Enable CORS globally
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

def network_safe(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except requests.exceptions.RequestException:
            app.logger.exception("Supabase network error")
            return jsonify({"error": "Network connection error. Please check your internet connection and try again."}), 503
        except Exception:
            app.logger.exception("Internal error in auth route")
            return jsonify({"error": "Internal server error"}), 500
    return decorated

# -----------------------
# Authentication Decorators
# -----------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        
        # Check if user is admin
        user_role = session.get('user_role', 'user')
        if user_role != 'admin':
            flash('Admin access required.', 'danger')
            # dashboard removed — redirect to home
            return redirect(url_for('home'))
        
        return f(*args, **kwargs)
    return decorated_function

# -----------------------
# Context Processors
# -----------------------
@app.before_request
def load_user():
    from flask import current_app
    current_use_supabase = current_app.config.get('USE_SUPABASE', True)
    
    if 'user_id' in session:
        user_id = session['user_id']
        user_email = session.get('user_email')

        if current_use_supabase and supabase_client:
            try:
                user_response = supabase_client.auth.get_user()
                if user_response.user:
                    g.user = {
                        'id': user_response.user.id,
                        'email': user_response.user.email,
                        'user_metadata': user_response.user.user_metadata or {}
                    }
                else:
                    session.clear()
                    g.user = None
            except Exception:
                session.clear()
                g.user = None
        else:
            # Use fallback user data
            if user_email and user_email in fallback_users:
                user_data = fallback_users[user_email]
                g.user = {
                    'id': user_data['id'],
                    'email': user_data['email'],
                    'username': user_data['username'],
                    'user_metadata': {'username': user_data['username']}
                }
            else:
                session.clear()
                g.user = None
    else:
        g.user = None

@app.context_processor
def inject_user():
    return dict(current_user=g.user)

# -----------------------
# Add small helper to set session in one place (moved here so login can call it)
def _set_session_user(user_id, email, username=None):
    # set unified session keys and make session persistent
    session.clear()
    session['user_id'] = user_id
    session['user_email'] = email
    if username:
        session['user_username'] = username
    session.permanent = True

# -----------------------
# Authentication Routes
# -----------------------
@app.route('/signup', methods=['GET', 'POST'])
@cross_origin()
@network_safe
def signup():
	from flask import current_app
	current_use_supabase = current_app.config.get('USE_SUPABASE', True)
	
	print(f"[DEBUG] Signup route called. Method: {request.method}, USE_SUPABASE: {current_use_supabase}")

	if request.method == 'POST':
		email = request.form.get('email')
		password = request.form.get('password')
		confirm_password = request.form.get('confirm_password')
		username = request.form.get('username')

		print(f"[DEBUG] Signup form data - Email: {email}, Username: {username}")

		# Validation
		if not email or not password or not confirm_password or not username:
			flash('All fields are required.', 'danger')
			return render_template('auth/signup.html')

		if password != confirm_password:
			flash('Passwords do not match.', 'danger')
			return render_template('auth/signup.html')

		if len(password) < 6:
			flash('Password must be at least 6 characters.', 'danger')
			return render_template('auth/signup.html')

		if len(username) < 3:
			flash('Username must be at least 3 characters.', 'danger')
			return render_template('auth/signup.html')

		# Check if email already exists in fallback storage
		if email in fallback_users:
			flash('Email already registered. Please login instead.', 'warning')
			return render_template('auth/signup.html')

		# If Supabase is available, try it first
		if current_use_supabase and supabase_client:
			try:
				# Sign up with Supabase
				response = supabase_client.auth.sign_up({
					'email': email,
					'password': password,
					'options': {
						'data': {
							'username': username,
							'created_at': datetime.utcnow().isoformat()
						}
					}
				})

				if response.user:
					flash('Account created successfully! Please check your email to verify your account.', 'success')
					return redirect(url_for('login'))
				else:
					flash('Error creating account. Please try again.', 'danger')

			except Exception as e:
				error_msg = str(e).lower()
				print(f"[AUTH ERROR] Supabase signup failed: {e}")  # Debug logging

				if 'getaddrinfo' in error_msg or 'network' in error_msg or 'connection' in error_msg:
					print("[INFO] Switching to fallback authentication due to network error")
					current_app.config['USE_SUPABASE'] = False
					flash('Network connection error. Using local authentication for testing.', 'warning')
				else:
					flash('An error occurred during signup. Please try again.', 'danger')
					return render_template('auth/signup.html')

		# Fallback authentication (when Supabase is unavailable or failed)
		# Use the current app config flag rather than stale global variable
		if not current_app.config.get('USE_SUPABASE', True):
			print(f"[INFO] Using fallback authentication for signup: {email}")
			print(f"[DEBUG] Current fallback_users count: {len(fallback_users)}")

			# Create user in fallback storage
			user_id = secrets.token_hex(16)
			fallback_users[email] = {
				'id': user_id,
				'email': email,
				'username': username,
				'password_hash': hashlib.sha256(password.encode()).hexdigest(),
				'created_at': datetime.utcnow().isoformat(),
				'verified': True  # Skip email verification for testing
			}

			print(f"[SUCCESS] Created fallback user: {email} (ID: {user_id})")
			print(f"[DEBUG] Updated fallback_users count: {len(fallback_users)}")
			flash('Account created successfully! You can now login.', 'success')
			return redirect(url_for('login'))

		# If we get here, something went wrong
		flash('Unable to create account. Please try again.', 'danger')

	return render_template('auth/signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
	# If already logged in, don't show login page again
	# Fix: check the actual session key set on login ('user_id')
	if 'user_id' in session:
		return redirect(url_for('home'))

	from flask import current_app
	current_use_supabase = current_app.config.get('USE_SUPABASE', True)
	
	print(f"[DEBUG] Login route called. Method: {request.method}, USE_SUPABASE: {current_use_supabase}")

	if request.method == 'POST':
		email = request.form.get('email')
		password = request.form.get('password')

		print(f"[DEBUG] Login form data - Email: {email}")

		if not email or not password:
			flash('Email and password are required.', 'danger')
			return render_template('auth/login.html')

		# If Supabase is available, try it first
		if current_use_supabase and supabase_client:
			try:
				# Sign in with Supabase
				response = supabase_client.auth.sign_in_with_password({
					'email': email,
					'password': password
				})

				if response.user:
					# Store user info in session (use helper)
					_set_session_user(response.user.id, response.user.email,
									  response.user.user_metadata.get('username', 'User') if response.user.user_metadata else 'User')

					flash('Logged in successfully!', 'success')

					# Redirect to next page or home (dashboard removed)
					next_page = request.args.get('next')
					if next_page:
						return redirect(next_page)
					return redirect(url_for('home'))
				else:
					flash('Invalid email or password.', 'danger')

			except Exception as e:
				error_msg = str(e).lower()
				print(f"[AUTH ERROR] Supabase login failed: {e}")  # Debug logging

				if 'getaddrinfo' in error_msg or 'network' in error_msg or 'connection' in error_msg:
					print("[INFO] Switching to fallback authentication due to network error")
					current_app.config['USE_SUPABASE'] = False
					flash('Network connection error. Using local authentication for testing.', 'warning')
				else:
					flash('Login failed. Please check your credentials and try again.', 'danger')
					return render_template('auth/login.html')

		# Fallback authentication (when Supabase is unavailable)
		if not current_app.config.get('USE_SUPABASE', True):
			print(f"[INFO] Using fallback authentication for login: {email}")
			print(f"[DEBUG] Checking if email exists in fallback_users: {email in fallback_users}")

			if email in fallback_users:
				user_data = fallback_users[email]
				print(f"[DEBUG] Found user data: {user_data['email']}")

				# Verify password
				password_hash = hashlib.sha256(password.encode()).hexdigest()
				stored_hash = user_data['password_hash']
				print(f"[DEBUG] Password verification: input hash matches stored hash: {password_hash == stored_hash}")

				if password_hash == stored_hash:
					# Store user info in session via helper
					_set_session_user(user_data['id'], user_data['email'], user_data['username'])

					print(f"[SUCCESS] Fallback login successful for: {email}")
					flash('Logged in successfully!', 'success')

					# Redirect to next page or home (dashboard removed)
					next_page = request.args.get('next')
					if next_page:
						return redirect(next_page)
					return redirect(url_for('home'))
				else:
					print(f"[ERROR] Password mismatch for: {email}")
					flash('Invalid email or password.', 'danger')
			else:
				print(f"[ERROR] Email not found in fallback_users: {email}")
				flash('Invalid email or password.', 'danger')

	return render_template('auth/login.html')

@app.route('/logout')
def logout():
    from flask import current_app
    current_use_supabase = current_app.config.get('USE_SUPABASE', True)
    
    if current_use_supabase and supabase_client:
        try:
            supabase_client.auth.sign_out()
        except:
            pass

    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/profile')
@login_required
def profile():
	from flask import current_app
	current_use_supabase = current_app.config.get('USE_SUPABASE', True)
	
	if current_use_supabase and supabase_client:
		try:
			user_response = supabase_client.auth.get_user()
			return render_template('auth/profile.html', user=user_response.user)
		except Exception as e:
			flash(f'Error loading profile: {str(e)}', 'danger')
			# dashboard removed — use home
			return redirect(url_for('home'))
	else:
		# Use fallback user data
		user_email = session.get('user_email')
		if user_email and user_email in fallback_users:
			user_data = fallback_users[user_email]
			# Create a mock user object for template compatibility
			class MockUser:
				def __init__(self, data):
					self.id = data['id']
					self.email = data['email']
					self.user_metadata = {'username': data['username']}
					self.created_at = data['created_at']

			mock_user = MockUser(user_data)
			return render_template('auth/profile.html', user=mock_user)
		else:
			flash('User data not found.', 'danger')
			return redirect(url_for('home'))

@app.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    from flask import current_app
    current_use_supabase = current_app.config.get('USE_SUPABASE', True)
    
    username = request.form.get('username')

    if not username or len(username.strip()) < 3:
        flash('Username must be at least 3 characters.', 'danger')
        return redirect(url_for('profile'))

    if current_use_supabase and supabase_client:
        try:
            response = supabase_client.auth.update_user({
                'data': {'username': username}
            })

            if response.user:
                session['user_username'] = username
                flash('Profile updated successfully!', 'success')
            else:
                flash('Error updating profile.', 'danger')

        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    else:
        # Update fallback user data
        user_email = session.get('user_email')
        if user_email and user_email in fallback_users:
            fallback_users[user_email]['username'] = username.strip()
            session['user_username'] = username
            flash('Profile updated successfully!', 'success')
        else:
            flash('User data not found.', 'danger')

    return redirect(url_for('profile'))



# -----------------------
# Public Routes
# -----------------------
@app.route('/')
def home():
    # If user is not logged in, redirect to login page
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/blog')
def blog():
    return render_template('blog.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

# -----------------------
# Protected Routes
# -----------------------
@app.route('/input', methods=['GET', 'POST'])
@app.route('/analyser/input', methods=['GET', 'POST'])
@login_required
def input_page():
    # Enhanced input page with user tracking
    sentiment = ""
    hate_speech = ""
    input_text = ""
    sentiment_score = {"Positive": 0, "Neutral": 0, "Negative": 0}
    hate_score = {"Hate Speech": 0, "None": 0}
    offensive_word_count = 0
    vulgarity = "--"
    pie_chart_div = None
    bar_chart_div = None
    line_chart_div = None
    highlighted_input = None
    sentiment_emoji = ""
    offensive_found = []

    if request.method == 'POST':
        import pandas as pd

        if 'csv_file' in request.files and request.files['csv_file'].filename != '':
            csv_file = request.files['csv_file']
            try:
                df = pd.read_csv(csv_file)
                text_column = None
                possible_columns = ['text', 'tweet', 'content', 'message', 'caption']
                for col in df.columns:
                    if any(possible_col in col.lower() for possible_col in possible_columns):
                        text_column = col
                        break
                if text_column is None and len(df.columns) > 0:
                    text_column = df.columns[0]
                if text_column and len(df) > 0:
                    rows_to_analyze = min(5, len(df))
                    texts = df[text_column].head(rows_to_analyze).fillna('').tolist()
                    input_text = '\n'.join(texts)
                else:
                    input_text = "Could not find text data in the CSV file."
            except Exception as e:
                input_text = f"Error processing CSV file: {str(e)}"
        else:
            input_text = request.form.get('user_input', '')

        OFFENSIVE_WORDS_LIST = OFFENSIVE_WORDS or set()
        words = [w.strip('.,!?;:').lower() for w in input_text.split()]
        offensive_found = [w for w in words if w in OFFENSIVE_WORDS_LIST]
        offensive_word_count = len(offensive_found)
        total_words = len([w for w in words if w.isalpha()])
        if total_words == 0:
            total_words = 1
        vulgarity_percentage = round((offensive_word_count / total_words) * 100, 2)
        if offensive_word_count == 0:
            vulgarity_label = "Clean"
        elif vulgarity_percentage < 10:
            vulgarity_label = "Low"
        elif vulgarity_percentage < 30:
            vulgarity_label = "Medium"
        else:
            vulgarity_label = "High"
        vulgarity = f"{vulgarity_label} ({vulgarity_percentage}%)"

        import re as _re
        def highlight_offensive_words(text):
            def replacer(match):
                word = match.group(0).lower()
                if word in OFFENSIVE_WORDS_LIST:
                    return f'<span style="color: red; font-weight: bold;">{match.group(0)}</span>'
                return match.group(0)
            pattern = _re.compile(r'\b\w+\b', _re.IGNORECASE)
            return pattern.sub(replacer, text)
        highlighted_input = highlight_offensive_words(input_text)

        sentiment_result = predict(input_text, mode='sentiment')
        hate_result = predict(input_text, mode='hate')
        sentiment = str(sentiment_result)
        hate_speech = str(hate_result)

        sentiment_score = {"Positive": 0, "Neutral": 0, "Negative": 0}
        hate_score = {"Hate Speech": 0, "None": 100}
        if sentiment.lower().startswith("positive"):
            sentiment_emoji = "😊"
            sentiment_score["Positive"] = 100
        elif sentiment.lower().startswith("neutral"):
            sentiment_emoji = "😐"
            sentiment_score["Neutral"] = 100
        elif sentiment.lower().startswith("negative"):
            sentiment_emoji = "😠"
            sentiment_score["Negative"] = 100

        if hate_speech.lower().startswith("hate speech") or hate_speech.lower().startswith("hate"):
            hate_score["Hate Speech"] = 100
            hate_score["None"] = 0

        # charts code
        labels = ['Positive', 'Neutral', 'Negative']
        values = [sentiment_score['Positive'], sentiment_score['Neutral'], sentiment_score['Negative']]
        fig_bar_sentiment = go.Figure(data=[go.Bar(x=labels, y=values, text=[f'{v:.0f}%' for v in values], textposition='auto', hoverinfo='y+text')])
        fig_bar_sentiment.update_layout(margin=dict(t=20, b=20, l=20, r=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300, font=dict(family='Inter, sans-serif', color='white'), xaxis=dict(title='', tickfont=dict(size=14, color='#ffffff')), yaxis=dict(title='Score', tickfont=dict(size=12, color='#ffffff'), range=[0, 100]))
        sentiment_chart = pio.to_html(fig_bar_sentiment, full_html=False)

        from collections import Counter
        offensive_freq = Counter([w for w in words if w in OFFENSIVE_WORDS_LIST])
        if not offensive_freq:
            bar_labels = ['No offensive words found']
            bar_values = [0]
        else:
            bar_labels = list(offensive_freq.keys())
            bar_values = list(offensive_freq.values())
        fig_bar = go.Figure(data=[go.Bar(x=bar_labels, y=bar_values, textposition='auto', textfont=dict(color='white'), hoverinfo='x+y')])
        fig_bar.update_layout(margin=dict(t=10, b=0, l=0, r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=250, font=dict(family='Inter, sans-serif', color='white'))
        bar_chart_div = pio.to_html(fig_bar, full_html=False)

        return render_template(
            'input.html',
            sentiment=sentiment,
            hate_speech=hate_speech,
            user_input=input_text,
            sentiment_score=sentiment_score,
            hate_score=hate_score,
            offensive_word_count=offensive_word_count,
            vulgarity=vulgarity,
            sentiment_chart=sentiment_chart,
            bar_chart_div=bar_chart_div,
            line_chart_div=line_chart_div,
            highlighted_input=highlighted_input,
            sentiment_emoji=sentiment_emoji,
            offensive_words_found=offensive_found
        )

    return render_template(
        'input.html',
        sentiment=sentiment,
        hate_speech=hate_speech,
        user_input=input_text,
        sentiment_score=sentiment_score,
        hate_score=hate_score,
        offensive_word_count=offensive_word_count,
        vulgarity=vulgarity,
        sentiment_chart=None,
        bar_chart_div=bar_chart_div,
        line_chart_div=line_chart_div,
        highlighted_input=highlighted_input,
        sentiment_emoji=sentiment_emoji,
        offensive_words_found=[]
    )

@app.route('/dashboard')
@login_required
def dashboard():
	# Dashboard page removed — preserve link behavior by sending user to home
	return redirect(url_for('home'))

@app.route('/export')
@login_required
def export():
	# Export page removed — redirect to home
	return redirect(url_for('home'))

# -----------------------
# Enhanced YouTube Analysis Route
# -----------------------
@app.route('/youtube-analysis', methods=['GET', 'POST'])
@login_required
def youtube_analysis():
    def _make_json_safe(o):
        if o is None:
            return None
        if isinstance(o, (str, int, float, bool)):
            return o
        try:
            from markupsafe import Markup as _Markup
            if isinstance(o, _Markup):
                return str(o)
        except Exception:
            pass
        try:
            if getattr(o, "__class__", None) and o.__class__.__name__ == "Undefined":
                return None
        except Exception:
            pass
        if isinstance(o, dict):
            return {k: _make_json_safe(v) for k, v in o.items()}
        if isinstance(o, (list, tuple, set)):
            return [_make_json_safe(v) for v in o]
        if hasattr(o, "__dict__"):
            try:
                return _make_json_safe(vars(o))
            except Exception:
                pass
        try:
            return str(o)
        except Exception:
            return None

    def _escape_script_tags_in_obj(o):
        if o is None:
            return None
        if isinstance(o, (int, float, bool)):
            return o
        if isinstance(o, str):
            return o.replace('</script>', '<\\/script>').replace('\r', '\\r').replace('\n', '\\n')
        if isinstance(o, dict):
            return {k: _escape_script_tags_in_obj(v) for k, v in o.items()}
        if isinstance(o, list):
            return [_escape_script_tags_in_obj(v) for v in o]
        if isinstance(o, tuple):
            return tuple(_escape_script_tags_in_obj(v) for v in o)
        try:
            return str(o)
        except Exception:
            return None

    if request.method == 'POST':
        try:
            youtube_input = request.form.get('youtube_url', '').strip()
            past_days = min(max(1, int(request.form.get('past_days', 7))), 30)

            if not youtube_input:
                return render_template('youtube_analysis.html', results={'error': 'Please enter a YouTube video URL or channel ID'})

            video_id = extract_video_id(youtube_input)
            channel_id = None
            if not video_id:
                channel_id = extract_channel_id(youtube_input)
                if not channel_id and re.match(r"^UC[A-Za-z0-9_\-]{20,}$", youtube_input):
                    channel_id = youtube_input

            if not video_id and not channel_id:
                return render_template('youtube_analysis.html', results={'error': 'Invalid YouTube URL or ID. Please provide a valid video URL or channel ID.'})

            if video_id:
                comments_data = get_comments_by_video(video_id, past_days)
            else:
                comments_data = get_comments_by_channel(channel_id, past_days)

            if isinstance(comments_data, dict) and 'error' in comments_data:
                return render_template('youtube_analysis.html', results={'error': f"Could not retrieve comments: {comments_data['error']}"})
            if not isinstance(comments_data, list):
                return render_template('youtube_analysis.html', results={'error': 'Unexpected response fetching comments.'})
            if len(comments_data) == 0:
                return render_template('youtube_analysis.html', results={'error': 'No comments returned from YouTube for given input.'})

            normalized_comments = []
            for raw in comments_data:
                text = (raw.get('text') or '').strip()
                if not text:
                    continue

                try:
                    sent_raw = predict(text, mode='sentiment')
                except Exception:
                    sent_raw = None
                try:
                    hate_raw = predict(text, mode='hate')
                except Exception:
                    hate_raw = None

                def map_sent(s):
                    if not s:
                        return "Neutral"
                    sv = str(s).strip().lower()
                    if sv.startswith('pos') or 'positive' in sv:
                        return "Positive"
                    if sv.startswith('neg') or 'negative' in sv:
                        return "Negative"
                    return "Neutral"

                def map_hate(h):
                    if not h:
                        return "Safe Content"
                    hv = str(h).strip().lower()
                    if hv.startswith('hate') or 'hate' in hv or hv in ('offensive','abusive'):
                        return "Hate Speech"
                    return "Safe Content"

                sent = map_sent(sent_raw)
                hate = map_hate(hate_raw)

                normalized_comments.append({
                    'text': text,
                    'username': raw.get('username') or raw.get('author') or 'Unknown',
                    'date': raw.get('date') or raw.get('publishedAt') or '',
                    'likes': int(raw.get('likes') or raw.get('likeCount') or 0),
                    'sentiment': sent,
                    'hate_speech': hate
                })

            if not normalized_comments:
                return render_template('youtube_analysis.html', results={'error': 'No valid comment text found (all empty).'})

            analyzed_comments = analyze_comments_sentiment_hate(normalized_comments)
            kpis = calculate_kpis(analyzed_comments)
            timeline_data = prepare_timeline_data(analyzed_comments, past_days)
            insights = generate_insights(analyzed_comments, past_days)

            print("[DEBUG] sentiment counts:", {s: sum(1 for c in analyzed_comments if c['sentiment'] == s) for s in ('Positive','Neutral','Negative')})

            sentiment_distribution = {
                'Positive': sum(1 for c in analyzed_comments if c['sentiment'] == 'Positive'),
                'Neutral':  sum(1 for c in analyzed_comments if c['sentiment'] == 'Neutral'),
                'Negative': sum(1 for c in analyzed_comments if c['sentiment'] == 'Negative'),
            }
            hate_distribution = {
                'Safe Content': sum(1 for c in analyzed_comments if c['hate_speech'] == 'Safe Content'),
                'Hate Speech':  sum(1 for c in analyzed_comments if c['hate_speech'] == 'Hate Speech'),
            }

            results = {
                'kpis': kpis,
                'total_comments': len(analyzed_comments),
                'analyzed_comments': analyzed_comments,
                'timeline_data': timeline_data,
                'insights': insights,
                'error': None,
                'hate_percentage': kpis.get('hate_speech_pct', 0.0),
                'positive_percentage': kpis.get('positive_pct', 0.0),
                'negative_percentage': kpis.get('negative_pct', 0.0),
                'neutral_percentage': kpis.get('neutral_pct', 0.0),
                'sentiment_distribution': sentiment_distribution,
                'hate_distribution': hate_distribution,
                'charts': {
                    'pie_sent': str(pio.to_html(go.Figure(), full_html=False)),
                }
            }

            charts_html = {
                'pie_sent': Markup(str(pio.to_html(go.Figure(), full_html=False))),
            }

            safe_results = _make_json_safe(results)
            safe_results = _escape_script_tags_in_obj(safe_results)
            results_json = json.dumps(safe_results)
            return render_template('youtube_analysis.html', results=safe_results, charts=charts_html, results_json=results_json)

        except Exception as e:
            import traceback
            error_message = f"Error during YouTube analysis: {str(e)}"
            print(error_message)
            print(traceback.format_exc())
            return render_template('youtube_analysis.html', results={'error': error_message})

    return render_template('youtube_analysis.html', results=None)

# -----------------------
# API Routes
# -----------------------
@app.route('/api/user-info')
@login_required
def api_user_info():
    return jsonify({
        'user_id': session.get('user_id'),
        'email': session.get('user_email'),
        'username': session.get('user_username')
    })

# -----------------------
# Error Handlers
# -----------------------
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500

# -----------------------
# Run server
# -----------------------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)