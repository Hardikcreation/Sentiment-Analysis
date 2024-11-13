import hashlib
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

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
    created_time = db.Column(db.DateTime, nullable=True)  # Ensure datetime format
    image_url = db.Column(db.String(512), nullable=True)  # Field for image URL
    likes = db.Column(db.Integer, default=0)              # New field for likes
    shares = db.Column(db.Integer, default=0)             # New field for shares
    sentiment = db.Column(db.String(50), nullable=True)    # New field for post sentiment

    def __repr__(self):
        return f'<Post {self.id}>'


class Comment(db.Model):
    id = db.Column(db.String(255), primary_key=True)  # Synthetic ID
    post_id = db.Column(db.String(255), db.ForeignKey('post.id'), nullable=False)
    message = db.Column(db.Text, nullable=True)
    created_time = db.Column(db.DateTime, nullable=True)
    sentiment = db.Column(db.String(50), nullable=True)
    
    post = db.relationship('Post', backref=db.backref('comments', lazy=True))
    
    @staticmethod
    def generate_id(post_id, created_time, message):
        # Create a unique ID based on post_id, created_time, and a hash of the message
        message_hash = hashlib.md5(message.encode('utf-8')).hexdigest()[:8]  # Hash first 8 chars of message
        return f"{post_id}_{created_time}_{message_hash}"
