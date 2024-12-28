from abc import ABC, abstractmethod

class ChatService(ABC):
    """채팅 서비스를 위한 인터페이스"""
    
    @abstractmethod
    async def send_message(self, message: str) -> str:
        """사용자의 메시지를 받아 채팅 응답을 반환"""
        pass 