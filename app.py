import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from flask_migrate import Migrate
from flask_jwt_extended import jwt_required, get_jwt_identity, JWTManager, create_access_token
from datetime import timedelta

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing for React Frontend
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

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Import User model (defined in models.py)
from models import User


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


@app.route('/api/profile', methods=['POST'])
@jwt_required()
def update_profile():
    try:
        # Get the current user ID from the JWT token
        current_user_id = get_jwt_identity()  
        print(f"Current User ID: {current_user_id}")  # Log the user ID for debugging

        # Retrieve the data from the form
        name = request.form.get('name')
        description = request.form.get('description')
        location = request.form.get('location')
        picture = request.files.get('picture')

        # Validate that all required fields are provided
        if not name or not description or not location or not picture:
            return jsonify({'error': 'All fields are required'}), 400

        # Fetch the user from the database
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Ensure the uploads directory exists
        if not os.path.exists('uploads'):
            os.makedirs('uploads')

        # Save the picture
        image_path = os.path.join('uploads', picture.filename)
        picture.save(image_path)

        # Update the user profile
        user.name = name
        user.description = description
        user.location = location
        user.picture = image_path

        # Commit the changes to the database
        db.session.commit()

        return jsonify({'message': 'Profile updated successfully'}), 200

    except Exception as e:
        # Log the exception and return an error response
        error_message = traceback.format_exc()  # Get the full traceback of the error
        print(error_message)  # Log the error to the console
        return jsonify({'error': f'Error updating profile: {str(e)}'}), 500


if __name__ == "__main__":
    db.create_all()  # Create database tables
    app.run(debug=True)
