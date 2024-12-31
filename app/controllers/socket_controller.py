from fastapi import WebSocket, APIRouter
from app.services.socket_service_impl import handle_websocket, handle_drawing_websocket
import logging
import json

logger = logging.getLogger(__name__)
router = APIRouter()



@router.websocket("/ws/drawing/{robot_id}/{canvas_id}")
async def websocket_endpoint(websocket: WebSocket, robot_id: str, canvas_id: str):
    await handle_websocket(websocket, robot_id, canvas_id)



@router.websocket("/drawing/send")
async def drawing_websocket_endpoint(websocket: WebSocket):
    await handle_drawing_websocket(websocket)



# @router.websocket("/drawing/send")
# async def drawing_websocket_endpoint(websocket: WebSocket):
#     try:
#         logger.info("Drawing WebSocket connection attempt received")
#         await websocket.accept()
#         logger.info("Drawing WebSocket connection accepted")
        
#         while True:
#             try:
#                 # 클라이언트로부터 메시지 수신
#                 data = await websocket.receive_text()
#                 logger.info(f"Received message: {data}")
                
#                 # JSON 파싱
#                 message = json.loads(data)
#                 logger.info(f"Parsed message: {message}")
                
#                 # 메시지 처리 및 응답
#                 response = {
#                     "status": "success",
#                     "message": "Drawing received",
#                     "received_data": message
#                 }
                
#                 # 응답 전송
#                 await websocket.send_text(json.dumps(response))
#                 logger.info(f"Sent response: {response}")
                
#             except json.JSONDecodeError as e:
#                 logger.error(f"JSON decode error: {str(e)}")
#                 await websocket.send_text(json.dumps({
#                     "status": "error",
#                     "message": "Invalid JSON format"
#                 }))
                
#     except Exception as e:
#         logger.error(f"Error in WebSocket connection: {str(e)}")
#         raise







