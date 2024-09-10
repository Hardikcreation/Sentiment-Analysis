from flask import Flask, render_template, redirect, url_for, request, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
import requests
import json
from textblob import TextBlob
from collections import defaultdict
from googletrans import Translator

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Ensure database is created before handling the first request
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('User already exists!')
        else:
            new_user = User(username=username, password_hash=generate_password_hash(password))
            db.session.add(new_user)
            db.session.commit()
            flash('Signup successful! Please login.')
            return redirect(url_for('login'))
    return render_template('signup.html')

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

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        # Define the page ID and access token
        page_id = '1448364408720250'
        access_token = 'EAAMQPmFBDa0BO3iQZCRH7nx9mmXUaCZCBON79P1hKOSZCp5BEl68ZC9RESabtBHZBZABts14GEXSy1Ev4FQhUCwQR35JkRgJp2GztuKNZBbucn9K5x9Tpvl5GOlpARyW6wQyBEaZAnDFSfNX27wU8zNHdHXA5ZCDlMI2AlZA1XiNEWO47Ur9ZA1YCea3TuLtIO9deRRbqLW48pec1ek'

        # Function to get posts from the page
        def get_posts(page_id, access_token):
            url = f"https://graph.facebook.com/v20.0/{page_id}/posts?limit=5&access_token={access_token}"
            response = requests.get(url)
            data = json.loads(response.text)
            return data.get('data', [])

        # Function to get comments for a specific post
        def get_comments(post_id, access_token):
            url = f"https://graph.facebook.com/v20.0/{post_id}/comments?limit=5&access_token={access_token}"
            response = requests.get(url)
            data = json.loads(response.text)
            return data.get('data', [])

        # Function to analyze sentiment and classify it
        def analyze_sentiment(text):
            if not text:
                return 'Neutral'  # Return default sentiment if text is None or empty

            translator = Translator()
            try:
                # Detect the language of the text
                lang = translator.detect(text).lang

                # Translate the text to English if it is in Hindi
                if lang == 'hi':
                    text = translator.translate(text, src='hi', dest='en').text

                # Perform sentiment analysis
                analysis = TextBlob(text)
                polarity = analysis.sentiment.polarity
                if polarity > 0:
                    return 'Positive'
                elif polarity < 0:
                    return 'Negative'
                else:
                    return 'Neutral'

            except Exception as e:
                print(f"Error during sentiment analysis: {e}")
                return 'Neutral'  # Return default sentiment in case of error

        posts = get_posts(page_id, access_token)
        post_sentiment_data = defaultdict(lambda: {'Positive': 0, 'Negative': 0, 'Neutral': 0, 'Comments': []})

        for post in posts:
            post_id = post.get('id', 'No ID')
            post_message = post.get('message', 'No message')
            post_created_time = post.get('created_time', 'No time')
            comments = get_comments(post_id, access_token)

            for comment in comments:
                comment_message = comment.get('message', 'No message')
                sentiment = analyze_sentiment(comment_message)
                post_sentiment_data[post_id]['Positive'] += sentiment == 'Positive'
                post_sentiment_data[post_id]['Negative'] += sentiment == 'Negative'
                post_sentiment_data[post_id]['Neutral'] += sentiment == 'Neutral'
                post_sentiment_data[post_id]['Comments'].append({
                    'Comment Message': comment_message,
                    'Sentiment': sentiment,
                    'Created Time': comment.get('created_time', 'No time')
                })

        # Prepare data for the chart
        chart_data = []
        for post_id, data in post_sentiment_data.items():
            chart_data.append({
                'post_id': post_id,
                'Positive': data['Positive'],
                'Negative': data['Negative'],
                'Neutral': data['Neutral']
            })

        return render_template('dashboard.html', username=session['username'], chart_data=chart_data, posts=posts, post_sentiment_data=post_sentiment_data)
    else:
        flash('You need to login first!')
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
