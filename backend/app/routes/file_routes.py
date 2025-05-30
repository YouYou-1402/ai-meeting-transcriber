# backend/app/routes/file_routes.py
from flask import Blueprint, request, jsonify, current_app, send_file
import os
import logging
from ..utils.file_handler import FileHandler

logger = logging.getLogger(__name__)

file_bp = Blueprint('files', __name__)

@file_bp.route('/upload-test', methods=['POST'])
def test_upload():
    """Test endpoint cho việc upload file"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Không có file'
            }), 400
        
        file = request.files['file']
        
        file_handler = FileHandler(
            current_app.config['UPLOAD_FOLDER'],
            current_app.config['ALLOWED_EXTENSIONS']
        )
        
        result = file_handler.save_uploaded_file(file)
        
        if result:
            return jsonify({
                'success': True,
                'data': result,
                'message': 'Upload thành công'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Lỗi khi upload file'
            }), 500
            
    except Exception as e:
        logger.error(f"Error in test upload: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@file_bp.route('/download/<path:filename>', methods=['GET'])
def download_file(filename):
    """Download file từ output folder"""
    try:
        file_path = os.path.join(current_app.config['OUTPUT_FOLDER'], filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': 'File không tồn tại'
            }), 404
        
        return send_file(file_path, as_attachment=True)
        
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Lỗi khi tải file'
        }), 500
