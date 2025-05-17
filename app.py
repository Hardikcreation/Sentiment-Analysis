from flask import Flask, render_template, request
from flask_migrate import Migrate
from dotenv import load_dotenv
from sqlalchemy import func, case
from collections import defaultdict, Counter
from extensions import db
from models import Post, Comment, Tweet

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Hardik%40123@localhost/tweet'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Init extensions
db.init_app(app)
migrate = Migrate(app, db)

# Ensure database is created before handling requests
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    page_id = request.form.get('page_id', '1052601808104708')

    posts = Post.query.filter_by(page_id=page_id).order_by(Post.created_time.desc()).all()
    total_posts = len(posts)

    post_sentiment_data = defaultdict(
        lambda: {'Positive': 0, 'Negative': 0, 'Neutral': 0, 'Comments': [], 'Image URL': None, 'Likes': 0, 'Shares': 0})
    sentiment_time_data = defaultdict(list)
    total_comments = 0
    total_likes = 0
    total_shares = 0

    for post in posts:
        post_id = post.id
        image_url = post.image_url
        likes = post.likes
        shares = post.shares

        total_likes += likes
        total_shares += shares

        comments = Comment.query.filter_by(post_id=post_id).all()
        total_comments += len(comments)

        for comment in comments:
            sentiment = comment.sentiment
            post_sentiment_data[post_id][sentiment] += 1
            post_sentiment_data[post_id]['Comments'].append({
                'Comment Message': comment.message,
                'Sentiment': sentiment,
                'Created Time': comment.created_time
            })

        post_sentiment_data[post_id]['Image URL'] = image_url
        post_sentiment_data[post_id]['Likes'] = likes
        post_sentiment_data[post_id]['Shares'] = shares

        time_data = Comment.query.with_entities(
            func.date(Comment.created_time).label('created_time'),
            func.sum(case((Comment.sentiment == 'Positive', 1), else_=0)).label('Positive'),
            func.sum(case((Comment.sentiment == 'Negative', 1), else_=0)).label('Negative'),
            func.sum(case((Comment.sentiment == 'Neutral', 1), else_=0)).label('Neutral')
        ).filter_by(post_id=post_id).group_by(func.date(Comment.created_time)).all()

        for entry in time_data:
            sentiment_time_data[post_id].append({
                'created_time': entry.created_time,
                'Positive': entry.Positive,
                'Negative': entry.Negative,
                'Neutral': entry.Neutral
            })

    chart_data = [{'post_id': post_id, 'Positive': data['Positive'], 'Negative': data['Negative'], 'Neutral': data['Neutral']}
                    for post_id, data in post_sentiment_data.items()]

    return render_template(
        'dashboard.html',
        chart_data=chart_data,
        posts=posts,
        post_sentiment_data=post_sentiment_data,
        sentiment_time_data=sentiment_time_data,
        total_posts=total_posts,
        total_comments=total_comments,
        total_likes=total_likes,
        total_shares=total_shares
    )

@app.route('/tweets', methods=['GET'])
def tweet_analysis():
    search_query = request.args.get('search', '').strip()
    if search_query:
        tweets = Tweet.query.filter(
            (Tweet.hashtag.ilike(f'%{search_query}%')) |
            (Tweet.author_id.ilike(f'%{search_query}%'))
        ).order_by(Tweet.created_time.desc()).all()
    else:
        tweets = Tweet.query.order_by(Tweet.created_time.desc()).all()

    positive = sum(1 for tweet in tweets if tweet.sentiment == 'Positive')
    neutral = sum(1 for tweet in tweets if tweet.sentiment == 'Neutral')
    negative = sum(1 for tweet in tweets if tweet.sentiment == 'Negative')

    sentiment_data = {
        'positive': positive,
        'neutral': neutral,
        'negative': negative
    }

    hashtags = [tweet.hashtag for tweet in tweets if tweet.hashtag]
    hashtag_counter = Counter(hashtags)
    sorted_hashtags = sorted(hashtag_counter.items(), key=lambda x: x[1], reverse=True)
    hashtag_labels = [item[0] for item in sorted_hashtags]
    hashtag_counts = [item[1] for item in sorted_hashtags]

    serialized_tweets = [{
        'id': tweet.id,
        'author_id': tweet.author_id,
        'hashtag': tweet.hashtag,
        'text': tweet.text,
        'created_time': tweet.created_time.strftime('%Y-%m-%d %H:%M'),
        'likes': tweet.likes,
        'retweets': tweet.retweets,
        'replies': tweet.replies,
        'quotes': tweet.quotes,
        'sentiment': tweet.sentiment,
        'media_urls': tweet.media_urls
    } for tweet in tweets]

    return render_template(
        'tweets.html',
        tweets=tweets,
        sentiment_data=sentiment_data,
        hashtag_labels=hashtag_labels,
        hashtag_counts=hashtag_counts,
        serialized_tweets=serialized_tweets,
        time_labels=[],  # Optional placeholder
        time_counts=[]
    )

if __name__ == '__main__':
    app.run(debug=True)
