import os
import sqlite3
import psycopg2
from flask import Flask
from models import db, User, Post, Comment, Like, Message, FriendRequest  

# Initialize Flask app
app = Flask(__name__)
app.config.from_object('config.Config')  # Load your configuration (DATABASE_URL, etc.)

# Initialize the database connection with SQLAlchemy
db.init_app(app)

# Helper function to migrate data from SQLite to PostgreSQL
def migrate_data():
    # Connect to SQLite database (update with your actual path)
    sqlite_conn = sqlite3.connect('sqlite.db')  # Path to your SQLite database
    sqlite_cursor = sqlite_conn.cursor()

    # Fetch data from SQLite (adjust for your tables and columns)
    sqlite_cursor.execute("SELECT * FROM users")  # Fetch all users from SQLite
    users = sqlite_cursor.fetchall()

    # Connect to PostgreSQL database on Render
    postgres_conn = psycopg2.connect(os.environ.get('DATABASE_URL'))  # Get DATABASE_URL from environment variable
    postgres_cursor = postgres_conn.cursor()

    # Migrate users to PostgreSQL
    for user in users:
        postgres_cursor.execute(
            "INSERT INTO users (id, name, email, password, description, location, picture, is_super_user) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (user[0], user[1], user[2], user[3], user[4], user[5], user[6], user[7])  # Adjust based on the SQLite schema
        )

    # Fetch posts from SQLite
    sqlite_cursor.execute("SELECT * FROM posts")
    posts = sqlite_cursor.fetchall()

    # Migrate posts to PostgreSQL
    for post in posts:
        postgres_cursor.execute(
            "INSERT INTO posts (id, user_id, content, media_url, timestamp) "
            "VALUES (%s, %s, %s, %s, %s)",
            (post[0], post[1], post[2], post[3], post[4])  # Adjust based on the SQLite schema
        )

    # Fetch comments from SQLite
    sqlite_cursor.execute("SELECT * FROM comments")
    comments = sqlite_cursor.fetchall()

    # Migrate comments to PostgreSQL
    for comment in comments:
        postgres_cursor.execute(
            "INSERT INTO comments (id, content, timestamp, user_id, post_id) "
            "VALUES (%s, %s, %s, %s, %s)",
            (comment[0], comment[1], comment[2], comment[3], comment[4])  # Adjust based on the SQLite schema
        )

    # Fetch likes from SQLite
    sqlite_cursor.execute("SELECT * FROM likes")
    likes = sqlite_cursor.fetchall()

    # Migrate likes to PostgreSQL
    for like in likes:
        postgres_cursor.execute(
            "INSERT INTO likes (id, user_id, post_id) "
            "VALUES (%s, %s, %s)",
            (like[0], like[1], like[2])  # Adjust based on the SQLite schema
        )

    # Fetch messages from SQLite
    sqlite_cursor.execute("SELECT * FROM messages")
    messages = sqlite_cursor.fetchall()

    # Migrate messages to PostgreSQL
    for message in messages:
        postgres_cursor.execute(
            "INSERT INTO messages (id, sender_id, receiver_id, message, media_type, media_url, timestamp) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (message[0], message[1], message[2], message[3], message[4], message[5], message[6])  # Adjust based on the SQLite schema
        )

    # Fetch friend requests from SQLite
    sqlite_cursor.execute("SELECT * FROM friend_requests")
    friend_requests = sqlite_cursor.fetchall()

    # Migrate friend requests to PostgreSQL
    for friend_request in friend_requests:
        postgres_cursor.execute(
            "INSERT INTO friend_requests (id, requester_id, recipient_id, status, timestamp) "
            "VALUES (%s, %s, %s, %s, %s)",
            (friend_request[0], friend_request[1], friend_request[2], friend_request[3], friend_request[4])  # Adjust based on the SQLite schema
        )

    # Commit changes to PostgreSQL and close the connections
    postgres_conn.commit()

    # Close all cursors and connections
    sqlite_cursor.close()
    sqlite_conn.close()
    postgres_cursor.close()
    postgres_conn.close()

# Run the migration script
if __name__ == "__main__":
    with app.app_context():
        migrate_data()  # Call the migration function
