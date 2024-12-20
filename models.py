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

    sent_messages = db.relationship(
        'Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic'
    )
    received_messages = db.relationship(
        'Message', foreign_keys='Message.receiver_id', backref='receiver', lazy='dynamic'
    )

    sent_friend_requests = db.relationship(
        'FriendRequest', foreign_keys='FriendRequest.requester_id', backref='requester', lazy='dynamic'
    )
    received_friend_requests = db.relationship(
        'FriendRequest', foreign_keys='FriendRequest.recipient_id', backref='recipient', lazy='dynamic'
    )

    def __repr__(self):
        return f"<User {self.name}>"


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

    def __repr__(self):
        return f"<FriendRequest from {self.requester_id} to {self.recipient_id}, status={self.status}>"
