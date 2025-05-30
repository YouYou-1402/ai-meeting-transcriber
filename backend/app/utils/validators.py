# backend/app/utils/validators.py
import re
import os
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class Validators:
    
    @staticmethod
    def validate_file_upload(file, allowed_extensions: Dict[str, set], max_size_mb: int = 500) -> Dict[str, Any]:
        """
        Validate file upload
        
        Args:
            file: File object
            allowed_extensions: Allowed file extensions
            max_size_mb: Kích thước file tối đa (MB)
            
        Returns:
            Dictionary chứa kết quả validation
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'file_type': None
        }
        
        try:
            # Kiểm tra file có tồn tại
            if not file or not file.filename:
                result['valid'] = False
                result['errors'].append("Không có file được chọn")
                return result
            
            filename = file.filename.lower()
            
            # Kiểm tra extension
            if '.' not in filename:
                result['valid'] = False
                result['errors'].append("File không có extension")
                return result
            
            extension = filename.rsplit('.', 1)[1]
            
            # Xác định loại file
            file_type = None
            for ftype, extensions in allowed_extensions.items():
                if extension in extensions:
                    file_type = ftype
                    break
            
            if not file_type:
                result['valid'] = False
                result['errors'].append(f"Loại file '{extension}' không được hỗ trợ")
                return result
            
            result['file_type'] = file_type
            
            # Kiểm tra kích thước file
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)  # Reset file pointer
            
            max_size_bytes = max_size_mb * 1024 * 1024
            if file_size > max_size_bytes:
                result['valid'] = False
                result['errors'].append(f"Kích thước file vượt quá giới hạn {max_size_mb}MB")
                return result
            
            # Warnings cho file lớn
            if file_size > 100 * 1024 * 1024:  # 100MB
                result['warnings'].append("File có kích thước lớn, thời gian xử lý có thể lâu")
            
            # Kiểm tra tên file
            if not Validators.validate_filename(file.filename):
                result['warnings'].append("Tên file chứa ký tự đặc biệt, sẽ được tự động điều chỉnh")
            
        except Exception as e:
            logger.error(f"Error validating file: {str(e)}")
            result['valid'] = False
            result['errors'].append("Lỗi khi kiểm tra file")
        
        return result
    
    @staticmethod
    def validate_filename(filename: str) -> bool:
        """
        Kiểm tra tên file hợp lệ
        
        Args:
            filename: Tên file
            
        Returns:
            True nếu hợp lệ
        """
        if not filename:
            return False
        
        # Kiểm tra ký tự không hợp lệ
        invalid_chars = r'[<>:"/\\|?*]'
        if re.search(invalid_chars, filename):
            return False
        
        # Kiểm tra độ dài
        if len(filename) > 255:
            return False
        
        # Kiểm tra tên file reserved (Windows)
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL'] + [f'COM{i}' for i in range(1, 10)] + [f'LPT{i}' for i in range(1, 10)]
        name_without_ext = os.path.splitext(filename)[0].upper()
        if name_without_ext in reserved_names:
            return False
        
        return True
    
    @staticmethod
    def validate_meeting_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate dữ liệu cuộc họp
        
        Args:
            data: Dữ liệu cuộc họp
            
        Returns:
            Kết quả validation
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Kiểm tra title
        title = data.get('title', '').strip()
        if not title:
            result['errors'].append("Tiêu đề cuộc họp không được để trống")
            result['valid'] = False
        elif len(title) > 200:
            result['errors'].append("Tiêu đề cuộc họp không được vượt quá 200 ký tự")
            result['valid'] = False
        
        # Kiểm tra transcript
        transcript = data.get('transcript', '').strip()
        if transcript and len(transcript) < 10:
            result['warnings'].append("Transcript quá ngắn, có thể không chính xác")
        
        # Kiểm tra action items
        action_items = data.get('action_items', [])
        if action_items:
            for i, item in enumerate(action_items):
                if not isinstance(item, dict):
                    result['errors'].append(f"Action item {i+1} không đúng định dạng")
                    result['valid'] = False
                    continue
                
                if not item.get('task', '').strip():
                    result['warnings'].append(f"Action item {i+1} thiếu mô tả nhiệm vụ")
        
        return result
    
    @staticmethod
    def validate_api_request(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
        """
        Validate API request data
        
        Args:
            data: Request data
            required_fields: Danh sách field bắt buộc
            
        Returns:
            Kết quả validation
        """
        result = {
            'valid': True,
            'errors': [],
            'missing_fields': []
        }
        
        # Kiểm tra required fields
        for field in required_fields:
            if field not in data or data[field] is None:
                result['missing_fields'].append(field)
                result['valid'] = False
        
        if result['missing_fields']:
            result['errors'].append(f"Thiếu các trường bắt buộc: {', '.join(result['missing_fields'])}")
        
        return result
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = None) -> str:
        """
        Làm sạch input text
        
        Args:
            text: Text cần làm sạch
            max_length: Độ dài tối đa
            
        Returns:
            Text đã được làm sạch
        """
        if not isinstance(text, str):
            return ""
        
        # Loại bỏ ký tự đặc biệt nguy hiểm
        text = re.sub(r'[<>"\']', '', text)
        
        # Trim whitespace
        text = text.strip()
        
        # Giới hạn độ dài
        if max_length and len(text) > max_length:
            text = text[:max_length]
        
        return text
