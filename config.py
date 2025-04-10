import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    if os.environ.get('FLASK_ENV') == 'production':
        SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')  # Use the connection string from Render
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///users.db'  # SQLite for local development