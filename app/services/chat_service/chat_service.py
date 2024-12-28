from abc import ABC, abstractmethod

class ChatService(ABC):
    """텍스트 서비스 인터페이스"""
    
    @abstractmethod
    async def send_message(self, message: str) -> str:
        """사용자의 메시지를 받아 채팅 응답을 반환"""
        pass 