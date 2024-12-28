from fastapi import APIRouter, HTTPException
from app.services.chat_service.chat_service_impl import ChatServiceImpl

# router 객체를 직접 export
router = APIRouter(
    # prefix="/chat",
    tags=["test"]
)

@router.get("/test")
async def test_openai():
    service = ChatServiceImpl()
    try:
        response = await service.send_message("한국어로 답해줘, 미국 대통령은?")
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

# @router.post("/send_message")