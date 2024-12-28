from fastapi import Depends
from .chat_service import ChatService
from .chat_service_impl import ChatServiceImpl

def get_chat_service() -> ChatService:
    return ChatServiceImpl()