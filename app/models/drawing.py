from typing import Optional, List
from pydantic import BaseModel, Field
from dataclasses import dataclass, field
from datetime import datetime

class NewDrawingRequest(BaseModel):
    robot_id: str = Field(..., description="로봇 고유 번호")
    name: str = Field(..., description="아이 이름")
    age: Optional[int] = Field(None, description="아이 나이")
    canvas_id: str = Field(..., description="현재 그림 ID (UUID)")

@dataclass
class ChatMessage:
    role: str  # 'user' 또는 'ai'
    text: str
    timestamp: datetime = field(default_factory=datetime.now)

class DrawingData:
    def __init__(self, robot_id: str, name: str, age: Optional[int], canvas_id: str):
        self.robot_id = robot_id
        self.name = name
        self.age = age
        self.canvas_id = canvas_id
        self.prompt = ""
        self.audio_data = None
        self.chat_history: List[ChatMessage] = []

    def add_message(self, role: str, text: str):
        """대화 내용을 저장"""
        self.chat_history.append(ChatMessage(role=role, text=text)) 