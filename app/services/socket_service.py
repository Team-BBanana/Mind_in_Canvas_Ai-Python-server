# WebSocket 연결과 비동기 처리를 위한 FastAPI 컴포넌트 임포트
from fastapi import WebSocket, WebSocketDisconnect
# 타입 힌팅을 위한 Dict, List 임포트
from typing import Dict, List
# JSON 데이터 처리를 위한 모듈 임포트
import json
# base64 인코딩/디코딩을 위한 모듈 임포트
import base64
# 드로잉 서비스 의존성 가져오기
from app.services.drawing_service.dependencies import get_drawing_service
# 드로잉 관련 데이터 모델 임포트
from app.models.drawing import DrawingSocketRequest, DrawingAnalysis
# OpenAI API 클라이언트 임포트
from openai import OpenAI
# OpenAI API 키 설정 임포트
from app.config import OPENAI_API_KEY


# WebSocket 연결을 관리하는 클래스
class ConnectionManager:
    def __init__(self):
        # canvas_id별로 WebSocket 연결을 저장하는 딕셔너리 초기화
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, canvas_id: str):
        # 새로운 WebSocket 연결 수락
        await websocket.accept()
        # 해당 canvas_id에 대한 연결 리스트가 없으면 생성
        if canvas_id not in self.active_connections:
            self.active_connections[canvas_id] = []
        # WebSocket 연결을 리스트에 추가
        self.active_connections[canvas_id].append(websocket)

    def disconnect(self, websocket: WebSocket, canvas_id: str):
        # canvas_id에 해당하는 연결이 있는 경우
        if canvas_id in self.active_connections:
            # WebSocket 연결 제거
            self.active_connections[canvas_id].remove(websocket)
            # 해당 canvas_id의 모든 연결이 끊어진 경우 키 삭제
            if not self.active_connections[canvas_id]:
                del self.active_connections[canvas_id]

    async def broadcast_to_canvas(self, message: str, canvas_id: str):
        # 특정 canvas_id에 연결된 모든 클라이언트에게 메시지 브로드캐스트
        if canvas_id in self.active_connections:
            for connection in self.active_connections[canvas_id]:
                await connection.send_text(message)

# ConnectionManager 인스턴스 생성
manager = ConnectionManager()


# 음성 메시지를 처리하는 WebSocket 핸들러
async def handle_websocket(websocket: WebSocket, robot_id: str, canvas_id: str):
    # WebSocket 연결 설정
    await manager.connect(websocket, canvas_id)
    # 드로잉 서비스 인스턴스 가져오기
    drawing_service = get_drawing_service()
    
    try:
        while True:
            # 클라이언트로부터 데이터 수신
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "voice":
                # base64 인코딩된 음성 데이터를 디코딩
                audio_data = base64.b64decode(message["audio_data"])
                
                # 음성 데이터 처리 및 응답 생성
                result = await drawing_service.process_audio(audio_data, robot_id, canvas_id)
                
                # 처리된 결과를 클라이언트에게 전송
                response = {
                    "type": "voice",
                    "text": result.text,
                    "audio_data": base64.b64encode(result.audio_data).decode('utf-8')
                }
                await websocket.send_text(json.dumps(response))
                
    except WebSocketDisconnect:
        # WebSocket 연결 종료 시 연결 해제
        manager.disconnect(websocket, canvas_id)
    except Exception as e:
        # 기타 예외 발생 시 에러 로깅 및 연결 해제
        print(f"Error in websocket handler: {str(e)}")
        manager.disconnect(websocket, canvas_id)


# 그림 분석을 처리하는 WebSocket 핸들러
async def handle_drawing_websocket(websocket: WebSocket):
    # WebSocket 연결 수락
    await websocket.accept()
    # 드로잉 서비스 및 OpenAI 클라이언트 초기화
    drawing_service = get_drawing_service()
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    try:
        # 클라이언트로부터 초기 연결 데이터 수신
        data = await websocket.receive_json()
        request = DrawingSocketRequest(**data)
        
        # 연결 성공 응답 전송
        await websocket.send_json({"status": "success"})
        
        # 지속적인 이미지 업데이트 처리 루프
        while True:
            # 이미지 URL 수신
            data = await websocket.receive_json()
            image_url = data.get("image_url")
            if not image_url:
                continue
                
            try:
                # GPT-4 Vision API를 사용하여 이미지 분석 요청
                response = client.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "이 그림을 분석해주세요. 다음 정보가 필요합니다:\n1. 사용된 주요 색상들\n2. 그림에서 느껴지는 감정\n3. 그림의 주요 내용\n4. 대화를 이어가기 위한 문맥 정보"
                                },
                                {
                                    "type": "image_url",
                                    "image_url": image_url
                                }
                            ]
                        }
                    ],
                    max_tokens=500
                )
                
                # GPT 응답 텍스트 추출
                analysis_text = response.choices[0].message.content
                
                # 분석 텍스트를 구조화된 데이터로 파싱
                lines = analysis_text.split('\n')
                colors = []
                emotion = ""
                content = ""
                context = ""
                
                # 각 라인을 분석하여 해당하는 카테고리에 데이터 저장
                for line in lines:
                    if "색상" in line:
                        colors = [color.strip() for color in line.split(':')[1].split(',')]
                    elif "감정" in line:
                        emotion = line.split(':')[1].strip()
                    elif "내용" in line:
                        content = line.split(':')[1].strip()
                    elif "문맥" in line:
                        context = line.split(':')[1].strip()
                
                # 분석 결과를 DrawingAnalysis 객체로 생성
                analysis = DrawingAnalysis(
                    colors=colors,
                    emotion=emotion,
                    content=content,
                    context=context
                )
                
                # 분석 결과를 드로잉 서비스에 저장
                drawing_data = drawing_service.drawing_data.get(request.canvas_id)
                if drawing_data:
                    drawing_data.update_image(image_url)
                    drawing_data.add_analysis(analysis)
                
            except Exception as e:
                # 이미지 분석 중 에러 발생 시 로깅하고 계속 진행
                print(f"Error analyzing image: {str(e)}")
                continue
                
    except WebSocketDisconnect:
        # 클라이언트 연결 종료 시 로깅
        print(f"Client disconnected")
    except Exception as e:
        # 기타 예외 발생 시 에러 로깅 및 연결 종료
        print(f"Error in drawing websocket handler: {str(e)}")
        await websocket.close() 