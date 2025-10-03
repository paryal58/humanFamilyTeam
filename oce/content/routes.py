from flask import Blueprint, render_template, send_file, request, jsonify, redirect, url_for, flash, session
from oce.utils.db_interface import create_post, get_post_by_uuid
from oce.utils.models import User
from flask_dance.contrib.github import github, make_github_blueprint
from flask_dance.consumer.storage.session import BaseStorage
from dotenv import load_dotenv
load_dotenv()
import os

class SessionStorage(BaseStorage):
    def __init__(self, session_key="flask_dance_token"):
        super().__init__()
        self.session_key = session_key

    def get(self, blueprint):
        print("Getting token from session:", session.get(self.session_key))
        return session.get(self.session_key)

    def set(self, blueprint, token):
        print("Setting token in session:", token)
        if isinstance(token, str):  # Handle legacy string just in case
            token = {"access_token": token}
        session[self.session_key] = token

    def delete(self, blueprint):
        print("Deleting token from session")
        session.pop(self.session_key, None)

content = Blueprint('content', __name__)

ADMINS = os.getenv('ADMINS', '').split(',')

# github_blueprint = make_github_blueprint(
#     client_id=os.getenv('GITHUB_OAUTH_CLIENT_ID'),
#     client_secret=os.getenv('GITHUB_OAUTH_CLIENT_SECRET'),
#     scope='user',
#     redirect_url="/github_callback",
#     storage=SessionStorage()
# 
# content.register_blueprint(github_blueprint, url_prefix='/github_login')

@content.route('/content/block1')
def block1():
    return render_template('block1.html')

@content.route('/content/block2')
def block2():
    return render_template('block2.html')

@content.route('/content/block3')
def block3():
    return render_template('block3.html')

@content.route('/content/block4')
def block4():
    return render_template('block4.html')

@content.route('/content/block5')
def block5():
    return render_template('block5.html')

@content.route('/content/block6')
def block6():
    return render_template('block6.html')

@content.route('/content/block7')
def block7():
    return render_template('block7.html')

@content.route('/content/block8')
def block8():
    return render_template('block8.html')

@content.route('/content/block9')
def block9():
    return render_template('block9.html')

@content.route('/content/tiles/')
def tiles():
    return send_file('static/docs/Human-Domino-Effect-Footprint-Tiles.pdf', download_name='Human-Domino-Effect-Footprint-Tiles.pdf')

@content.route('/content/ConceptExchange/')
def concept_exchange():
    from oce.utils.db_interface import get_all_posts
    
    try:
        # Fetch all posts from the database
        posts = get_all_posts()
        return render_template('mainForum.html', posts=posts)
    except Exception as e:
        print(f"Error fetching posts: {e}")
        return render_template('mainForum.html', posts=[])

@content.route('/content/resources/<selected_age>')
def resources(selected_age):
    return render_template('resources.html', selected_age=selected_age)

@content.route('/content/Login/')
def login():
    return render_template('LoginPage.html')

@content.route('/content/calendar/')
def calendar():
    return render_template('calendar.html')

@content.route('/content/Contact/')
def contact():
    return render_template('ContactPage.html')

@content.route('/content/Shop/')
def shop():
    return render_template('Shop.html')

@content.route('/content/Cart/')
def cart():
    return render_template('Cart.html')

@content.route('/create_post', methods=['POST'])
def create_post_route():
    data = request.get_json()  # Get JSON data from the request
    text_content = data.get('text_content')  # Extract the post content
    username = data.get('username')

    if not text_content:
        return jsonify({'success': False, 'error': 'Text content is required.'}), 400

    try:
        # create_post(author=User(user_uuid="example", username="name", email="example@email.com", password="password", profile_pic=b"", about_me=''), text_content=text_content, tag1='', tag2='', tag3='', tag4='', tag5='', datetime='', location='', image=None)
        create_post(author=username, text_content=text_content)  # this should be updated when the user login feature is added to look more like the one above this line
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# @content.route('/github_login')
# def github_login():
#     if not github.authorized:
#         return redirect(url_for("github.login"))  # this triggers OAuth flow

#     resp = github.get("/user")
#     if not resp.ok:
#         flash("Failed to fetch user info.", "error")
#         return redirect(url_for("content.login"))

#     username = resp.json()["login"]
#     session["user"] = username
#     flash(f"Logged in as {username}", "success")

#     if username in ADMINS:
#         return redirect(url_for("content.admin_dashboard"))

#     return redirect(url_for("content.index"))

# @content.route("/github_test")
# def github_test():
#     print("Authorized:", github.authorized)
#     print("Token:", github.token)
#     return "Check terminal"

# @content.route('/admin')
# def admin_dashboard():
#     if 'user' not in session or session['user'] not in ADMINS:
#         return "Unauthorized", 403
#     return render_template('admin_dashboard.html')

# @content.route('/logout')
# def logout():
#     session.pop('user', None)
#     session.pop('flask_dance_token', None)  # Clear the OAuth token
#     flash("You have been logged out.", "success")
#     return redirect(url_for('content.index'))

@content.route('/')
def index():
    return render_template('index.html')