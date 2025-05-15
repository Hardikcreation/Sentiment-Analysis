import os
import tweepy
import logging
from datetime import datetime, timedelta, timezone
from transformers import XLMRobertaTokenizer, AutoModelForSequenceClassification, pipeline
from deep_translator import GoogleTranslator
from dotenv import load_dotenv
from app import create_app
from models import Tweet
from extensions import db

# Load environment variables
load_dotenv()

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Twitter API
BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
if not BEARER_TOKEN:
    raise ValueError("Twitter Bearer Token is missing in .env")

client = tweepy.Client(bearer_token=BEARER_TOKEN)

# Flask App
app = create_app()

# Sentiment analysis helper

# Load the multilingual sentiment analysis model
model_name = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
tokenizer = XLMRobertaTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)

# Create a sentiment analysis pipeline
sentiment_pipeline = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)

def convert_to_sentiment(label):
    """
    Convert model output label to sentiment category.
    """
    label = label.lower()
    if label == 'negative':
        return 'Negative'
    elif label == 'neutral':
        return 'Neutral'
    elif label == 'positive':
        return 'Positive'
    else:
        return 'Neutral'

def analyze_sentiment(text):
    """
    Detect and return sentiment for a given text input.
    """
    if not text:
        return 'Neutral'
    
    try:
        # Translate to English if not already
        translated_text = GoogleTranslator(source='auto', target='en').translate(text)
        result = sentiment_pipeline(translated_text)[0]
        label = result['label']
        return convert_to_sentiment(label)
    except Exception as e:
        print(f"Error during sentiment analysis: {e}")
        return 'Neutral'


# Main tweet fetcher by date range
def get_tweets_by_hashtag(hashtag, max_results=10, start_date_str=None, end_date_str=None):
    with app.app_context():
        # Validate date input
        if not start_date_str or not end_date_str:
            logger.error("Start date and end date must be provided in 'YYYY-MM-DD' format.")
            return

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError as e:
            logger.error(f"Date format error: {e}")
            return

        if start_date > end_date:
            logger.error("Start date must be earlier than or equal to end date.")
            return

        current_date = start_date
        while current_date < end_date:
            next_date = current_date + timedelta(days=1)
            logger.info(f"Fetching tweets from {current_date.date()} to {next_date.date()}")

            try:
                query = f"#{hashtag} -is:retweet"
                tweets = client.search_recent_tweets(
                    query=query,
                    start_time=current_date.isoformat(),
                    end_time=next_date.isoformat(),
                    max_results=max_results,
                    tweet_fields=["public_metrics", "created_at", "author_id", "attachments"],
                    expansions=["attachments.media_keys"],
                    media_fields=["type", "url", "preview_image_url"]
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

                        # Check for duplicates
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
                    logger.info("No tweets found in this range.")

            except tweepy.TooManyRequests:
                logger.warning("Rate limit hit. Please retry later.")
                break
            except tweepy.TweepyException as e:
                logger.error(f"Twitter API error: {e}")
            except Exception as e:
                logger.error(f"Unexpected error: {e}")

            current_date = next_date

# Entry point
if __name__ == '__main__':
    get_tweets_by_hashtag(
        hashtag="IStandwithSharmishta",
        max_results=10,
        start_date_str="2025-05-09",
        end_date_str="2025-05-15"  # End date is exclusive 
    )
