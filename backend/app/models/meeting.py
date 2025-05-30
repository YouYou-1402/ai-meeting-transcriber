# backend/app/models/meeting.py
from . import db
from datetime import datetime
import json

class Meeting(db.Model):
    __tablename__ = 'meetings'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    duration = db.Column(db.Float)  # in seconds
    
    # Transcription data
    transcript = db.Column(db.Text)
    summary = db.Column(db.Text)
    action_items = db.Column(db.Text)  # JSON string
    participants = db.Column(db.Text)  # JSON string
    
    # Processing status
    status = db.Column(db.String(50), default='uploaded')  # uploaded, processing, completed, failed
    processing_progress = db.Column(db.Integer, default=0)  # 0-100
    error_message = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    
    # Output files
    document_path = db.Column(db.String(500))
    audio_path = db.Column(db.String(500))
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'filename': self.filename,
            'file_size': self.file_size,
            'duration': self.duration,
            'transcript': self.transcript,
            'summary': self.summary,
            'action_items': json.loads(self.action_items) if self.action_items else [],
            'participants': json.loads(self.participants) if self.participants else [],
            'status': self.status,
            'processing_progress': self.processing_progress,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'document_path': self.document_path
        }
    
    def set_action_items(self, items):
        self.action_items = json.dumps(items, ensure_ascii=False)
    
    def set_participants(self, participants):
        self.participants = json.dumps(participants, ensure_ascii=False)
