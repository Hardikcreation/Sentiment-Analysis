import os
from dotenv import load_dotenv
from flask import Flask
from flask_migrate import Migrate
import tweepy
import logging
from datetime import datetime
from transformers import XLMRobertaTokenizer, AutoModelForSequenceClassification, pipeline
from deep_translator import GoogleTranslator
from extensions import db
from models import Tweet

# Load environment variables from .env file
load_dotenv()

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Twitter API
BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
if not BEARER_TOKEN:
    raise ValueError("Twitter Bearer Token is missing in .env")

client = tweepy.Client(bearer_token=BEARER_TOKEN)

# Flask App
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback-secret")

# Database Config
DB_URI = f"mysql+pymysql://{os.getenv('DB_USERNAME')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Init extensions
db.init_app(app)
migrate = Migrate(app, db)

# Ensure DB tables are created
with app.app_context():
    db.create_all()

# Load the sentiment model
model_name = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
tokenizer = XLMRobertaTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)
sentiment_pipeline = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)

def convert_to_sentiment(label):
    label = label.lower()
    if label == 'negative':
        return 'Negative'
    elif label == 'neutral':
        return 'Neutral'
    elif label == 'positive':
        return 'Positive'
    return 'Neutral'

def analyze_sentiment(text):
    if not text:
        return 'Neutral'
    try:
        translated_text = GoogleTranslator(source='auto', target='en').translate(text)
        result = sentiment_pipeline(translated_text)[0]
        return convert_to_sentiment(result['label'])
    except Exception as e:
        logger.error(f"Sentiment analysis error: {e}")
        return 'Neutral'

def get_tweets_by_hashtag(hashtag, max_results=10, start_date=None, end_date=None):
    with app.app_context():
        logger.info(f"Fetching recent tweets with hashtag #{hashtag}")

        try:
            query = f"#{hashtag} -is:retweet"
            tweets = client.search_recent_tweets(
                query=query,
                max_results=max_results,
                tweet_fields=["public_metrics", "created_at", "author_id", "attachments"],
                expansions=["attachments.media_keys"],
                media_fields=["type", "url", "preview_image_url"],
                start_time=start_date,
                end_time=end_date
            )

            media_dict = {}
            if tweets.includes and "media" in tweets.includes:
                media_dict = {media.media_key: media for media in tweets.includes["media"]}

            if tweets.data:
                for tweet in tweets.data:
                    tweet_id = str(tweet.id)
                    author_id = str(tweet.author_id)
                    text = tweet.text
                    created_time = tweet.created_at
                    metrics = tweet.public_metrics or {}
                    sentiment = analyze_sentiment(text)

                    media_urls = []
                    if hasattr(tweet, "attachments") and tweet.attachments:
                        media_keys = tweet.attachments.get("media_keys", [])
                        for key in media_keys:
                            media = media_dict.get(key)
                            if media:
                                if media.type == "photo" and hasattr(media, "url"):
                                    media_urls.append(media.url)
                                elif media.type in ["video", "animated_gif"] and hasattr(media, "preview_image_url"):
                                    media_urls.append(media.preview_image_url)

                    existing_tweet = Tweet.query.get(tweet_id)
                    if not existing_tweet:
                        new_tweet = Tweet(
                            id=tweet_id,
                            author_id=author_id,
                            hashtag=hashtag,
                            text=text,
                            created_time=created_time,
                            likes=metrics.get('like_count', 0),
                            retweets=metrics.get('retweet_count', 0),
                            replies=metrics.get('reply_count', 0),
                            quotes=metrics.get('quote_count', 0),
                            sentiment=sentiment,
                            media_urls=", ".join(media_urls) if media_urls else None
                        )
                        db.session.add(new_tweet)
                        logger.info(f"Stored Tweet: {tweet_id} with media: {media_urls}")
                    else:
                        logger.info(f"Tweet {tweet_id} already exists. Skipping.")

                db.session.commit()
                logger.info("Tweets stored successfully.")
            else:
                logger.info("No tweets found.")

        except tweepy.TooManyRequests:
            logger.warning("Rate limit hit. Please retry later.")
        except tweepy.TweepyException as e:
            logger.error(f"Twitter API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

# Entry Point
if __name__ == '__main__':
    start_date = datetime(2025, 5, 15, 0, 0, 0).isoformat("T") + "Z"
    end_date = datetime(2025, 5, 19, 23, 59, 59).isoformat("T") + "Z"
    get_tweets_by_hashtag(
        hashtag="ipl",
        max_results=12,
        start_date=start_date,
        end_date=end_date
    )
