import hashlib
from extensions import db

class Tweet(db.Model):
    id = db.Column(db.String(255), primary_key=True)          # Usually IDs fit within 50 chars
    author_id = db.Column(db.String(50))
    hashtag = db.Column(db.String(100))
    text = db.Column(db.Text)                                # Text can remain Text (no length needed)
    created_time = db.Column(db.DateTime)
    likes = db.Column(db.Integer)
    retweets = db.Column(db.Integer)
    replies = db.Column(db.Integer)
    quotes = db.Column(db.Integer)
    sentiment = db.Column(db.String(20))
    media_urls = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"{self.text} ({self.sentiment})"


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'


class Post(db.Model):
    id = db.Column(db.String(255), primary_key=True)
    page_id = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=True)
    created_time = db.Column(db.DateTime, nullable=True)
    image_url = db.Column(db.String(512), nullable=True)
    likes = db.Column(db.Integer, default=0)
    shares = db.Column(db.Integer, default=0)
    sentiment = db.Column(db.String(50), nullable=True)

    def __repr__(self):
        return f'<Post {self.id}>'


class Comment(db.Model):
    id = db.Column(db.String(255), primary_key=True)
    post_id = db.Column(db.String(255), db.ForeignKey('post.id'), nullable=False)
    message = db.Column(db.Text, nullable=True)
    created_time = db.Column(db.DateTime, nullable=True)
    sentiment = db.Column(db.String(50), nullable=True)

    post = db.relationship('Post', backref=db.backref('comments', lazy=True))

    @staticmethod
    def generate_id(post_id, created_time, message):
        message_hash = hashlib.md5(message.encode('utf-8')).hexdigest()[:8]
        return f"{post_id}_{created_time}_{message_hash}"
