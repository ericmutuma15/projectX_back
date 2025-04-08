import os
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory, url_for, Blueprint
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from flask_migrate import Migrate
from flask_jwt_extended import (jwt_required,
                                get_jwt_identity, 
                                JWTManager, 
                                create_access_token,
                                 set_access_cookies, 
                                 create_refresh_token, 
                                 set_refresh_cookies,
                                 unset_jwt_cookies)
from werkzeug.utils import secure_filename
from sqlalchemy.orm import joinedload
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from config import Config

app = Flask(__name__, static_folder="static")
app.config.from_object(Config)

# Enable Cross-Origin Resource Sharing for React Frontend
CORS(app, resources={
    r"/*": {"origins": "*"},
    r"/api/*": {"origins": ["http://127.0.0.1:5173", "http://localhost:5173", "https://projectx-back.onrender.com"]},
    r"/static/images/*": {"origins": "*"},
    r"/static/sidebar_images/*": {"origins": "*"},
    r"/static/uploads/*": {"origins": "*"}
}, supports_credentials=True, 
allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Origin"], 
methods=["GET", "POST", "OPTIONS"])
socketio = SocketIO(app, cors_allowed_origins="*")
messages_bp = Blueprint('messages', __name__)

# JWT Configuration
jwt = JWTManager(app)
app.config["JWT_SECRET_KEY"] = os.urandom(24)  # Secure random key
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_COOKIE_CSRF_PROTECT"] = False  # Disable CSRF for testing
app.config["JWT_ACCESS_COOKIE_NAME"] = "access_token"
app.config["JWT_REFRESH_COOKIE_NAME"] = "refresh_token"
app.config["JWT_COOKIE_SECURE"] = True  # Set to True in production
app.config["JWT_HEADER_NAME"] = "Authorization"
app.config["JWT_HEADER_TYPE"] = "Bearer"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=24)  # Access token expiration
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)  # Refresh token expiration
app.config['JWT_COOKIE_SAMESITE'] = 'None'  # 'Strict' or 'Lax' based on your needs
app.config['JWT_ACCESS_COOKIE_PATH'] = '/'  # Path for the access token cookie
app.config['JWT_REFRESH_COOKIE_PATH'] = '/'  # Path for the refresh token cookie
# Database Configuration
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Initialize extensions
db = SQLAlchemy(app)
mail = Mail(app)
migrate = Migrate(app, db)
#social_bp = Blueprint('social', __name__)

# Serializer for secure tokens
serializer = URLSafeTimedSerializer(app.config["JWT_SECRET_KEY"])

# Import models
from models import User, Message, FriendRequest, Post, Like, Comment, Notification, Friendship

# Utility to check file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Routes
@app.route('/')
def home():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    if not path.startswith('api/'):
        return send_from_directory(app.static_folder, 'index.html')
    return send_from_directory(app.static_folder, path)

# Refresh token endpoint
@app.route('/api/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user = get_jwt_identity()
    new_token = create_access_token(identity=current_user, expires_delta=timedelta(hours=24))
    response = jsonify({"message": "Token refreshed"})
    set_access_cookies(response, new_token)
    return response


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if User.query.filter_by(email=email).first():
        return jsonify({"message": "Email already registered"}), 400

    hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
    # Make super user for the specific email
    is_super_user = True if email == "ericmutuma15@gmail.com" else False
    new_user = User(name=name, email=email, password=hashed_password, is_super_user=is_super_user)

    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "User registered successfully"}), 201
    except Exception as e:
        return jsonify({"message": "Registration failed", "error": str(e)}), 500
    


import logging

# Enable logging for debugging
logging.basicConfig(level=logging.DEBUG)

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()

    # Validate email and password
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    # Retrieve the user
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({"message": "Invalid email or password"}), 401

    # Generate access and refresh tokens
    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)

    # Set cookies with proper properties
    response = jsonify({"message": "Login successful"})
    set_access_cookies(response, access_token, max_age=timedelta(hours=1))
    set_refresh_cookies(response, refresh_token, max_age=timedelta(days=30))

    return response, 200

