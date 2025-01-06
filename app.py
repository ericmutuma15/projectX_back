import os
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from flask_migrate import Migrate
from flask_jwt_extended import jwt_required, get_jwt_identity, JWTManager, create_access_token
from datetime import timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__)

 # Enable Cross-Origin Resource Sharing for React Frontend
CORS(app,  resources={r"/api/*": {"origins": "http://127.0.0.1:5173"}, r"/static/images/*": {"origins": "*"}, r"/static/uploads/*": {"origins": "*"}},  supports_credentials=True, 
     allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Origin"], 
     methods=["GET", "POST", "OPTIONS"]) 
jwt = JWTManager(app)

# Configure the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # Change to your preferred database
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["JWT_SECRET_KEY"] = "your-secret-key"  # Replace with your secret key
app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies"]  # Define locations
app.config["JWT_ACCESS_COOKIE_NAME"] = "access_token"  # Optional: name of the cookie
app.config["JWT_COOKIE_SECURE"] = False  # For development (set True in production)
app.config["JWT_HEADER_NAME"] = "Authorization"  # Default header name
app.config["JWT_HEADER_TYPE"] = "Bearer"        # Default header type
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=24)  # JWT token expires in 24 hours
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Import User model (defined in models.py)
from models import User, Message, FriendRequest, Post

# Function to check if the file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if User.query.filter_by(email=email).first():
        return jsonify({"message": "Email already registered"}), 400

    hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
    new_user = User(name=name, email=email, password=hashed_password)

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
        # Create JWT token with 24-hour expiration time
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

# Serve images from the static folder
@app.route('/static/images/<filename>')
def serve_image(filename):
    return send_from_directory(os.path.join(app.root_path, 'static/images'), filename)

@app.route('/static/uploads/<filename>')
def static_files(filename):
    return send_from_directory(os.path.join(app.root_path, 'static/uploads'), filename)

# Route to get all users excluding the current authenticated user
@app.route("/api/users", methods=["GET"])
@jwt_required()
def get_users():
    try:
        # Get the user ID of the currently authenticated user
        current_user_id = get_jwt_identity()

        # Query all users excluding the currently authenticated user
        users = User.query.filter(User.id != current_user_id).all()

        

        # Prepare the list of users to return
        user_list = []
        for user in users:
            user_list.append({
                'id': user.id,
                'name': user.name,
                'description': user.description,
                'location': user.location,
                'picture': user.picture,  # The path to the profile picture
            })

        return jsonify(user_list), 200

    except Exception as e:
        return jsonify({"error": f"Error fetching users: {str(e)}"}), 500
    

# Route to get the current authenticated user's data
@app.route("/api/current_user", methods=["GET"])
@jwt_required()
def get_current_user():
    try:
        current_user_id = get_jwt_identity()

        # Query the current user's data
        user = User.query.filter_by(id=current_user_id).first()

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Build the full URL for the profile picture
        picture_url = (
            url_for('serve_image', filename=user.picture, _external=True)
            if user.picture else None
        )

        user_data = {
            'id': user.id,
            'name': user.name,
            'description': user.description,
            'location': user.location,
            'picture': picture_url,  # Full URL for the picture
        }

        return jsonify(user_data), 200

    except Exception as e:
        return jsonify({"error": f"Error fetching user data: {str(e)}"}), 500

    

