from datetime import datetime
from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    credits = db.Column(db.Integer, default=50, nullable=False)
    
    # Profile fields
    full_name = db.Column(db.String(100))
    organization = db.Column(db.String(100))
    role = db.Column(db.String(100))
    preferences = db.Column(db.JSON, default={})
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    chats = db.relationship('Chat', backref='user', lazy=True)
    documents = db.relationship('Document', backref='user', lazy=True)
    insurance_requirements = db.relationship('InsuranceRequirement', backref='user', lazy=True)
    insurance_claims = db.relationship('InsuranceClaim', backref='user', lazy=True)
    reports = db.relationship('Report', backref='user', lazy=True)

    def __init__(self, username, email):
        self.username = username
        self.email = email
        self.credits = 50
        self.last_login = datetime.utcnow()
        self.created_at = datetime.utcnow()
        self.preferences = {
            'notification_enabled': True,
            'theme': 'light',
            'language': 'en'
        }

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

    def update_profile(self, data):
        """Update user profile with provided data"""
        self.full_name = data.get('full_name', self.full_name)
        self.organization = data.get('organization', self.organization)
        self.role = data.get('role', self.role)
        if 'preferences' in data:
            self.preferences.update(data['preferences'])

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    report_type = db.Column(db.String(50), nullable=False)  # summary, analysis, metrics
    content = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_shared = db.Column(db.Boolean, default=False)
    shared_with = db.Column(db.JSON, default=[])

    def __init__(self, user_id, title, report_type, content):
        self.user_id = user_id
        self.title = title
        self.report_type = report_type
        self.content = content

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship('Message', back_populates='chat', lazy=True)
    documents = db.relationship('Document', secondary='chat_documents', backref='chats')

    def __init__(self, user_id, title=None):
        self.user_id = user_id
        self.title = title or "New Chat"

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    chat = db.relationship('Chat', back_populates='messages')

    def __repr__(self):
        return f'<Message {self.id}>'

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

chat_documents = db.Table('chat_documents',
    db.Column('chat_id', db.Integer, db.ForeignKey('chat.id'), primary_key=True),
    db.Column('document_id', db.Integer, db.ForeignKey('document.id'), primary_key=True)
)