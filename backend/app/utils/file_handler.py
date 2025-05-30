# backend/app/utils/file_handler.py
import os
import shutil
import hashlib
import mimetypes
from werkzeug.utils import secure_filename
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class FileHandler:
    def __init__(self, upload_folder: str, allowed_extensions: Dict[str, set]):
        """
        Khởi tạo File Handler
        
        Args:
            upload_folder: Thư mục upload
            allowed_extensions: Dictionary các extension được phép
        """
        self.upload_folder = upload_folder
        self.allowed_extensions = allowed_extensions
        os.makedirs(upload_folder, exist_ok=True)
    
    def is_allowed_file(self, filename: str, file_type: str = None) -> bool:
        """
        Kiểm tra file có được phép upload không
        
        Args:
            filename: Tên file
            file_type: Loại file ('video', 'audio')
            
        Returns:
            True nếu được phép, False nếu không
        """
        if not filename or '.' not in filename:
            return False
        
        extension = filename.rsplit('.', 1)[1].lower()
        
        if file_type and file_type in self.allowed_extensions:
            return extension in self.allowed_extensions[file_type]
        
        # Kiểm tra tất cả các loại file
        all_extensions = set()
        for extensions in self.allowed_extensions.values():
            all_extensions.update(extensions)
        
        return extension in all_extensions
    
    def save_uploaded_file(self, file, filename: str = None) -> Optional[Dict[str, Any]]:
        """
        Lưu file upload
        
        Args:
            file: File object từ request
            filename: Tên file tùy chỉnh (optional)
            
        Returns:
            Dictionary chứa thông tin file đã lưu hoặc None nếu lỗi
        """
        try:
            if not file or not file.filename:
                logger.error("No file provided")
                return None
            
            # Kiểm tra file được phép
            if not self.is_allowed_file(file.filename):
                logger.error(f"File type not allowed: {file.filename}")
                return None
            
            # Tạo tên file an toàn
            if not filename:
                filename = secure_filename(file.filename)
            else:
                # Giữ extension gốc
                original_ext = file.filename.rsplit('.', 1)[1].lower()
                if '.' not in filename:
                    filename = f"{filename}.{original_ext}"
                filename = secure_filename(filename)
            
            # Tạo tên file unique nếu đã tồn tại
            file_path = os.path.join(self.upload_folder, filename)
            counter = 1
            base_name, ext = os.path.splitext(filename)
            
            while os.path.exists(file_path):
                new_filename = f"{base_name}_{counter}{ext}"
                file_path = os.path.join(self.upload_folder, new_filename)
                filename = new_filename
                counter += 1
            
            # Lưu file
            file.save(file_path)
            
            # Lấy thông tin file
            file_info = self.get_file_info(file_path)
            file_info['filename'] = filename
            file_info['file_path'] = file_path
            
            logger.info(f"File saved successfully: {file_path}")
            return file_info
            
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            return None
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Lấy thông tin chi tiết của file
        
        Args:
            file_path: Đường dẫn file
            
        Returns:
            Dictionary chứa thông tin file
        """
        try:
            if not os.path.exists(file_path):
                return {}
            
            stat = os.stat(file_path)
            mime_type, _ = mimetypes.guess_type(file_path)
            
            # Tính hash MD5
            md5_hash = self.calculate_file_hash(file_path)
            
            return {
                'size': stat.st_size,
                'mime_type': mime_type,
                'created_time': stat.st_ctime,
                'modified_time': stat.st_mtime,
                'md5_hash': md5_hash,
                'extension': os.path.splitext(file_path)[1].lower()
            }
            
        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            return {}
    
    def calculate_file_hash(self, file_path: str) -> Optional[str]:
        """
        Tính MD5 hash của file
        
        Args:
            file_path: Đường dẫn file
            
        Returns:
            MD5 hash string hoặc None nếu lỗi
        """
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating file hash: {str(e)}")
            return None
    
    def delete_file(self, file_path: str) -> bool:
        """
        Xóa file
        
        Args:
            file_path: Đường dẫn file
            
        Returns:
            True nếu xóa thành công, False nếu lỗi
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"File deleted: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            return False
    
    def move_file(self, source_path: str, destination_path: str) -> bool:
        """
        Di chuyển file
        
        Args:
            source_path: Đường dẫn file nguồn
            destination_path: Đường dẫn file đích
            
        Returns:
            True nếu di chuyển thành công, False nếu lỗi
        """
        try:
            # Tạo thư mục đích nếu chưa tồn tại
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            
            shutil.move(source_path, destination_path)
            logger.info(f"File moved from {source_path} to {destination_path}")
            return True
        except Exception as e:
            logger.error(f"Error moving file: {str(e)}")
            return False
    
    def cleanup_temp_files(self, temp_folder: str, max_age_hours: int = 24):
        """
        Dọn dẹp các file tạm thời cũ
        
        Args:
            temp_folder: Thư mục chứa file tạm
            max_age_hours: Tuổi tối đa của file (giờ)
        """
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for filename in os.listdir(temp_folder):
                file_path = os.path.join(temp_folder, filename)
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getctime(file_path)
                    if file_age > max_age_seconds:
                        self.delete_file(file_path)
                        logger.info(f"Cleaned up old temp file: {file_path}")
                        
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
