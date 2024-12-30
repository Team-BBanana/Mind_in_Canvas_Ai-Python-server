from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import base64
from app.services.drawing_service.dependencies import get_drawing_service

class ConnectionManager:
    def __init__(self):
        # canvas_id를 키로 사용하는 연결 관리
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, canvas_id: str):
        await websocket.accept()
        if canvas_id not in self.active_connections:
            self.active_connections[canvas_id] = []
        self.active_connections[canvas_id].append(websocket)

    def disconnect(self, websocket: WebSocket, canvas_id: str):
        if canvas_id in self.active_connections:
            self.active_connections[canvas_id].remove(websocket)
            if not self.active_connections[canvas_id]:
                del self.active_connections[canvas_id]

    async def broadcast_to_canvas(self, message: str, canvas_id: str):
        if canvas_id in self.active_connections:
            for connection in self.active_connections[canvas_id]:
                await connection.send_text(message)

manager = ConnectionManager()

async def handle_websocket(websocket: WebSocket, robot_id: str, canvas_id: str):
    await manager.connect(websocket, canvas_id)
    drawing_service = get_drawing_service()
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "voice":
                # 음성 데이터 처리
                audio_data = base64.b64decode(message["audio_data"])
                
                # 오디오 처리 및 응답 생성
                result = await drawing_service.process_audio(audio_data, robot_id, canvas_id)
                
                # 응답 전송
                response = {
                    "type": "voice",
                    "text": result.text,
                    "audio_data": base64.b64encode(result.audio_data).decode('utf-8')
                }
                await websocket.send_text(json.dumps(response))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, canvas_id)
    except Exception as e:
        print(f"Error in websocket handler: {str(e)}")
        manager.disconnect(websocket, canvas_id) 