@app.route("/api/google-login", methods=["POST"])
def google_login():
    data = request.get_json()
    email = data.get("email")

    # Check if the user exists
    user = User.query.filter_by(email=email).first()

    if user:
        # Generate access and refresh tokens
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)

        # Set cookies with proper properties
        response = jsonify({"message": "Login successful"})
        set_access_cookies(response, access_token, max_age=timedelta(hours=1), secure=True, samesite="Lax")
        set_refresh_cookies(response, refresh_token, max_age=timedelta(days=30), secure=True, samesite="Lax")
        print(response.headers)

        return response, 200
    else:
        logging.error(f"User with email {email} not registered")
        return jsonify({"message": "Email not registered"}), 404

    
@app.route("/api/logout", methods=["POST"])
def logout():
    response = jsonify({"message": "Logout successful"})
    unset_jwt_cookies(response)
    return response, 200



#serve images

@app.route('/static/<filename>')
def serve_image(filename):
    return send_from_directory(os.path.join(app.root_path, 'static/images'), filename)

@app.route('/<filename>')
def static_files(filename):
    return send_from_directory(os.path.join(app.root_path, 'static/uploads'), filename)

@app.route('/static/sidebar_images/<filename>')
def serve_sidebar_image(filename):
    return send_from_directory(os.path.join(app.root_path, 'static/sidebar_images'), filename)

@app.route("/api/token", methods=["GET"])
@jwt_required(refresh=True)
def refresh_token():
    try:
        # Extract the identity from the refresh token
        current_user = get_jwt_identity()

        # Generate a new access token
        access_token = create_access_token(identity=current_user)
        
        # Set the new access token in the cookie
        response = {"access_token": access_token}
        response.set_cookie(
            app.config["JWT_ACCESS_COOKIE_NAME"],
            access_token,
            httponly=True,
            secure=app.config["JWT_COOKIE_SECURE"],  # Ensure this is False in development
            samesite="Lax",
            max_age=24 * 60 * 60  # 24 hours
        )

        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/users", methods=["GET"])
@jwt_required()
def get_users():
    try:
        current_user_id = get_jwt_identity()

        # Get friend IDs in both directions (since friendships are mutual)
        friend_ids_query1 = db.session.query(Friendship.friend_id).filter(Friendship.user_id == current_user_id)
        friend_ids_query2 = db.session.query(Friendship.user_id).filter(Friendship.friend_id == current_user_id)
        friend_ids = friend_ids_query1.union(friend_ids_query2).all()
        friend_ids = {fid[0] for fid in friend_ids}  # Convert list of tuples to a set

        # Query for users who are not the current user and not in the friend IDs
        users = User.query.filter(
            User.id != current_user_id,
            ~User.id.in_(friend_ids)
        ).all()

        # Build the response list with the desired fields
        user_list = [{
            'id': user.id,
            'name': user.name,
            'description': user.description,
            'location': user.location,
            'picture': user.picture,
        } for user in users]

        return jsonify(user_list), 200

    except Exception as e:
        return jsonify({"error": f"Error fetching users: {str(e)}"}), 500
    
    
