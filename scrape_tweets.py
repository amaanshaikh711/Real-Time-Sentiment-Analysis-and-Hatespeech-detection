import os
import certifi
os.environ['SSL_CERT_FILE'] = certifi.where()

import snscrape.modules.twitter as sntwitter
import pandas as pd

import ssl
ssl._create_default_https_context = ssl._create_unverified_context


# Your query: adjust keywords or dates as needed
query = "hate speech OR offensive language since:2024-01-01 until:2025-01-01 lang:en"

# Set max tweets to collect (optional)
max_tweets = 100

# List to store tweets
tweets = []

# Loop to fetch tweets
for i, tweet in enumerate(sntwitter.TwitterSearchScraper(query).get_items()):
    if i > 500:
        break
    tweets.append([tweet.date, tweet.user.username, tweet.content])

# Convert to DataFrame
df = pd.DataFrame(tweets, columns=['Date', 'User', 'Tweet'])

# Save to CSV
df.to_csv('hate_speech_tweets.csv', index=False, encoding='utf-8')

print(f"✅ Done! {len(df)} tweets saved to hate_speech_tweets.csv")
