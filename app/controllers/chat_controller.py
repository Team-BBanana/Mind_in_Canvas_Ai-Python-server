from fastapi import APIRouter, HTTPException, Depends
from app.services.chat_service.chat_service import ChatService
from app.services.chat_service.dependencies import get_chat_service
from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str  # 기본값 제거, 필수 필드로 설정

    class Config:
        json_schema_extra = {
            "example": {
                "message": "안녕하세요, 질문입니다."
            }
        }

router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

@router.post("/")
async def chat_with_ai(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    try:
        response = await chat_service.send_message(request.message)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


