import os
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from flask_migrate import Migrate
from flask_jwt_extended import jwt_required, get_jwt_identity, JWTManager, create_access_token
from werkzeug.utils import secure_filename
from sqlalchemy.orm import joinedload
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from config import Config

app = Flask(__name__, static_folder="static")
app.config.from_object(Config)

# Enable Cross-Origin Resource Sharing for React Frontend
CORS(app, resources={
    r"/api/*": {"origins": "http://127.0.0.1:5173"},
    r"/static/images/*": {"origins": "*"},
    r"/static/sidebar_images/*": {"origins": "*"},
    r"/static/uploads/*": {"origins": "*"}
}, supports_credentials=True, 
allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Origin"], 
methods=["GET", "POST", "OPTIONS"])

# JWT Configuration
jwt = JWTManager(app)
app.config["JWT_SECRET_KEY"] = os.urandom(24)  
app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies"]
app.config["JWT_ACCESS_COOKIE_NAME"] = "access_token"
app.config["JWT_COOKIE_SECURE"] = False  # Set to True in production
app.config["JWT_HEADER_NAME"] = "Authorization"
app.config["JWT_HEADER_TYPE"] = "Bearer"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=24)

# Database Configuration
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # Replace with your preferred database URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Flask-Mail configuration
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "ericmutuma15@gmail.com" 
app.config["MAIL_PASSWORD"] = "" 


db = SQLAlchemy(app)
mail = Mail(app)
migrate = Migrate(app, db)

# Serializer for secure tokens
#print("SECRET_KEY:", app.config.get("JWT_SECRET_KEY"))
serializer = URLSafeTimedSerializer(app.config["JWT_SECRET_KEY"])


# Import models
from models import User, Message, FriendRequest, Post, Like, Comment

# Utility to check file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Routes
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

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

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password, password):
        access_token = create_access_token(identity=user.id)
        return jsonify({"message": "Login successful", "access_token": access_token}), 200

    return jsonify({"message": "Invalid credentials"}), 401


@app.route("/api/google-login", methods=["POST"])
def google_login():
    data = request.get_json()
    email = data.get("email")

    user = User.query.filter_by(email=email).first()
    if user:
        return jsonify({"message": "Login successful"}), 200
    return jsonify({"message": "Email not registered"}), 404


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



@app.route("/api/users", methods=["GET"])
@jwt_required()
def get_users():
    try:
        current_user_id = get_jwt_identity()
        users = User.query.filter(User.id != current_user_id).all()
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
@jwt_required()
def get_current_user():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.filter_by(id=current_user_id).first()

        if not user:
            return jsonify({"error": "User not found"}), 404

        picture_url = (
            url_for('serve_image', filename=user.picture, _external=True)
            if user.picture else None
        )

        user_data = {
            'id': user.id,
            'name': user.name,
            'description': user.description,
            'location': user.location,
            'picture': picture_url,
        }

        return jsonify(user_data), 200
    except Exception as e:
        return jsonify({"error": f"Error fetching user data: {str(e)}"}), 500

#endpoint to fetch user posts
@app.route("/api/user_posts", methods=["GET"])
@jwt_required()
def get_user_posts():
    try:
        current_user_id = get_jwt_identity()

        # Query posts made by the current user
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
                    "profile_picture": (
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
        user_id = get_jwt_identity()  # Get user ID from the token
        post = Post.query.get(post_id)

        if not post:
            return jsonify({"error": "Post not found"}), 404

        # Get the content of the comment from the request
        comment_content = request.json.get('content')

        if not comment_content:
            return jsonify({"error": "Comment content is required"}), 400

        # Create a new comment object and add it to the database
        new_comment = Comment(content=comment_content, user_id=user_id, post_id=post.id)
        db.session.add(new_comment)
        db.session.commit()

        # Return the newly created comment
        return jsonify({
            "id": new_comment.id,
            "content": new_comment.content,
            "user_name": new_comment.user.name,  
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


if __name__ == "__main__":
    db.create_all()
    app.run(debug=True, port=5555)
