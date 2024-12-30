from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from dataclasses import dataclass, field
from datetime import datetime

class NewDrawingRequest(BaseModel):
    robot_id: str = Field(..., description="로봇 고유 번호")
    name: str = Field(..., description="아이 이름")
    age: Optional[int] = Field(None, description="아이 나이")
    canvas_id: str = Field(..., description="현재 그림 ID (UUID)")

class DrawingAnalysis(BaseModel):
    colors: List[str] = Field(default_factory=list, description="사용된 색상들")
    emotion: str = Field("", description="감지된 감정")
    content: str = Field("", description="그림 내용 분석")
    context: str = Field("", description="대화 문맥 정보")
    timestamp: datetime = Field(default_factory=datetime.now)

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
        self.current_image_url: str = ""
        self.drawing_analysis: List[DrawingAnalysis] = []

    def add_message(self, role: str, text: str):
        """대화 내용을 저장"""
        self.chat_history.append(ChatMessage(role=role, text=text))

    def update_image(self, image_url: str):
        """현재 이미지 URL 업데이트"""
        self.current_image_url = image_url

    def add_analysis(self, analysis: DrawingAnalysis):
        """그림 분석 데이터 추가"""
        self.drawing_analysis.append(analysis)

class DrawingSocketRequest(BaseModel):
    canvas_id: str = Field(..., description="현재 그림 ID (UUID)")
    image_url: str = Field(..., description="S3 URL") 