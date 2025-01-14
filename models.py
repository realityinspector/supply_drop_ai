from datetime import datetime
from extensions import db

class Document(db.Model):
    """Temporary document storage for analysis"""
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    processing_type = db.Column(db.String(50), nullable=False)  # 'rejection_analysis' or 'resource_finder'
    session_id = db.Column(db.String(100), nullable=False)  # Store Flask session ID
    
    def __init__(self, filename, file_path, content, processing_type, session_id):
        self.filename = filename
        self.file_path = file_path
        self.content = content
        self.processing_type = processing_type
        self.session_id = session_id