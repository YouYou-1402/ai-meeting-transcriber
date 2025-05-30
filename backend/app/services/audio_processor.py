# backend/app/services/audio_processor.py
import ffmpeg
import os
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class AudioProcessor:
    def __init__(self, temp_folder: str):
        self.temp_folder = temp_folder
        os.makedirs(temp_folder, exist_ok=True)
    
    def extract_audio_from_video(self, video_path: str, output_path: str = None) -> Optional[str]:
        """
        Tách âm thanh từ video sử dụng FFmpeg
        
        Args:
            video_path: Đường dẫn file video
            output_path: Đường dẫn file âm thanh output (optional)
            
        Returns:
            Đường dẫn file âm thanh đã tách hoặc None nếu lỗi
        """
        try:
            if not output_path:
                base_name = os.path.splitext(os.path.basename(video_path))[0]
                output_path = os.path.join(self.temp_folder, f"{base_name}_audio.wav")
            
            # Kiểm tra file input tồn tại
            if not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                return None
            
            # Tách âm thanh với FFmpeg
            (
                ffmpeg
                .input(video_path)
                .output(
                    output_path,
                    acodec='pcm_s16le',  # WAV format
                    ac=1,  # Mono channel
                    ar='16000'  # 16kHz sample rate (tối ưu cho Whisper)
                )
                .overwrite_output()
                .run(quiet=True, capture_stdout=True)
            )
            
            # Kiểm tra file output được tạo thành công
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"Audio extracted successfully: {output_path}")
                return output_path
            else:
                logger.error("Audio extraction failed - output file is empty or not created")
                return None
                
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error during audio extraction: {e.stderr.decode()}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during audio extraction: {str(e)}")
            return None
    
    def get_media_info(self, file_path: str) -> Optional[dict]:
        """
        Lấy thông tin metadata của file media
        
        Args:
            file_path: Đường dẫn file media
            
        Returns:
            Dictionary chứa thông tin media hoặc None nếu lỗi
        """
        try:
            probe = ffmpeg.probe(file_path)
            
            # Tìm stream video và audio
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            audio_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)
            
            info = {
                'duration': float(probe['format']['duration']),
                'size': int(probe['format']['size']),
                'format_name': probe['format']['format_name'],
                'bit_rate': int(probe['format'].get('bit_rate', 0))
            }
            
            if video_stream:
                info.update({
                    'width': int(video_stream.get('width', 0)),
                    'height': int(video_stream.get('height', 0)),
                    'video_codec': video_stream.get('codec_name'),
                    'fps': eval(video_stream.get('r_frame_rate', '0/1'))
                })
            
            if audio_stream:
                info.update({
                    'audio_codec': audio_stream.get('codec_name'),
                    'sample_rate': int(audio_stream.get('sample_rate', 0)),
                    'channels': int(audio_stream.get('channels', 0))
                })
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting media info: {str(e)}")
            return None
    
    def convert_to_wav(self, input_path: str, output_path: str = None) -> Optional[str]:
        """
        Chuyển đổi file âm thanh sang định dạng WAV
        
        Args:
            input_path: Đường dẫn file input
            output_path: Đường dẫn file output (optional)
            
        Returns:
            Đường dẫn file WAV hoặc None nếu lỗi
        """
        try:
            if not output_path:
                base_name = os.path.splitext(os.path.basename(input_path))[0]
                output_path = os.path.join(self.temp_folder, f"{base_name}.wav")
            
            (
                ffmpeg
                .input(input_path)
                .output(
                    output_path,
                    acodec='pcm_s16le',
                    ac=1,
                    ar='16000'
                )
                .overwrite_output()
                .run(quiet=True, capture_stdout=True)
            )
            
            if os.path.exists(output_path):
                logger.info(f"Audio converted to WAV: {output_path}")
                return output_path
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error converting to WAV: {str(e)}")
            return None
