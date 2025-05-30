# backend/app/models/__init__.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db(app):
    """Initialize database"""
    db.init_app(app)
    
    # Import models để SQLAlchemy biết về chúng
    from .meeting import Meeting
    
    # Tạo tables nếu chưa tồn tại
    with app.app_context():
        db.create_all()
