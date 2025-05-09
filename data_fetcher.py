import requests
import json
from textblob import TextBlob
from deep_translator import GoogleTranslator  # Updated import
from models import db, Post, Comment
from datetime import datetime
from flask import Flask
import hashlib
import asyncio  # For parallel requests
import aiohttp  # Async HTTP requests

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Hardik%40123@localhost/sentiment_analysis'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Async function to handle requests in parallel
async def fetch_url(session, url, headers=None):
    async with session.get(url, headers=headers) as response:
        return await response.json()

async def fetch_and_store_data(page_id, access_token):
    async with aiohttp.ClientSession() as session:
        def get_posts_url(page_id, access_token):
            return f"https://graph.facebook.com/v20.0/{page_id}/posts?limit=15&fields=message,created_time,attachments{{media}},likes.summary(true),shares&access_token={access_token}"

        def get_comments_url(post_id, access_token):
            return f"https://graph.facebook.com/v20.0/{post_id}/comments?limit=20&access_token={access_token}"

        def analyze_sentiment(text):
            if not text:
                return 'Neutral'
            
            # Initialize deep-translator's GoogleTranslator
            translator = GoogleTranslator(source='auto', target='en')  # Auto-detect the source language
            
            try:
                # Translate text to English (if necessary)
                translated_text = translator.translate(text)
                analysis = TextBlob(translated_text)
                polarity = analysis.sentiment.polarity
                
                if polarity > 0:
                    return 'Positive'
                elif polarity < 0:
                    return 'Negative'
                else:
                    return 'Neutral'
            except Exception as e:
                print(f"Error during sentiment analysis: {e}")
                return 'Neutral'

        def convert_datetime(dt_str):
            try:
                dt = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S%z')
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                print(f"Error converting datetime: {dt_str}")
                return None

        def generate_synthetic_id(post_id, created_time, message):
            data = f"{post_id}_{created_time}_{message}"
            return hashlib.md5(data.encode()).hexdigest()

        # Fetch posts
        posts_url = get_posts_url(page_id, access_token)
        posts_response = await fetch_url(session, posts_url)

        posts = posts_response.get('data', [])
        post_tasks = []  # List of async tasks for parallel comment fetching

        for post in posts:
            post_id = post.get('id', 'No ID')
            post_message = post.get('message', "")
            post_created_time = convert_datetime(post.get('created_time', 'No time'))

            # Get image URL if available
            image_url = ""
            if 'attachments' in post and 'media' in post['attachments']['data'][0]:
                image_url = post['attachments']['data'][0]['media']['image']['src']
            
            # Get likes and shares
            likes_count = post.get('likes', {}).get('summary', {}).get('total_count', 0)
            shares_count = post.get('shares', {}).get('count', 0)
            
            # Analyze post sentiment
            post_sentiment = analyze_sentiment(post_message)

            existing_post = db.session.get(Post, post_id)
            if not existing_post:
                new_post = Post(id=post_id, page_id=page_id, message=post_message, 
                                created_time=post_created_time, image_url=image_url,
                                likes=likes_count, shares=shares_count, sentiment=post_sentiment)
                db.session.add(new_post)

            # Fetch comments asynchronously
            comments_url = get_comments_url(post_id, access_token)
            post_tasks.append(fetch_url(session, comments_url))

        # Await the completion of all comment requests
        comments_responses = await asyncio.gather(*post_tasks)

        for post, comments_response in zip(posts, comments_responses):
            post_id = post.get('id', 'No ID')
            comments = comments_response.get('data', [])
            
            for comment in comments:
                comment_message = comment.get('message', None)
                comment_created_time = convert_datetime(comment.get('created_time', 'No time'))

                if not comment_message:
                    print(f"Skipping comment due to missing message.")
                    continue

                # Analyze comment sentiment
                sentiment = analyze_sentiment(comment_message)
                comment_id = generate_synthetic_id(post_id, comment_created_time, comment_message)

                existing_comment = db.session.get(Comment, comment_id)
                if not existing_comment:
                    new_comment = Comment(id=comment_id, post_id=post_id, message=comment_message, 
                                          created_time=comment_created_time, sentiment=sentiment)
                    db.session.add(new_comment)

        db.session.commit()

# Run within Flask app context
with app.app_context():
    page_id = '1448364408720250'
    access_token = 'EAAMQPmFBDa0BOwdppB9AiAPPIJuNQHqEUPRmGAI4v8VyfodKNKusycz4Min90jpMAy7xqXvrMYsSi86aY84YMujTFrQPof7w5sTnZC5luQL8D0JZBm1oTWH8DC8RFcsufrEiPnF0wPkJcQnJfcDZCtxNLrMGME4sFNgIoszB89PTYIySEQI02pSdJX7a0MfnlrlUtGb9w7LKUJZBGuuQqv4d4tT79f3pl1sZD'

    asyncio.run(fetch_and_store_data(page_id, access_token))
