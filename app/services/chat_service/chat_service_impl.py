from app.services.chat_service.chat_service import ChatService
from app.services.chat_service.chat_domain_service import call_openai_api

class ChatServiceImpl(ChatService):
    
    
    async def send_message(self, message: str) -> str:
        try:
            messages = [{
                "role": "user", 
                "content": message
            }]
            
            return await call_openai_api(messages)
            
        except Exception as e:
            # ChatService 관련 오류임을 명시하는 커스텀 에러 메시지
            raise Exception(f"ChatService 오류: {str(e)}")
