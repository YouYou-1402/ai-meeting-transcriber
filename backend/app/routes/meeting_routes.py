# backend/app/routes/meeting_routes.py
from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import RequestEntityTooLarge
import os
import logging
import threading
from datetime import datetime

from ..models import db
from ..models.meeting import Meeting
from ..services.audio_processor import AudioProcessor
from ..services.transcription_service import TranscriptionService
from ..services.llm_service import LLMService
from ..services.document_generator import DocumentGenerator
from ..utils.file_handler import FileHandler
from ..utils.validators import Validators

logger = logging.getLogger(__name__)

meeting_bp = Blueprint('meetings', __name__)

# Global services (sẽ được khởi tạo trong app factory)
audio_processor = None
transcription_service = None
llm_service = None
document_generator = None
file_handler = None

def init_services(app):
    """Khởi tạo các services"""
    global audio_processor, transcription_service, llm_service, document_generator, file_handler
    
    audio_processor = AudioProcessor(app.config['TEMP_FOLDER'])
    transcription_service = TranscriptionService(app.config['WHISPER_MODEL'])
    llm_service = LLMService(app.config['OPENAI_API_KEY'])
    document_generator = DocumentGenerator(app.config['OUTPUT_FOLDER'])
    file_handler = FileHandler(app.config['UPLOAD_FOLDER'], app.config['ALLOWED_EXTENSIONS'])

