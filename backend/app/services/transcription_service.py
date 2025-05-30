# backend/app/services/transcription_service.py
import whisper
import logging
import os
from typing import Optional, Dict, Any
import torch

logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self, model_name: str = "base"):
        """
        Khởi tạo Whisper transcription service
        
        Args:
            model_name: Tên model Whisper (tiny, base, small, medium, large)
        """
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load Whisper model"""
        try:
            # Kiểm tra CUDA có sẵn không
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Loading Whisper model '{self.model_name}' on device: {device}")
            
            self.model = whisper.load_model(self.model_name, device=device)
            logger.info(f"Whisper model '{self.model_name}' loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading Whisper model: {str(e)}")
            raise
    
    def transcribe_audio(self, audio_path: str, language: str = None) -> Optional[Dict[str, Any]]:
        """
        Chuyển đổi âm thanh thành văn bản
        
        Args:
            audio_path: Đường dẫn file âm thanh
            language: Ngôn ngữ (vi, en, auto-detect nếu None)
            
        Returns:
            Dictionary chứa transcript và metadata hoặc None nếu lỗi
        """
        try:
            if not os.path.exists(audio_path):
                logger.error(f"Audio file not found: {audio_path}")
                return None
            
            logger.info(f"Starting transcription for: {audio_path}")
            
            # Thực hiện transcription
            options = {
                "fp16": torch.cuda.is_available(),  # Sử dụng FP16 nếu có GPU
                "verbose": False
            }
            
            if language:
                options["language"] = language
            
            result = self.model.transcribe(audio_path, **options)
            
            # Xử lý kết quả
            transcript_data = {
                "text": result["text"].strip(),
                "language": result.get("language", "unknown"),
                "segments": []
            }
            
            # Xử lý segments với timestamps
            for segment in result.get("segments", []):
                transcript_data["segments"].append({
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"].strip()
                })
            
            logger.info(f"Transcription completed. Text length: {len(transcript_data['text'])} characters")
            return transcript_data
            
        except Exception as e:
            logger.error(f"Error during transcription: {str(e)}")
            return None
    
    def transcribe_with_speaker_detection(self, audio_path: str) -> Optional[Dict[str, Any]]:
        """
        Transcription với phát hiện người nói (cơ bản)
        
        Args:
            audio_path: Đường dẫn file âm thanh
            
        Returns:
            Dictionary chứa transcript với speaker labels
        """
        try:
            result = self.transcribe_audio(audio_path)
            if not result:
                return None
            
            # Phân tích segments để phát hiện người nói
            # (Đây là implementation cơ bản, có thể cải thiện với pyannote.audio)
            speakers = []
            current_speaker = "Speaker 1"
            speaker_count = 1
            
            for i, segment in enumerate(result["segments"]):
                # Logic đơn giản: thay đổi speaker nếu có khoảng im lặng > 2 giây
                if i > 0:
                    silence_duration = segment["start"] - result["segments"][i-1]["end"]
                    if silence_duration > 2.0:  # 2 giây im lặng
                        speaker_count += 1
                        current_speaker = f"Speaker {speaker_count}"
                
                speakers.append({
                    "speaker": current_speaker,
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"]
                })
            
            result["speakers"] = speakers
            return result
            
        except Exception as e:
            logger.error(f"Error in speaker detection: {str(e)}")
            return None
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Lấy thông tin về model hiện tại
        
        Returns:
            Dictionary chứa thông tin model
        """
        return {
            "model_name": self.model_name,
            "device": str(self.model.device) if self.model else "unknown",
            "cuda_available": torch.cuda.is_available(),
            "model_loaded": self.model is not None
        }
