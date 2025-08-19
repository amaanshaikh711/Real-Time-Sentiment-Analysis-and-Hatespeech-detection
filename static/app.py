from flask import Flask, render_template, request
import sys
import os
import pickle
import nltk
from utils.cleaning import clean_text

# Download stopwords once (only if not already downloaded)
nltk.download('stopwords')

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Initialize Flask app
app = Flask(__name__)
app = Flask(__name__, static_folder='static', template_folder='templates')
app.debug = True


# Load sentiment model and vectorizer
with open('model/sentiment_model.pkl', 'rb') as f:
    sentiment_vectorizer, sentiment_model = pickle.load(f)

# Load hate speech model and vectorizer
with open('model/hate_model.pkl', 'rb') as f:
    hate_vectorizer, hate_model = pickle.load(f)

@app.route('/', methods=['GET', 'POST'])
def home():
    sentiment = ""
    hate_speech = ""
    input_text = ""

    if request.method == 'POST':
        # ✅ FIX: Fetch user input safely
        input_text = request.form.get('user_input', '')
        if not input_text.strip():
            return render_template('index.html', error="Please enter some text!")

        # Debug print
        print(f"Received input: {input_text}")

        # Clean the text
        cleaned = clean_text(input_text)
        print(f"Cleaned input: {cleaned}")

        # Predict Sentiment
        try:
            sentiment_vec = sentiment_vectorizer.transform([cleaned])
            sentiment_result = sentiment_model.predict(sentiment_vec)[0]
            sentiment = {
                2: "Positive 😊",
                1: "Neutral 😐",
                0: "Negative 😡"
            }.get(sentiment_result, "Unknown")
        except Exception as e:
            sentiment = f"Error in sentiment prediction: {str(e)}"

        # Predict Hate Speech
        try:
            hate_vec = hate_vectorizer.transform([cleaned])
            hate_result = hate_model.predict(hate_vec)[0]
            hate_speech = "Hate Speech 🚫" if hate_result == 1 else "None ✅"
        except Exception as e:
            hate_speech = f"Error in hate speech prediction: {str(e)}"

        return render_template('index.html', sentiment=sentiment, hate_speech=hate_speech, input_text=input_text)

    return render_template('index.html')

@app.route('/input', methods=['GET', 'POST'])
def input_page():
    return render_template('input.html')

if __name__ == '__main__':
    app.run(debug=True)
