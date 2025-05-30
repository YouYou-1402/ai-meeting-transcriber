# backend/app/routes/__init__.py
from flask import Blueprint

def register_routes(app):
    """Đăng ký tất cả routes"""
    from .meeting_routes import meeting_bp
    from .file_routes import file_bp
    
    app.register_blueprint(meeting_bp, url_prefix='/api/meetings')
    app.register_blueprint(file_bp, url_prefix='/api/files')
