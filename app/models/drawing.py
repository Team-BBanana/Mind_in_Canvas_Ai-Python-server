from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

class NewDrawingRequest(BaseModel):
    robot_id: str = Field(..., description="로봇 고유 번호")
    name: str = Field(..., description="아이 이름")
    age: Optional[int] = Field(None, description="아이 나이")
    canvas_id: str = Field(..., description="현재 그림 ID (UUID)")

class ChatMessage(BaseModel):
    role: str
    text: str
    timestamp: datetime = Field(default_factory=datetime.now)

class DrawingData(BaseModel):
    """그림 데이터를 담는 모델"""
    robot_id: str
    name: str
    age: Optional[int]
    canvas_id: str
    image_id: Optional[str] = None  # 🔑 image_id 필드 추가
    prompt: str = ""
    audio_data: Optional[bytes] = None
    chat_history: List[ChatMessage] = []
    analysis: str = ""
    summary: str = ""
    drawing_name: str = ""
    image_url: Optional[str] = None
    analyses: List['DrawingAnalysis'] = []
    contents: Optional[str] = None  # 🔄 **새로 추가된 필드**


    def add_message(self, role: str, text: str):
        """대화 내용을 저장"""
        self.chat_history.append(ChatMessage(role=role, text=text))

    def update_image(self, image_url: str):
        """이미지 URL 업데이트"""
        self.image_url = image_url

    def add_analysis(self, analysis: 'DrawingAnalysis'):
        """분석 결과 추가"""
        self.analyses.append(analysis)


class DrawingAnalysis(BaseModel):
    """그림 분석 결과를 담는 모델"""
    colors: List[str]
    emotion: str
    content: str
    context: str

class DrawingSocketRequest(BaseModel):
    """웹소켓 연결 요청 데이터 모델"""
    canvas_id: str


class DoneDrawingRequest(BaseModel):
    canvas_id: str = Field(..., description="현재 그림 ID (UUID)")
    image_url: str = Field(..., description="S3에 저장된 최종 이미지 URL")

class DoneDrawingResponse(BaseModel):
    status: str = Field(..., description="요청 처리 상태 ('success' 또는 'error')")
    analysis: Optional[str] = Field(None, description="AI 분석 결과 (감정/의도 등)")
    summary: Optional[str] = Field(None, description="대화 요약 내용")
    conversation_history: Optional[str] = Field(None, description="전체 대화 기록")
    background_image: Optional[str] = Field(None, description="생성된 배경 이미지 URL")
    drawing_name: Optional[str] = Field(None, description="생성된 그림 이름")