@app.route('/api/profile', methods=['POST'])
@jwt_required()
def update_profile():
    try:
        current_user_id = get_jwt_identity()  # Get user ID from the JWT token
        name = request.form.get('name')
        description = request.form.get('description')
        location = request.form.get('location')
        picture = request.files.get('picture')

        if not name or not description or not location or not picture:
            return jsonify({'error': 'All fields are required'}), 400

        user = User.query.get(current_user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Ensure the upload folder exists
        upload_folder = app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        # Save the image locally in the static folder
        if picture and allowed_file(picture.filename):
            filename = secure_filename(picture.filename)
            image_path = os.path.join(upload_folder, filename)
            picture.save(image_path)
            user.picture = f'images/{filename}'  # Store the relative path in the database

        user.name = name
        user.description = description
        user.location = location

        db.session.commit()  # Commit the changes to the database

        return jsonify({'message': 'Profile updated successfully'}), 200
    except Exception as e:
        app.logger.error(f"Error updating profile: {str(e)}")
        return jsonify({'error': f'Error updating profile: {str(e)}'}), 500



# Route to send a friend request
@app.route('/api/send-friend-request', methods=['POST'])
@jwt_required()
def send_friend_request():
    current_user_id = get_jwt_identity()
    data = request.get_json()
    recipient_id = data.get('userId')

    if not recipient_id:
        return jsonify({"message": "User ID is required"}), 400

    # Check if the user is trying to send a request to themselves
    if current_user_id == recipient_id:
        return jsonify({"message": "You cannot send a friend request to yourself"}), 400

    # Check if a request already exists
    existing_request = FriendRequest.query.filter_by(requester_id=current_user_id, recipient_id=recipient_id).first()
    if existing_request:
        return jsonify({"message": "Friend request already sent"}), 400

    # Create a new friend request
    friend_request = FriendRequest(requester_id=current_user_id, recipient_id=recipient_id)
    db.session.add(friend_request)
    db.session.commit()

    # Here you can add logic to send a notification to the recipient (e.g., via email, etc.)

    return jsonify({"message": "Friend request sent successfully"}), 200

@app.route('/api/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    current_user_id = get_jwt_identity()
    notifications = FriendRequest.query.filter_by(recipient_id=current_user_id, status='pending').all()
    return jsonify([{
        "id": req.id,
        "requester_name": req.requester.name,
        "timestamp": req.timestamp
    } for req in notifications])


# Route to reject a user
@app.route('/api/reject-user', methods=['POST'])
@jwt_required()
def reject_user():
    current_user_id = get_jwt_identity()
    data = request.get_json()
    recipient_id = data.get('userId')

    if not recipient_id:
        return jsonify({"message": "User ID is required"}), 400

    # Remove the user from the current user's list (reject the user)
    friend_request = FriendRequest.query.filter_by(requester_id=recipient_id, recipient_id=current_user_id, status='pending').first()
    
    if friend_request:
        db.session.delete(friend_request)
        db.session.commit()

        return jsonify({"message": "User rejected successfully"}), 200
    else:
        return jsonify({"message": "No pending friend request found"}), 404



@app.route('/api/posts', methods=['POST'])
@jwt_required()
def create_post():
    try:
        # Get the current user ID from JWT
        current_user_id = get_jwt_identity()

        # Get FormData content
        form_data = request.form.to_dict(flat=True)
        media = request.files.get('media')

        content = form_data.get('content')
        media_url = None

        # Ensure static/uploads directory exists
        uploads_folder = os.path.join(app.root_path, 'static/uploads')
        if not os.path.exists(uploads_folder):
            os.makedirs(uploads_folder)

        if media:
            # Handle media upload
            media_filename = secure_filename(media.filename)
            media.save(os.path.join(uploads_folder, media_filename))
            media_url = f'/static/uploads/{media_filename}'

        if not content and not media_url:
            return jsonify({"error": "Content or media_url is required"}), 400

        # Create a new post
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


#Route to fetch al the feeds

from sqlalchemy.orm import joinedload

@app.route('/api/feeds', methods=['GET'])
def get_all_posts():
    posts = Post.query.options(joinedload(Post.user)).order_by(Post.timestamp.desc()).all()

    response = [{
        'id': post.id,
        'user_id': post.user_id,
        'user_name': post.user.name if post.user else "Unknown",
        'content': post.content,
        'media_url': post.media_url,
        'timestamp': post.timestamp.isoformat()
    } for post in posts]
    
    return jsonify(response), 200





'''@app.route('/api/messages', methods=['POST'])
@jwt_required()
def send_message():
    try:
        data = request.form
        sender_id = get_jwt_identity()
        receiver_id = data.get("receiver_id")
        message = data.get("message")
        media = request.files.get("media")

        if not receiver_id:
            return jsonify({"error": "Receiver ID is required"}), 400

        media_type = None
        media_url = None

        # Save media file if provided
        if media and allowed_file(media.filename):
            filename = secure_filename(media.filename)
            media_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            media.save(media_path)
            media_type = media.mimetype.split('/')[0]
            media_url = f"/static/images/{filename}"

        new_message = Message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            message=message,
            media_type=media_type,
            media_url=media_url
        )
        db.session.add(new_message)
        db.session.commit()
        return jsonify({"message": "Message sent successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/messages/<int:receiver_id>', methods=['GET'])
@jwt_required()
def get_messages(receiver_id):
    try:
        sender_id = get_jwt_identity()
        messages = Message.query.filter(
            (Message.sender_id == sender_id) & (Message.receiver_id == receiver_id) |
            (Message.sender_id == receiver_id) & (Message.receiver_id == sender_id)
        ).order_by(Message.timestamp).all()

        return jsonify([
            {
                "id": msg.id,
                "sender_id": msg.sender_id,
                "receiver_id": msg.receiver_id,
                "message": msg.message,
                "media_type": msg.media_type,
                "media_url": msg.media_url,
                "timestamp": msg.timestamp
            } for msg in messages
        ]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
'''
if __name__ == "__main__":
    db.create_all()  # Create database tables
    app.run(debug=True, port=5555)
