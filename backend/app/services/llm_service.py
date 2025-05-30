# backend/app/services/llm_service.py
import openai
import logging
import json
from typing import Optional, Dict, List, Any
import re

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self, api_key: str):
        """
        Khởi tạo LLM service với OpenAI API
        
        Args:
            api_key: OpenAI API key
        """
        openai.api_key = api_key
        self.model = "gpt-3.5-turbo"  # Có thể thay đổi thành gpt-4
    
    def generate_meeting_summary(self, transcript: str, meeting_info: Dict = None) -> Optional[Dict[str, Any]]:
        """
        Tạo tóm tắt cuộc họp từ transcript
        
        Args:
            transcript: Bản ghi cuộc họp
            meeting_info: Thông tin bổ sung về cuộc họp
            
        Returns:
            Dictionary chứa summary và các thông tin đã trích xuất
        """
        try:
            # Tạo prompt cho việc tóm tắt
            prompt = self._create_summary_prompt(transcript, meeting_info)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Bạn là một AI chuyên gia về việc phân tích và tóm tắt cuộc họp. Hãy tạo biên bản cuộc họp chuyên nghiệp và chi tiết."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            summary_text = response.choices[0].message.content
            
            # Phân tích và trích xuất thông tin từ summary
            parsed_summary = self._parse_summary(summary_text)
            
            return {
                "summary": summary_text,
                "parsed_data": parsed_summary,
                "model_used": self.model,
                "tokens_used": response.usage.total_tokens if hasattr(response, 'usage') else 0
            }
            
        except Exception as e:
            logger.error(f"Error generating meeting summary: {str(e)}")
            return None
    
    def extract_action_items(self, transcript: str) -> Optional[List[Dict[str, Any]]]:
        """
        Trích xuất các nhiệm vụ cần làm từ transcript
        
        Args:
            transcript: Bản ghi cuộc họp
            
        Returns:
            List các action items
        """
        try:
            prompt = f"""
            Phân tích bản ghi cuộc họp sau và trích xuất tất cả các nhiệm vụ cần làm (action items).
            
            Với mỗi nhiệm vụ, hãy xác định:
            1. Mô tả nhiệm vụ
            2. Người chịu trách nhiệm (nếu có)
            3. Deadline (nếu có)
            4. Mức độ ưu tiên (cao/trung bình/thấp)
            
            Trả về kết quả dưới dạng JSON array với format:
            [
                {{
                    "task": "Mô tả nhiệm vụ",
                    "assignee": "Tên người chịu trách nhiệm",
                    "deadline": "Ngày deadline",
                    "priority": "cao/trung bình/thấp",
                    "status": "pending"
                }}
            ]
            
            Bản ghi cuộc họp:
            {transcript}
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.2
            )
            
            # Parse JSON response
            try:
                action_items = json.loads(response.choices[0].message.content)
                return action_items if isinstance(action_items, list) else []
            except json.JSONDecodeError:
                # Fallback: parse text response
                return self._parse_action_items_from_text(response.choices[0].message.content)
                
        except Exception as e:
            logger.error(f"Error extracting action items: {str(e)}")
            return []
    
    def identify_participants(self, transcript: str) -> Optional[List[str]]:
        """
        Xác định danh sách người tham gia cuộc họp
        
        Args:
            transcript: Bản ghi cuộc họp
            
        Returns:
            List tên người tham gia
        """
        try:
            prompt = f"""
            Phân tích bản ghi cuộc họp sau và xác định danh sách tất cả người tham gia.
            
            Trả về danh sách tên dưới dạng JSON array:
            ["Tên người 1", "Tên người 2", ...]
            
            Chỉ trả về tên thật của người tham gia, không bao gồm "Speaker 1", "Speaker 2".
            
            Bản ghi cuộc họp:
            {transcript[:2000]}...
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.2
            )
            
            try:
                participants = json.loads(response.choices[0].message.content)
                return participants if isinstance(participants, list) else []
            except json.JSONDecodeError:
                # Fallback: parse text response
                return self._parse_participants_from_text(response.choices[0].message.content)
                
        except Exception as e:
            logger.error(f"Error identifying participants: {str(e)}")
            return []
    
    def _create_summary_prompt(self, transcript: str, meeting_info: Dict = None) -> str:
        """Tạo prompt cho việc tóm tắt cuộc họp"""
        base_prompt = f"""
        Phân tích bản ghi cuộc họp sau và tạo biên bản cuộc họp chuyên nghiệp theo định dạng:
        
        BIÊN BẢN CUỘC HỌP
        
        1. THÔNG TIN CHUNG:
        - Thời gian: [Trích xuất từ nội dung hoặc thông tin bổ sung]
        - Địa điểm: [Trích xuất từ nội dung]
        - Người tham gia: [Danh sách người tham gia]
        - Người ghi biên bản: [Nếu có]
        
        2. MỤC ĐÍCH CUỘC HỌP:
        - [Mục đích chính của cuộc họp]
        
        3. NỘI DUNG THẢO LUẬN:
        - [Các điểm thảo luận chính, được tổ chức theo chủ đề]
        
        4. QUYẾT ĐỊNH:
        - [Các quyết định quan trọng đã được đưa ra]
        
        5. NHIỆM VỤ CẦN LÀM:
        - [Danh sách công việc cụ thể với người chịu trách nhiệm và deadline]
        
        6. VẤN ĐỀ CẦN THEO DÕI:
        - [Các vấn đề chưa giải quyết hoặc cần theo dõi]
        
        7. CUỘC HỌP TIẾP THEO:
        - [Thông tin về cuộc họp tiếp theo nếu có]
        
        Bản ghi cuộc họp:
        {transcript}
        """
        
        if meeting_info:
            additional_info = f"\n\nThông tin bổ sung về cuộc họp:\n"
            for key, value in meeting_info.items():
                additional_info += f"- {key}: {value}\n"
            base_prompt += additional_info
        
        return base_prompt
    
    def _parse_summary(self, summary_text: str) -> Dict[str, Any]:
        """Parse summary text để trích xuất thông tin cấu trúc"""
        parsed = {
            "meeting_info": {},
            "discussion_points": [],
            "decisions": [],
            "action_items": [],
            "next_steps": []
        }
        
        try:
            # Trích xuất thông tin chung
            info_match = re.search(r'1\. THÔNG TIN CHUNG:(.*?)2\. MỤC ĐÍCH', summary_text, re.DOTALL)
            if info_match:
                info_text = info_match.group(1)
                # Parse thời gian, địa điểm, người tham gia...
                time_match = re.search(r'- Thời gian: (.*)', info_text)
                if time_match:
                    parsed["meeting_info"]["time"] = time_match.group(1).strip()
                
                location_match = re.search(r'- Địa điểm: (.*)', info_text)
                if location_match:
                    parsed["meeting_info"]["location"] = location_match.group(1).strip()
            
            # Trích xuất các quyết định
            decisions_match = re.search(r'4\. QUYẾT ĐỊNH:(.*?)5\. NHIỆM VỤ', summary_text, re.DOTALL)
            if decisions_match:
                decisions_text = decisions_match.group(1)
                decisions = re.findall(r'- (.*)', decisions_text)
                parsed["decisions"] = [d.strip() for d in decisions if d.strip()]
            
        except Exception as e:
            logger.error(f"Error parsing summary: {str(e)}")
        
        return parsed
    
    def _parse_action_items_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Parse action items từ text response"""
        action_items = []
        lines = text.split('\n')
        
        for line in lines:
            if line.strip().startswith('-') or line.strip().startswith('•'):
                task_text = line.strip().lstrip('-•').strip()
                if task_text:
                    action_items.append({
                        "task": task_text,
                        "assignee": "Chưa xác định",
                        "deadline": "Chưa xác định",
                        "priority": "trung bình",
                        "status": "pending"
                    })
        
        return action_items
    
    def _parse_participants_from_text(self, text: str) -> List[str]:
        """Parse participants từ text response"""
        participants = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('[') and not line.startswith(']'):
                # Remove quotes and clean up
                name = line.strip('"').strip("'").strip(',').strip()
                if name and name not in participants:
                    participants.append(name)
        
        return participants
