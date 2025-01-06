from app import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500))
    location = db.Column(db.String(255))
    picture = db.Column(db.String(255))

    posts = db.relationship('Post', backref='author', lazy='dynamic')

    def __repr__(self):
        return f"<User {self.name}>"

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=True)  # Text, images, videos, quotes, etc.
    media_url = db.Column(db.String(300), nullable=True)  # URL or file path for media
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user = db.relationship('User', back_populates='posts')

    def __repr__(self):
        return f"<Post by User {self.user_id} at {self.timestamp}>"
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'content': self.content,
            'media_url': self.media_url,
            'timestamp': self.timestamp.isoformat(),  # Ensure datetime is in ISO format
        }

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=True)  # Optional for media-only messages
    media_type = db.Column(db.String(10), nullable=True)  # e.g., 'text', 'image', 'audio'
    media_url = db.Column(db.String(300), nullable=True)  # URL or file path for media
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Message from {self.sender_id} to {self.receiver_id}>"

class FriendRequest(db.Model):
    __tablename__ = 'friend_requests'
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'accepted', 'rejected'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    requester = db.relationship('User', foreign_keys=[requester_id], backref='sent_requests')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_requests')

    def __repr__(self):
        return f"<FriendRequest from {self.requester_id} to {self.recipient_id}, status={self.status}>"
