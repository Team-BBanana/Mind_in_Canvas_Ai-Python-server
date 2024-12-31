from fastapi import APIRouter, HTTPException
from app.models.drawing import NewDrawingRequest, DoneDrawingRequest
from app.services.drawing_service.dependencies import get_drawing_service
from fastapi.responses import JSONResponse
import logging
import base64

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/drawing",
    tags=["drawing"]
)

@router.post("/new")
async def create_new_drawing(request: NewDrawingRequest):
    try:
        logger.info(f"New drawing request received: {request}")
        drawing_service = get_drawing_service()
        result = await drawing_service.handle_new_drawing(request)
        
        logger.info(f"Drawing service result: {result}")
        
        if result.startswith("error"):
            error_msg = result.replace("error: ", "")
            logger.error(f"Error in drawing service: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 저장된 데이터 가져오기
        drawing_data = drawing_service.drawing_data.get(request.canvas_id)
        if not drawing_data:
            raise HTTPException(status_code=404, detail="Drawing data not found")
            
        # URL에 이름과 나이 추가
        redirect_url = f"/static/voice_chat.html?robot_id={request.robot_id}&canvas_id={request.canvas_id}&name={request.name}"
        if request.age:
            redirect_url += f"&age={request.age}"
            
        return JSONResponse(content={
            "status": "success",
            "redirect_url": redirect_url,
            "initial_audio": base64.b64encode(drawing_data.audio_data).decode('utf-8'),
            "initial_text": drawing_data.prompt
        })
        
    except Exception as e:
        logger.error(f"Unexpected error in create_new_drawing: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"서버 오류가 발생했습니다: {str(e)}"
        )



@router.post("/done")
async def complete_drawing(request: DoneDrawingRequest):
    try:
        logger.info(f"Done drawing request received: {request}")
        drawing_service = get_drawing_service()
        result = await drawing_service.handle_done_drawing(request)
        
        logger.info(f"Drawing service result: {result}")
        
        if result.startswith("error"):
            error_msg = result.replace("error: ", "")
            logger.error(f"Error in drawing service: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 저장된 데이터 가져오기
        drawing_data = drawing_service.drawing_data.get(request.canvas_id)
        if not drawing_data:
            raise HTTPException(status_code=404, detail="Drawing data not found")
        
        return JSONResponse(content={
            "status": "success",
            "analysis": drawing_data.analysis,
            "summary": drawing_data.summary,
            "conversation_history": [f"{msg.role}: {msg.text}" for msg in drawing_data.chat_history],
            "background_image": drawing_data.image_id,
            "drawing_name": drawing_data.drawing_name
        })
        
    except Exception as e:
        logger.error(f"Unexpected error in complete_drawing: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"서버 오류가 발생했습니다: {str(e)}"
        )
