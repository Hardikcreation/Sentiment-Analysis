import requests
import json
from flask import Flask
from datetime import datetime
from models import db, Post, Comment
import hashlib
import asyncio
import aiohttp
from transformers import AutoModelForSequenceClassification, XLMRobertaTokenizer, pipeline

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Hardik%40123@localhost/tweet'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

async def fetch_url(session, url):
    try:
        async with session.get(url) as response:
            return await response.json()
    except Exception as e:
        print(f"Error fetching URL {url}: {e}")
        return {}

async def fetch_and_store_data(page_id, access_token):
    async with aiohttp.ClientSession() as session:
        def get_posts_url():
            return f"https://graph.facebook.com/v20.0/{page_id}/posts?limit=25&fields=message,created_time,attachments{{media}},likes.summary(true),shares&access_token={access_token}"

        def get_comments_url(post_id):
            return f"https://graph.facebook.com/v20.0/{post_id}/comments?limit=20&access_token={access_token}"

        model_name = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
        tokenizer = XLMRobertaTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        sentiment_pipeline = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)

        def analyze_sentiment(text):
            if not text:
                return 'Neutral'
            try:
                result = sentiment_pipeline(text[:512])[0]
                label = result['label']
                if 'positive' in label.lower():
                    return 'Positive'
                elif 'negative' in label.lower():
                    return 'Negative'
                else:
                    return 'Neutral'
            except Exception as e:
                print(f"Sentiment analysis error: {e}")
                return 'Neutral'

        def convert_datetime(dt_str):
            try:
                dt = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S%z')
                return dt.replace(tzinfo=None)
            except Exception as e:
                print(f"Datetime conversion error: {e}")
                return datetime.utcnow()

        def generate_synthetic_id(post_id, created_time, message):
            data = f"{post_id}_{created_time}_{message}"
            return hashlib.md5(data.encode()).hexdigest()

        posts_url = get_posts_url()
        print(f"Fetching posts from: {posts_url}")
        posts_response = await fetch_url(session, posts_url)
        posts = posts_response.get('data', [])

        if not posts:
            print("No posts found.")
            return

        post_tasks = []

        for post in posts:
            post_id = post.get('id')
            message = post.get('message', "")
            created_time = convert_datetime(post.get('created_time'))
            image_url = ""
            likes = post.get('likes', {}).get('summary', {}).get('total_count', 0)
            shares = post.get('shares', {}).get('count', 0)

            attachments = post.get('attachments', {}).get('data', [])
            if attachments and 'media' in attachments[0]:
                image_url = attachments[0]['media'].get('image', {}).get('src', "")

            sentiment = analyze_sentiment(message)

            print(f"Post ID: {post_id} | Sentiment: {sentiment}")

            if not db.session.query(Post).get(post_id):
                db.session.add(Post(
                    id=post_id,
                    page_id=page_id,
                    message=message,
                    created_time=created_time,
                    image_url=image_url,
                    likes=likes,
                    shares=shares,
                    sentiment=sentiment
                ))

            comments_url = get_comments_url(post_id)
            post_tasks.append(fetch_url(session, comments_url))

        comment_responses = await asyncio.gather(*post_tasks)

        for post, comments_data in zip(posts, comment_responses):
            post_id = post['id']
            comments = comments_data.get('data', [])

            for comment in comments:
                message = comment.get('message')
                created_time = convert_datetime(comment.get('created_time'))

                if not message:
                    continue

                sentiment = analyze_sentiment(message)
                comment_id = generate_synthetic_id(post_id, str(created_time), message)

                if not db.session.query(Comment).get(comment_id):
                    db.session.add(Comment(
                        id=comment_id,
                        post_id=post_id,
                        message=message,
                        created_time=created_time,
                        sentiment=sentiment
                    ))

        try:
            db.session.commit()
            print("Data fetched and stored successfully.")
        except Exception as e:
            db.session.rollback()
            print(f"Database commit error: {e}")

with app.app_context():
    db.create_all()
    page_id = '1437145013080740'
    access_token = 'EAAMQPmFBDa0BO0DZBZC1L4DGpYEKKx5K8ybibBiJnXcWOP1rtYHPNZC8ONDwmtIfQJZBIjUKbT8V3HZAj4wDpzavykU6cr47SVD1dCrEOBC0dFTjTLxRpOUIOBJrvePOk9dmTVyUjuOslqY0rOhpkwGhCmsybHsbwSawOG3dX9NMAPDvIhmJZArZAIVqPtb'
    asyncio.run(fetch_and_store_data(page_id, access_token))