@meeting_bp.route('/', methods=['GET'])
def get_meetings():
    """Lấy danh sách cuộc họp"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status')
        
        # Query với pagination
        query = Meeting.query
        
        if status:
            query = query.filter(Meeting.status == status)
        
        meetings = query.order_by(Meeting.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'data': {
                'meetings': [meeting.to_dict() for meeting in meetings.items],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': meetings.total,
                    'pages': meetings.pages,
                    'has_next': meetings.has_next,
                    'has_prev': meetings.has_prev
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting meetings: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Lỗi khi lấy danh sách cuộc họp'
        }), 500

@meeting_bp.route('/<int:meeting_id>', methods=['GET'])
def get_meeting(meeting_id):
    """Lấy thông tin chi tiết cuộc họp"""
    try:
        meeting = Meeting.query.get_or_404(meeting_id)
        return jsonify({
            'success': True,
            'data': meeting.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error getting meeting {meeting_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Lỗi khi lấy thông tin cuộc họp'
        }), 500

@meeting_bp.route('/upload', methods=['POST'])
def upload_meeting():
    """Upload file cuộc họp"""
    try:
        # Kiểm tra file trong request
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Không có file được upload'
            }), 400
        
        file = request.files['file']
        title = request.form.get('title', '').strip()
        
        # Validate file
        validation_result = Validators.validate_file_upload(
            file, 
            current_app.config['ALLOWED_EXTENSIONS'],
            current_app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024)
        )
        
        if not validation_result['valid']:
            return jsonify({
                'success': False,
                'error': validation_result['errors'][0] if validation_result['errors'] else 'File không hợp lệ'
            }), 400
        
        # Tạo title mặc định nếu không có
        if not title:
            title = os.path.splitext(file.filename)[0]
        
        # Lưu file
        file_info = file_handler.save_uploaded_file(file)
        if not file_info:
            return jsonify({
                'success': False,
                'error': 'Lỗi khi lưu file'
            }), 500
        
        # Lấy thông tin media
        media_info = audio_processor.get_media_info(file_info['file_path'])
        
        # Tạo record trong database
        meeting = Meeting(
            title=title,
            filename=file_info['filename'],
            file_path=file_info['file_path'],
            file_size=file_info['size'],
            duration=media_info.get('duration') if media_info else None,
            status='uploaded'
        )
        
        db.session.add(meeting)
        db.session.commit()
        
        # Bắt đầu xử lý trong background
        threading.Thread(
            target=process_meeting_async,
            args=(meeting.id,),
            daemon=True
        ).start()
        
        return jsonify({
            'success': True,
            'data': meeting.to_dict(),
            'message': 'File đã được upload thành công. Đang bắt đầu xử lý...'
        }), 201
        
    except RequestEntityTooLarge:
        return jsonify({
            'success': False,
            'error': 'File quá lớn'
        }), 413
        
    except Exception as e:
        logger.error(f"Error uploading meeting: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Lỗi khi upload file'
        }), 500

@meeting_bp.route('/<int:meeting_id>/process', methods=['POST'])
def process_meeting(meeting_id):
    """Xử lý cuộc họp (transcription + LLM analysis)"""
    try:
        meeting = Meeting.query.get_or_404(meeting_id)
        
        if meeting.status == 'processing':
            return jsonify({
                'success': False,
                'error': 'Cuộc họp đang được xử lý'
            }), 400
        
        if meeting.status == 'completed':
            return jsonify({
                'success': False,
                'error': 'Cuộc họp đã được xử lý'
            }), 400
        
        # Bắt đầu xử lý trong background
        threading.Thread(
            target=process_meeting_async,
            args=(meeting_id,),
            daemon=True
        ).start()
        
        return jsonify({
            'success': True,
            'message': 'Bắt đầu xử lý cuộc họp'
        })
        
    except Exception as e:
        logger.error(f"Error starting meeting processing: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Lỗi khi bắt đầu xử lý'
        }), 500

@meeting_bp.route('/<int:meeting_id>/download', methods=['GET'])
def download_meeting_document(meeting_id):
    """Download tài liệu cuộc họp"""
    try:
        from flask import send_file
        
        meeting = Meeting.query.get_or_404(meeting_id)
        
        if not meeting.document_path or not os.path.exists(meeting.document_path):
            return jsonify({
                'success': False,
                'error': 'Tài liệu chưa được tạo'
            }), 404
        
        return send_file(
            meeting.document_path,
            as_attachment=True,
            download_name=f"bien_ban_{meeting.title}_{meeting.id}.docx"
        )
        
    except Exception as e:
        logger.error(f"Error downloading document: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Lỗi khi tải tài liệu'
        }), 500

@meeting_bp.route('/<int:meeting_id>', methods=['PUT'])
def update_meeting(meeting_id):
    """Cập nhật thông tin cuộc họp"""
    try:
        meeting = Meeting.query.get_or_404(meeting_id)
        data = request.get_json()
        
        # Validate dữ liệu
        validation_result = Validators.validate_meeting_data(data)
        if not validation_result['valid']:
            return jsonify({
                'success': False,
                'error': validation_result['errors'][0]
            }), 400
        
        # Cập nhật các field được phép
        allowed_fields = ['title', 'summary', 'action_items', 'participants']
        
        for field in allowed_fields:
            if field in data:
                if field == 'action_items':
                    meeting.set_action_items(data[field])
                elif field == 'participants':
                    meeting.set_participants(data[field])
                else:
                    setattr(meeting, field, data[field])
        
        meeting.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': meeting.to_dict(),
            'message': 'Cập nhật thành công'
        })
        
    except Exception as e:
        logger.error(f"Error updating meeting: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Lỗi khi cập nhật cuộc họp'
        }), 500

@meeting_bp.route('/<int:meeting_id>', methods=['DELETE'])
def delete_meeting(meeting_id):
    """Xóa cuộc họp"""
    try:
        meeting = Meeting.query.get_or_404(meeting_id)
        
        # Xóa các file liên quan
        files_to_delete = [
            meeting.file_path,
            meeting.audio_path,
            meeting.document_path
        ]
        
        for file_path in files_to_delete:
            if file_path and os.path.exists(file_path):
                file_handler.delete_file(file_path)
        
        # Xóa record từ database
        db.session.delete(meeting)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Xóa cuộc họp thành công'
        })
        
    except Exception as e:
        logger.error(f"Error deleting meeting: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Lỗi khi xóa cuộc họp'
        }), 500

def process_meeting_async(meeting_id):
    """Xử lý cuộc họp trong background"""
    from .. import create_app
    
    # Tạo app context cho background thread
    app = create_app()
    
    with app.app_context():
        try:
            meeting = Meeting.query.get(meeting_id)
            if not meeting:
                logger.error(f"Meeting {meeting_id} not found")
                return
            
            # Cập nhật status
            meeting.status = 'processing'
            meeting.processing_progress = 0
            db.session.commit()
            
            logger.info(f"Starting processing for meeting {meeting_id}")
            
            # Bước 1: Tách âm thanh (nếu là video)
            audio_path = meeting.file_path
            if meeting.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv')):
                logger.info("Extracting audio from video...")
                audio_path = audio_processor.extract_audio_from_video(meeting.file_path)
                if not audio_path:
                    raise Exception("Không thể tách âm thanh từ video")
                meeting.audio_path = audio_path
            
            meeting.processing_progress = 20
            db.session.commit()
            
            # Bước 2: Transcription
            logger.info("Starting transcription...")
            transcript_data = transcription_service.transcribe_audio(audio_path)
            if not transcript_data:
                raise Exception("Không thể chuyển đổi âm thanh thành văn bản")
            
            meeting.transcript = transcript_data['text']
            meeting.processing_progress = 50
            db.session.commit()
            
            # Bước 3: LLM Analysis
            logger.info("Starting LLM analysis...")
            
            # Tạo summary
            summary_result = llm_service.generate_meeting_summary(
                transcript_data['text'],
                {
                    'title': meeting.title,
                    'duration': meeting.duration,
                    'filename': meeting.filename
                }
            )
            
            if summary_result:
                meeting.summary = summary_result['summary']
            
            meeting.processing_progress = 70
            db.session.commit()
            
            # Trích xuất action items
            action_items = llm_service.extract_action_items(transcript_data['text'])
            if action_items:
                meeting.set_action_items(action_items)
            
            # Xác định participants
            participants = llm_service.identify_participants(transcript_data['text'])
            if participants:
                meeting.set_participants(participants)
            
            meeting.processing_progress = 85
            db.session.commit()
            
            # Bước 4: Tạo document
            logger.info("Generating document...")
            document_path = document_generator.create_meeting_minutes(meeting.to_dict())
            if document_path:
                meeting.document_path = document_path
            
            # Hoàn thành
            meeting.status = 'completed'
            meeting.processing_progress = 100
            meeting.processed_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"Meeting {meeting_id} processed successfully")
            
        except Exception as e:
            logger.error(f"Error processing meeting {meeting_id}: {str(e)}")
            
            # Cập nhật status lỗi
            meeting = Meeting.query.get(meeting_id)
            if meeting:
                meeting.status = 'failed'
                meeting.error_message = str(e)
                db.session.commit()

@meeting_bp.route('/stats', methods=['GET'])
def get_meeting_stats():
    """Lấy thống kê cuộc họp"""
    try:
        total_meetings = Meeting.query.count()
        completed_meetings = Meeting.query.filter(Meeting.status == 'completed').count()
        processing_meetings = Meeting.query.filter(Meeting.status == 'processing').count()
        failed_meetings = Meeting.query.filter(Meeting.status == 'failed').count()
        
        # Tổng thời lượng
        total_duration = db.session.query(db.func.sum(Meeting.duration)).filter(
            Meeting.duration.isnot(None)
        ).scalar() or 0
        
        return jsonify({
            'success': True,
            'data': {
                'total_meetings': total_meetings,
                'completed_meetings': completed_meetings,
                'processing_meetings': processing_meetings,
                'failed_meetings': failed_meetings,
                'total_duration_hours': round(total_duration / 3600, 2),
                'success_rate': round((completed_meetings / total_meetings * 100), 2) if total_meetings > 0 else 0
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Lỗi khi lấy thống kê'
        }), 500
