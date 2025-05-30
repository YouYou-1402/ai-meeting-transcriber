# backend/app/__init__.py
from flask import Flask
from flask_cors import CORS
import logging
import os

def create_app(config_name='default'):
    """Application factory"""
    app = Flask(__name__)
    
    # Load configuration
    from .config import config
    app.config.from_object(config[config_name])
    
    # Setup logging
    setup_logging(app)
    
    # Initialize extensions
    CORS(app, origins=app.config['CORS_ORIGINS'])
    
    # Initialize database
    from .models import init_db
    init_db(app)
    
    # Create directories
    create_directories(app)
    
    # Register routes
    from .routes import register_routes
    register_routes(app)
    
    # Initialize services for routes
    from .routes.meeting_routes import init_services
    init_services(app)
    
    # Error handlers
    register_error_handlers(app)
    
    return app

def setup_logging(app):
    """Setup logging configuration"""
    if not app.debug:
        # Production logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s %(name)s %(message)s',
            handlers=[
                logging.FileHandler('app.log'),
                logging.StreamHandler()
            ]
        )
    else:
        # Development logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s %(levelname)s %(name)s %(message)s'
        )

def create_directories(app):
    """Tạo các thư mục cần thiết"""
    directories = [
        app.config['UPLOAD_FOLDER'],
        app.config['OUTPUT_FOLDER'],
        app.config['TEMP_FOLDER']
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def register_error_handlers(app):
    """Đăng ký error handlers"""
    
    @app.errorhandler(404)
    def not_found(error):
        return {
            'success': False,
            'error': 'Không tìm thấy tài nguyên'
        }, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {
            'success': False,
            'error': 'Lỗi server nội bộ'
        }, 500
    
    @app.errorhandler(413)
    def too_large(error):
        return {
            'success': False,
            'error': 'File quá lớn'
        }, 413
