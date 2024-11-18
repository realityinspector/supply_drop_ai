from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    credits = db.Column(db.Integer, default=50, nullable=False)  # Added credits field
    chats = db.relationship('Chat', backref='user', lazy=True)
    documents = db.relationship('Document', backref='user', lazy=True)
    insurance_requirements = db.relationship('InsuranceRequirement', backref='user', lazy=True)
    insurance_claims = db.relationship('InsuranceClaim', backref='user', lazy=True)

    def __init__(self, username, email):
        self.username = username
        self.email = email
        self.credits = 50  # Initialize with 50 credits

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def deduct_credits(self, amount=1):
        if self.credits >= amount:
            self.credits -= amount
            return True
        return False

    def add_credits(self, amount):
        self.credits += amount

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship('Message', backref='chat', lazy=True)

    def __init__(self, user_id, title=None):
        self.user_id = user_id
        self.title = title or "New Chat"

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, chat_id, content, role):
        self.chat_id = chat_id
        self.content = content
        self.role = role

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    processing_type = db.Column(db.String(50), nullable=False, default='text')  # text, summary, analysis, insurance_requirements
    processed_content = db.Column(db.JSON)  # Store processed results as JSON
    processing_status = db.Column(db.String(20), nullable=False, default='pending')  # pending, completed, failed

    def __init__(self, user_id, filename, content, processing_type=None):
        self.user_id = user_id
        self.filename = filename
        self.content = content
        self.processing_type = processing_type or 'text'
        self.processing_status = 'pending'

class InsuranceRequirement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=False)
    requirement_text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100))
    priority = db.Column(db.String(20))  # high, medium, low
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    claims = db.relationship('InsuranceClaim', backref='requirement', lazy=True)

    def __init__(self, user_id, document_id, requirement_text, category=None, priority=None):
        self.user_id = user_id
        self.document_id = document_id
        self.requirement_text = requirement_text
        self.category = category
        self.priority = priority

class InsuranceClaim(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    requirement_id = db.Column(db.Integer, db.ForeignKey('insurance_requirement.id'), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    analysis_type = db.Column(db.String(50))  # critique, enhance, formalize, grammar
    analysis_result = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, user_id, requirement_id, document_id, analysis_type=None, analysis_result=None):
        self.user_id = user_id
        self.requirement_id = requirement_id
        self.document_id = document_id
        self.analysis_type = analysis_type
        self.analysis_result = analysis_result
        self.status = 'pending'