from fastapi import WebSocket, APIRouter
from app.services.socket_service import handle_websocket, handle_drawing_websocket

router = APIRouter()

@router.websocket("/ws/drawing/{robot_id}/{canvas_id}")
async def websocket_endpoint(websocket: WebSocket, robot_id: str, canvas_id: str):
    await handle_websocket(websocket, robot_id, canvas_id)

@router.websocket("/drawing/send")
async def drawing_websocket_endpoint(websocket: WebSocket):
    await handle_drawing_websocket(websocket)







