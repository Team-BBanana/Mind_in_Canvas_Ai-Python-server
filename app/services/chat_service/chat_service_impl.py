from app.services.chat_service.chat_service import ChatService
from app.services.chat_service.chat_domain_service import call_openai_api

class ChatServiceImpl(ChatService):
    
    
    async def send_message(self, message: str) -> str:
        messages = [{
            "role": "user",
            "content": message
            }]
        
        return await call_openai_api(messages)
    
