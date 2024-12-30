# 추상 클래스와 추상 메서드를 위한 ABC 모듈 임포트
from abc import ABC, abstractmethod
# 그림 요청 데이터 모델 클래스 임포트
from app.models.drawing import NewDrawingRequest
# 네임드튜플 타입을 위한 임포트
from typing import NamedTuple

# 음성 처리 결과를 담는 네임드튜플 클래스 정의
class AudioProcessingResult(NamedTuple):
    text: str        # 음성을 텍스트로 변환한 결과
    audio_data: bytes # AI가 생성한 응답 음성 데이터



# 그림 서비스의 추상 인터페이스 클래스 정의
class DrawingService(ABC):
    
    # 새로운 그림 그리기 세션을 시작하는 추상 메서드
    @abstractmethod
    async def handle_new_drawing(self, request: NewDrawingRequest) -> str:
        """새로운 그림 요청을 처리하고 결과를 반환"""
        pass



    # 사용자의 음성 입력을 처리하고 AI 응답을 생성하는 추상 메서드
    @abstractmethod
    async def process_audio(self, audio_data: bytes, robot_id: str, canvas_id: str) -> AudioProcessingResult:
        """음성 데이터를 처리하고 응답을 생성"""
        pass 