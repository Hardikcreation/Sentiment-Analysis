import re
from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Post, Comment
from collections import defaultdict
from sqlalchemy import func, case

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Hardik%40123@localhost/sentiment_analysis'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

# Ensure database is created before handling the first request
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_confirmation = request.form['password_confirmation']

        # Check if passwords match
        if password != password_confirmation:
            flash('Passwords do not match!')
            return redirect(url_for('signup'))

        # Validate password
        if not validate_password(password):
            flash('Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, one number, and one special character!')
            return redirect(url_for('signup'))

        if User.query.filter_by(username=username).first():
            flash('User already exists!')
        else:
            new_user = User(username=username, password_hash=generate_password_hash(password))
            db.session.add(new_user)
            db.session.commit()
            flash('Signup successful! Please login.')
            return redirect(url_for('login'))
    return render_template('signup.html')

def validate_password(password):
    """
    Validate the password against common security requirements:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one number
    - Contains at least one special character
    """
    if (len(password) >= 8 and
        re.search(r'[A-Z]', password) and
        re.search(r'[a-z]', password) and
        re.search(r'[0-9]', password) and
            re.search(r'[@$!%*?&]', password)):
        return True
    return False

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!')
    return render_template('login.html')



@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' in session:
        page_id = request.form.get('page_id', '1052601808104708')  # Default page ID if none is selected

        # Fetch posts for the selected page, ordered by created_time in descending order
        posts = Post.query.filter_by(page_id=page_id).order_by(Post.created_time.desc()).all()

        # Calculate the total number of posts
        total_posts = len(posts)

        # Dictionary to store sentiment data, comments, likes, and shares for each post
        post_sentiment_data = defaultdict(
            lambda: {'Positive': 0, 'Negative': 0, 'Neutral': 0, 'Comments': [], 'Image URL': None, 'Likes': 0, 'Shares': 0})

        sentiment_time_data = defaultdict(list)
        total_comments = 0

        for post in posts:
            post_id = post.id
            post_message = post.message
            post_created_time = post.created_time
            image_url = post.image_url
            likes = post.likes  # Assuming this is how likes are stored
            shares = post.shares  # Assuming this is how shares are stored

            comments = Comment.query.filter_by(post_id=post_id).all()
            total_comments += len(comments)

            for comment in comments:
                comment_message = comment.message
                sentiment = comment.sentiment
                post_sentiment_data[post_id]['Positive'] += sentiment == 'Positive'
                post_sentiment_data[post_id]['Negative'] += sentiment == 'Negative'
                post_sentiment_data[post_id]['Neutral'] += sentiment == 'Neutral'
                post_sentiment_data[post_id]['Comments'].append({
                    'Comment Message': comment_message,
                    'Sentiment': sentiment,
                    'Created Time': comment.created_time
                })

            # Include the image URL, likes, and shares in the post data
            post_sentiment_data[post_id]['Image URL'] = image_url
            post_sentiment_data[post_id]['Likes'] = likes
            post_sentiment_data[post_id]['Shares'] = shares

            # Collect sentiment over time data for each post
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
            username=session['username'],
            chart_data=chart_data,
            posts=posts,
            post_sentiment_data=post_sentiment_data,
            sentiment_time_data=sentiment_time_data,
            total_posts=total_posts,
            total_comments=total_comments
        )
    else:
        flash('You need to login first!')
        return redirect(url_for('login'))



@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
