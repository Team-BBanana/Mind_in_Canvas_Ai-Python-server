# FastAPI 관련 필수 모듈 임포트
from fastapi import APIRouter, HTTPException, Depends, Query
# 채팅 서비스 관련 모듈 임포트
from app.services.chat_service.chat_service import ChatService
from app.services.chat_service.dependencies import get_chat_service
# 요청 데이터 검증을 위한 Pydantic 모듈 임포트
from pydantic import BaseModel

# POST 요청시 사용될 요청 모델 정의
class ChatRequest(BaseModel):
    message: str  # 사용자의 메시지를 담을 필수 문자열 필드

    # Swagger UI에서 보여질 요청 예시 설정
    class Config:
        json_schema_extra = {
            "example": {
                "message": "안녕하세요, 질문입니다."
            }
        }

# 채팅 관련 라우터 설정
router = APIRouter(
    prefix="/chat",  # 모든 엔드포인트에 적용될 접두사
    tags=["chat"]    # Swagger UI에서의 그룹화를 위한 태그
)


# GET 메서드로 채팅 요청을 처리하는 엔드포인트
@router.get("")
async def chat_with_ai_get(
    # Query 파라미터로 메시지를 받음. 기본값과 설명 포함
    message: str | None = Query(default="안녕하세요, 저는 AI 어시스턴트입니다. 무엇을 도와드릴까요?", description="사용자의 질문을 입력하세요."),
    # 의존성 주입을 통해 채팅 서비스 인스턴스를 받음
    chat_service: ChatService = Depends(get_chat_service)
):
    try:
        # 채팅 서비스를 통해 메시지 전송 및 응답 수신
        response = await chat_service.send_message(message)
        return {"response": response}
    except Exception as e:
        # 오류 발생시 500 Internal Server Error 반환
        raise HTTPException(status_code=500, detail=str(e))


# POST 메서드로 채팅 요청을 처리하는 엔드포인트
@router.post("")
async def chat_with_ai(
    # 요청 본문에서 ChatRequest 모델의 데이터를 받음
    request: ChatRequest,
    # 의존성 주입을 통해 채팅 서비스 인스턴스를 받음
    chat_service: ChatService = Depends(get_chat_service)
):
    try:
        # 채팅 서비스를 통해 메시지 전송 및 응답 수신
        response = await chat_service.send_message(request.message)
        return {"response": response}
    except Exception as e:
        # 오류 발생시 500 Internal Server Error 반환
        raise HTTPException(status_code=500, detail=str(e))

