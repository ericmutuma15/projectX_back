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
    is_super_user = db.Column(db.Boolean, default=False)

    # Relationships
    posts = db.relationship('Post', back_populates='user', lazy='dynamic')
    sent_requests = db.relationship('FriendRequest', foreign_keys='FriendRequest.requester_id', back_populates='requester')
    received_requests = db.relationship('FriendRequest', foreign_keys='FriendRequest.recipient_id', back_populates='recipient')
    likes = db.relationship('Like', back_populates='user', lazy='dynamic')
    comments = db.relationship('Comment', back_populates='user', lazy='select')

    def __repr__(self):
        return f"<User {self.name}>"


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=True)  # Text, images, videos, quotes, etc.
    media_url = db.Column(db.String(300), nullable=True)  # URL or file path for media
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='posts', overlaps="author")
    author = db.relationship('User', back_populates='posts', overlaps="user")
    likes = db.relationship('Like', back_populates='post', lazy='dynamic')
    comments = db.relationship('Comment', back_populates='post', lazy='select')  # Change 'dynamic' to 'select'

    # This method calculates the total like count for a post
    def like_count(self):
        return self.likes.count()  # This returns the total number of likes

    def __repr__(self):
        return f"<Post by User {self.user_id} at {self.timestamp}>"

class Comment(db.Model):  # New Comment model
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)  # Content of the comment
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='comments')
    post = db.relationship('Post', back_populates='comments')

    def __repr__(self):
        return f"<Comment by User {self.user_id} on Post {self.post_id}>"

class Like(db.Model):
    __tablename__ = 'likes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='likes')
    post = db.relationship('Post', back_populates='likes')

    def __repr__(self):
        return f"<Like by User {self.user_id} on Post {self.post_id}>"

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=True)
    media_type = db.Column(db.String(10), nullable=True)  # image, video, audio
    media_url = db.Column(db.String(300), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_read = db.Column(db.Boolean, default=False)  # New field to track read status

    sender = db.relationship("User", foreign_keys=[sender_id])
    receiver = db.relationship("User", foreign_keys=[receiver_id])

    def __repr__(self):
        return f"<Message from {self.sender_id} to {self.receiver_id}>"


class FriendRequest(db.Model):
    __tablename__ = 'friend_requests'
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    requester = db.relationship('User', foreign_keys=[requester_id], back_populates='sent_requests')
    recipient = db.relationship('User', foreign_keys=[recipient_id], back_populates='received_requests')

    def __repr__(self):
        return f"<FriendRequest from {self.requester_id} to {self.recipient_id}, status={self.status}>"


class Notification(db.Model):
    __tablename__ = 'notification'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    friend_request_id = db.Column(db.Integer, db.ForeignKey('friend_requests.id'), nullable=False)
    read = db.Column(db.Boolean, default=False)  # New field to track read status

    # Relationships (optional, but useful)
    friend_request = db.relationship("FriendRequest", backref="notifications")

    


class Friendship(db.Model):
    __tablename__ = 'friendship'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", foreign_keys=[user_id], backref="friends")
    friend = db.relationship("User", foreign_keys=[friend_id], backref="friend_of")

    __table_args__ = (db.UniqueConstraint('user_id', 'friend_id', name='unique_friendship'),)
    
    