@app.route("/api/current_user", methods=["GET"])
@jwt_required()  # JWT Authentication will automatically check the cookies
def get_current_user():
    try:
        # Get user ID from JWT token (extracted from the cookies)
        current_user_id = get_jwt_identity()
        app.logger.info(f"Current user ID: {current_user_id}")

        # Check if the token is valid and has a valid user ID
        if not current_user_id:
            return jsonify({"error": "Invalid token"}), 422

        # Fetch the user from the database
        user = User.query.filter_by(id=current_user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        # If the user has a picture, generate a URL for it
        picture_url = (
            url_for('serve_image', filename=user.picture, _external=True)
            if user.picture else None
        )

        # Send the user data as a JSON response
        data = {
            'id': user.id,
            'name': user.name,
            'description': user.description,
            'location': user.location,
            'picture': picture_url,
        }
        return jsonify(data), 200
    except Exception as e:
        app.logger.error(f"Error fetching user data: {str(e)}")
        return jsonify({"error": f"Error fetching user data: {str(e)}"}), 500

#end point to get user posts
@app.route("/api/user_posts/<int:user_id>", methods=["GET"])
@jwt_required()
def get_user_posts(user_id):
    try:
        # Query posts made by the selected user
        posts = Post.query.filter_by(user_id=user_id).order_by(Post.timestamp.desc()).all()

        # Serialize post data
        post_data = [
            {
                "id": post.id,
                "content": post.content,
                "media_url": (
                    url_for('static_files', filename=post.media_url, _external=True)
                    if post.media_url else None
                ),
                "timestamp": post.timestamp.isoformat(),  # Convert to ISO format for JSON
                "like_count": post.like_count(),
                "user": {
                    "id": post.user.id,
                    "name": post.user.name,
                    "user_photo": (
                        url_for('serve_image', filename=post.user.picture, _external=True)
                        if post.user.picture else None
                    ),
                },
            }
            for post in posts
        ]

        return jsonify({"posts": post_data}), 200
    except Exception as e:
        return jsonify({"error": f"Error fetching posts: {str(e)}"}), 500

@app.route("/api/user_posts", methods=["GET"])
@jwt_required()
def get_current_user_posts():
    try:
        # Get the logged-in user's ID
        current_user_id = get_jwt_identity()

        # Query posts made by the logged-in user
        posts = Post.query.filter_by(user_id=current_user_id).order_by(Post.timestamp.desc()).all()

        # Serialize post data
        post_data = [
            {
                "id": post.id,
                "content": post.content,
                "media_url": (
                    url_for('static_files', filename=post.media_url, _external=True)
                    if post.media_url else None
                ),
                "timestamp": post.timestamp.isoformat(),  # Convert to ISO format for JSON
                "like_count": post.like_count(),
                "user": {
                    "id": post.user.id,
                    "name": post.user.name,
                    "user_photo": (
                        url_for('serve_image', filename=post.user.picture, _external=True)
                        if post.user.picture else None
                    ),
                },
            }
            for post in posts
        ]

        return jsonify({"posts": post_data}), 200
    except Exception as e:
        return jsonify({"error": f"Error fetching posts: {str(e)}"}), 500



@app.route('/api/profile', methods=['POST'])
@jwt_required()
def update_profile():
    try:
        current_user_id = get_jwt_identity()
        name = request.form.get('name')
        description = request.form.get('description')
        location = request.form.get('location')
        picture = request.files.get('picture')

        if not name or not description or not location or not picture:
            return jsonify({'error': 'All fields are required'}), 400

        user = User.query.get(current_user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        upload_folder = app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        if picture and allowed_file(picture.filename):
            filename = secure_filename(picture.filename)
            image_path = os.path.join(upload_folder, filename)
            picture.save(image_path)
            user.picture = f'images/{filename}'

        user.name = name
        user.description = description
        user.location = location

        db.session.commit()
        return jsonify({'message': 'Profile updated successfully'}), 200
    except Exception as e:
        app.logger.error(f"Error updating profile: {str(e)}")
        return jsonify({'error': f'Error updating profile: {str(e)}'}), 500

@app.route('/api/posts', methods=['POST'])
@jwt_required()
def create_post():
    try:
        current_user_id = get_jwt_identity()
        form_data = request.form.to_dict(flat=True)
        media = request.files.get('media')

        content = form_data.get('content')
        media_url = None

        uploads_folder = os.path.join(app.root_path, 'static/uploads')
        if not os.path.exists(uploads_folder):
            os.makedirs(uploads_folder)

        if media:
            media_filename = secure_filename(media.filename)
            media.save(os.path.join(uploads_folder, media_filename))
            media_url = f'/static/uploads/{media_filename}'

        if not content and not media_url:
            return jsonify({"error": "Content or media_url is required"}), 400

        post = Post(
            content=content,
            media_url=media_url,
            user_id=current_user_id,
            timestamp=datetime.utcnow()
        )
        db.session.add(post)
        db.session.commit()

        return jsonify({"message": "Post created", "post_id": post.id}), 201
    except Exception as e:
        app.logger.error(f"Error creating post: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Get posts with comments
@app.route('/api/feeds', methods=['GET'])
def get_all_posts():
    posts = Post.query.options(joinedload(Post.user)).order_by(Post.timestamp.desc()).all()
    response = [{
        'id': post.id,
        'user_id': post.user_id,
        'user_name': post.user.name if post.user else "Unknown",
        'user_photo': post.user.picture if post.user and post.user.picture else None,
        'content': post.content,
        'media_url': post.media_url,
        'timestamp': post.timestamp.isoformat(),
        'comments': [{
            'id': comment.id,
            'content': comment.content,
            'user_name': comment.user.name if comment.user else "Unknown",
            'user_photo': comment.user.picture if comment.user and comment.user.picture else None,
            'timestamp': comment.timestamp.isoformat()
        } for comment in post.comments]
    } for post in posts]
    return jsonify(response), 200


@app.route('/api/posts/<int:post_id>/like', methods=['POST'])
@jwt_required()
def like_post(post_id):
    try:
        user_id = get_jwt_identity()  # Get user ID from the token
        post = Post.query.get(post_id)
        
        if not post:
            return jsonify({"error": "Post not found"}), 404
        
        # Check if the user already liked the post
        existing_like = Like.query.filter_by(user_id=user_id, post_id=post_id).first()
        if existing_like:
            # If the user already liked the post, remove the like
            db.session.delete(existing_like)
            db.session.commit()
            return jsonify({"message": "Like removed", "likes": post.like_count()})
        
        # If the user hasn't liked the post yet, add a like
        new_like = Like(user_id=user_id, post_id=post_id)
        db.session.add(new_like)
        db.session.commit()

        return jsonify({"message": "Post liked", "likes": post.like_count()})
    
    except Exception as e:
        print(f"Error in like_post: {e}")
        db.session.rollback()
        return jsonify({"error": "Internal Server Error"}), 500

# New endpoint to add a comment
@app.route('/api/posts/<int:post_id>/comments', methods=['POST'])
@jwt_required()
def add_comment(post_id):
    try:
        user_id = get_jwt_identity()
        print(f"JWT Identity: {user_id}")  # Debugging

        if not user_id:
            return jsonify({"error": "Unauthorized: No valid token"}), 401

        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

        comment_content = request.json.get('content')
        if not comment_content:
            return jsonify({"error": "Comment content is required"}), 400

        new_comment = Comment(content=comment_content, user_id=user_id, post_id=post.id)
        db.session.add(new_comment)
        db.session.commit()

        return jsonify({
            "id": new_comment.id,
            "content": new_comment.content,
            "user_name": new_comment.user.name,  
            "user_photo": new_comment.user.picture,  
            "timestamp": new_comment.timestamp.isoformat()
        }), 201

    except Exception as e:
        print(f"Error in add_comment: {e}")
        db.session.rollback()
        return jsonify({"error": "Internal Server Error"}), 500
    

# New endpoint to get comments for a specific post
@app.route('/api/posts/<int:post_id>/comments', methods=['GET'])
def get_comments(post_id):
    try:
        # Fetch comments for the post
        post = Post.query.get(post_id)

        if not post:
            return jsonify({"error": "Post not found"}), 404

        comments = Comment.query.filter_by(post_id=post_id).all()

        comments_data = [{
            'id': comment.id,
            'content': comment.content,
            'user_name': comment.user.name,  
            'timestamp': comment.timestamp.isoformat(),
        } for comment in comments]

        return jsonify(comments_data), 200

    except Exception as e:
        print(f"Error in get_comments: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# Upload route for sidebar images
@app.route("/api/upload_sidebar_image", methods=["POST"])
@jwt_required()
def upload_sidebar_image():
    try:
        # Fetch current user from JWT token
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)

        if not current_user:
            return jsonify({"error": "User not found"}), 404

        # Only super user can upload images
        if current_user.email != "ericmutuma15@gmail.com":
            return jsonify({"error": "You are not authorized to upload images"}), 403

        # Process the image upload
        image = request.files.get("image")
        if not image or not allowed_file(image.filename):
            return jsonify({"error": "No image provided or invalid format"}), 400

        filename = secure_filename(image.filename)
        # Create folder if it does not exist
        if not os.path.exists(app.config["UPLOAD_FOLDER"]):
            os.makedirs(app.config["UPLOAD_FOLDER"])

        # Save image to the folder
        image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        # Save image URL to return
        image_url = f"/static/sidebar_images/{filename}"

        return jsonify({"message": "Image uploaded successfully", "image_url": image_url}), 201

    except Exception as e:
        app.logger.error(f"Error uploading image: {str(e)}")
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500


# Define the allowed file extensions
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/api/sidebar_images", methods=["GET"])
def get_sidebar_images():
    try:
        # Define the folder path
        folder_path = os.path.join(app.root_path, "static", "sidebar_images")
        
        # Ensure the folder exists
        if not os.path.exists(folder_path):
            return jsonify({"error": "Sidebar images folder not found"}), 404
        
        # List all allowed image files in the directory
        files = [f for f in os.listdir(folder_path) if allowed_file(f)]

        if not files:
            return jsonify({"error": "No images found in the sidebar folder"}), 404

        # Construct response with filenames and URLs
        images = [
            {
                "filename": filename,
                "url": url_for('serve_sidebar_image', filename=filename, _external=True),
                "title": os.path.splitext(filename)[0]  # Use filename (without extension) as a placeholder title
            }
            for filename in files
        ]

        return jsonify(images), 200

    except Exception as e:
        app.logger.error(f"Error fetching sidebar images: {str(e)}")
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500

#endpoint to send friend request
@app.route('/api/send-friend-request', methods=['POST'])
@jwt_required()
def send_friend_request():
    data = request.get_json()
    recipient_id = data.get("userId")  # Ensure frontend sends the correct key

    if not recipient_id:
        return jsonify({"error": "Recipient ID is required"}), 400

    current_user_id = get_jwt_identity()

    if current_user_id == recipient_id:
        return jsonify({"error": "You cannot send a request to yourself"}), 400

    existing_request = FriendRequest.query.filter_by(
        requester_id=current_user_id,
        recipient_id=recipient_id,
        status="pending"
    ).first()

    if existing_request:
        return jsonify({"error": "Friend request already sent"}), 400

    # Save the friend request
    friend_request = FriendRequest(
        requester_id=current_user_id,
        recipient_id=recipient_id,
        status="pending"
    )
    db.session.add(friend_request)
    db.session.commit()  # Commit to generate friend_request.id

    # Create a notification for the recipient, linking to the friend request
    notification = Notification(
        user_id=recipient_id,
        message="You have a new friend request!",
        type="friend_request",
        friend_request_id=friend_request.id  # Store request ID for reference
    )
    db.session.add(notification)
    db.session.commit()

    return jsonify({"message": "Friend request sent!"}), 201



@app.route("/api/user/<int:user_id>", methods=["GET"])
@jwt_required()
def get_user_by_id(user_id):
    try:
        # Get the ID of the currently authenticated user
        current_user_id = get_jwt_identity()

        # Fetch the user from the database
        user = User.query.get(user_id)

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Check if the logged-in user and the requested user are friends
        is_friend = Friendship.query.filter(
            ((Friendship.user_id == current_user_id) & (Friendship.friend_id == user_id)) |
            ((Friendship.user_id == user_id) & (Friendship.friend_id == current_user_id))
        ).first() is not None

        # Generate a URL for the profile picture
        picture_url = (
            url_for('serve_image', filename=user.picture, _external=True)
            if user.picture else None
        )

        # Return user details, including is_friend status
        return jsonify({
            'id': user.id,
            'name': user.name,
            'description': user.description,
            'location': user.location,
            'picture': picture_url,
            'is_friend': is_friend,  # Added field
        }), 200

    except Exception as e:
        app.logger.error(f"Error fetching user data: {str(e)}")
        return jsonify({"error": f"Error fetching user data: {str(e)}"}), 500
    

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity


from sqlalchemy import case
from sqlalchemy.orm import aliased

@app.route('/api/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    current_user_id = get_jwt_identity()
    base_url = request.host_url  # e.g., "http://127.0.0.1:5555/"

    # Create aliases for the User model
    requester = aliased(User)
    acceptor = aliased(User)

    notifications = (
        db.session.query(
            Notification.id,
            Notification.message,
            Notification.type,
            Notification.friend_request_id,
            Notification.read,
            FriendRequest.status.label("friend_request_status"),
            # For "friend_accept" notifications, use the acceptor's info; otherwise, use the requester's info.
            case(
                (Notification.type == "friend_accept", acceptor.name),
                else_=requester.name
            ).label("originator_name"),
            case(
                (Notification.type == "friend_accept", acceptor.picture),
                else_=requester.picture
            ).label("originator_profile_pic"),
            case(
                (Notification.type == "friend_accept", acceptor.id),
                else_=requester.id
            ).label("originator_id")
        )
        .outerjoin(FriendRequest, FriendRequest.id == Notification.friend_request_id)
        .outerjoin(requester, requester.id == FriendRequest.requester_id)
        .outerjoin(acceptor, acceptor.id == FriendRequest.recipient_id)
        .filter(Notification.user_id == current_user_id)
        .filter(
            (Notification.type != "friend_request") | (FriendRequest.status != "accepted")
        )
        .all()
    )

    notification_list = [
        {
            "id": notif.id,
            "message": notif.message,
            "type": notif.type,
            "friend_request_id": notif.friend_request_id,
            "friend_request_status": notif.friend_request_status or "unknown",
            "originator_name": notif.originator_name or "Unknown User",
            "originator_profile_pic": (
                f"{base_url}static/{notif.originator_profile_pic}"
                if notif.originator_profile_pic
                else f"{base_url}static/default.jpg"
            ),
            "originator_id": notif.originator_id,
            "read": notif.read
        }
        for notif in notifications
    ]

    return jsonify(notification_list), 200



# Accept friend request
@app.route('/api/accept-friend-request', methods=['POST'])
@jwt_required()
def accept_friend_request():
    data = request.get_json()
    request_id = data.get("requestId")
    current_user_id = get_jwt_identity()

    if not request_id:
        return jsonify({"error": "Request ID is required"}), 400

    friend_request = FriendRequest.query.get(request_id)
    if not friend_request:
        return jsonify({"error": "Friend request not found"}), 404

    if friend_request.recipient_id != current_user_id:
        return jsonify({"error": "You are not the recipient of this friend request"}), 403

    if friend_request.status == "accepted":
        return jsonify({"error": "Friend request already accepted"}), 400

    # Accept friend request
    friend_request.status = "accepted"

    # Create reciprocal friendship in both directions.
    new_friendship_1 = Friendship(user_id=current_user_id, friend_id=friend_request.requester_id)
    new_friendship_2 = Friendship(user_id=friend_request.requester_id, friend_id=current_user_id)
    db.session.add_all([new_friendship_1, new_friendship_2])

    # Fetch the requester's details
    requester_user = User.query.get(friend_request.requester_id)
    if not requester_user:
        return jsonify({"error": "Requester user not found"}), 404

    # Fetch the current (recipient) user
    recipient_user = User.query.get(current_user_id)
    if not recipient_user:
        return jsonify({"error": "Recipient user not found"}), 404

    # Notify the requester that the friend request was accepted
    new_notification = Notification(
        user_id=friend_request.requester_id,  # Notify the requester
        message=f"{recipient_user.name} accepted your friend request!",
        type="friend_accept",
        friend_request_id=friend_request.id  # Associate the notification with the request
    )
    db.session.add(new_notification)

    db.session.commit()

    return jsonify({"message": "Friend request accepted!"}), 200



#Fetch friends list
@app.route('/api/friends', methods=['GET'])
@jwt_required()
def get_friends():
    current_user_id = get_jwt_identity()

    friends = db.session.query(
        User.id,
        User.name,
        User.picture
    ).join(Friendship, Friendship.friend_id == User.id
    ).filter(Friendship.user_id == current_user_id).all()

    friends_list = [
        {
            "id": friend.id,
            "name": friend.name,
            "profile_pic": f"{request.host_url}static/{friend.picture}" if friend.picture else f"{request.host_url}static/default.jpg"
        }
        for friend in friends
    ]

    return jsonify(friends_list), 200

@app.route('/api/mark-all-read', methods=['POST'])
@jwt_required()
def mark_all_read():
    current_user_id = get_jwt_identity()
    Notification.query.filter_by(user_id=current_user_id, read=False).update({"read": True})
    db.session.commit()
    return jsonify({"message": "All notifications marked as read"}), 200

# ----- Messaging API Endpoints -----

# ---------------------------
# Socket.IO event handlers
@socketio.on("connect")
def handle_connect():
    print("Client connected")

@socketio.on("disconnect")
def handle_disconnect():
    print("Client disconnected")

@socketio.on("join_chat")
def handle_join_chat(data):
    user_id = data.get("user_id")
    join_room(f"user_{user_id}")
    print(f"User {user_id} joined room user_{user_id}")

@socketio.on("leave_chat")
def handle_leave_chat(data):
    user_id = data.get("user_id")
    leave_room(f"user_{user_id}")
    print(f"User {user_id} left room user_{user_id}")


# --- Messaging Endpoints ---

@app.route("/messages/send", methods=["POST"])
@jwt_required()
def send_message():
    data = request.json
    receiver_id = data.get("receiver_id")
    message_text = data.get("message")
    media_url = data.get("media_url")
    media_type = data.get("media_type")
    
    if not receiver_id or not message_text:
        return jsonify({"error": "Receiver and message are required"}), 400

    current_user_id = get_jwt_identity()
    message = Message(
        sender_id=current_user_id,
        receiver_id=receiver_id,
        message=message_text,
        media_url=media_url,
        media_type=media_type
    )
    db.session.add(message)
    db.session.commit()

    # Get sender info to include in event payload
    sender = User.query.get(current_user_id)
    
    socketio.emit("new_message", {
        "id": message.id,
        "sender_id": current_user_id,
        "receiver_id": receiver_id,
        "message": message_text,
        "media_url": media_url,
        "media_type": media_type,
        "timestamp": message.timestamp.isoformat(),
        "is_read": message.is_read,
        "sender_profile_pic": sender.picture,
        "sender_name": sender.name
    }, room=f"user_{receiver_id}")

    return jsonify({"message": "Message sent successfully"}), 201

@app.route("/messages/<int:user_id>", methods=["GET"])
@jwt_required()
def get_messages(user_id):
    current_user_id = get_jwt_identity()
    messages = Message.query.filter(
        ((Message.sender_id == current_user_id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user_id))
    ).order_by(Message.timestamp.asc()).all()

    result = []
    for msg in messages:
        sender = User.query.get(msg.sender_id)
        result.append({
            "id": msg.id,
            "sender_id": msg.sender_id,
            "receiver_id": msg.receiver_id,
            "message": msg.message,
            "media_url": msg.media_url,
            "media_type": msg.media_type,
            "timestamp": msg.timestamp.isoformat(),
            "is_read": msg.is_read,
            "sender_profile_pic": sender.picture,
            "sender_name": sender.name
        })
    return jsonify(result)

@app.route("/messages/read/<int:sender_id>", methods=["PUT"])
@jwt_required()
def mark_messages_as_read(sender_id):
    current_user_id = get_jwt_identity()
    messages = Message.query.filter_by(receiver_id=current_user_id, sender_id=sender_id, is_read=False).all()
    for msg in messages:
        msg.is_read = True
    db.session.commit()
    return jsonify({"message": "Messages marked as read"}), 200

# --- File Upload Endpoint ---

@app.route("/upload", methods=["POST"])
@jwt_required()  # Optionally protect the endpoint
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(file_path)

    # Create URL for the uploaded file
    file_url = url_for("uploaded_file", filename=filename, _external=True)
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext in ["jpg", "jpeg", "png", "gif"]:
        media_type = "image"
    elif ext in ["mp4", "webm", "ogg"]:
        media_type = "video"
    else:
        media_type = "file"
    return jsonify({"media_url": file_url, "media_type": media_type}), 200

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/api/chats", methods=["GET"])
@jwt_required()
def get_chats():
    current_user_id = get_jwt_identity()
    # Query all messages where current user is either sender or receiver.
    messages = Message.query.filter(
        (Message.sender_id == current_user_id) | (Message.receiver_id == current_user_id)
    ).all()

    # Use a set to collect unique partner IDs.
    partner_ids = set()
    for msg in messages:
        if msg.sender_id != current_user_id:
            partner_ids.add(msg.sender_id)
        if msg.receiver_id != current_user_id:
            partner_ids.add(msg.receiver_id)

    # Build the chat list with user details.
    chats = []
    for pid in partner_ids:
        user = User.query.get(pid)
        if user:
            # Generate a URL for the user's profile picture if needed.
            picture_url = (
                url_for("serve_image", filename=user.picture, _external=True)
                if user.picture else None
            )
            chats.append({
                "id": user.id,
                "name": user.name,
                "profile_pic": picture_url or "/default-profile.png"
            })

    return jsonify(chats), 200



if __name__ == "__main__":
    db.create_all()
    socketio.run(app, debug=True, port=5555)
