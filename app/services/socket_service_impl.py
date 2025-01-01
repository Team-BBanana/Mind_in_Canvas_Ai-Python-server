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
from app.models.drawing import DrawingAnalysis, DrawingSocketRequest
# OpenAI API 클라이언트 임포트
from openai import OpenAI
# OpenAI API 키 설정 임포트
from app.config import OPENAI_API_KEY
import tempfile
import os


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

    async def forward_image(self, canvas_id: str, image_data: str):
        """이미지 데이터를 해당 canvas_id의 WebSocket 연결로 전달"""
        if canvas_id in self.active_connections:
            message = {
                "type": "image",
                "image_data": image_data
            }
            await self.broadcast_to_canvas(json.dumps(message), canvas_id)

# ConnectionManager 인스턴스 생성
manager = ConnectionManager()


# 음성 메시지를 처리하는 WebSocket 핸들러
async def handle_websocket(websocket: WebSocket, robot_id: str, canvas_id: str):
    # WebSocket 연결 설정
    await manager.connect(websocket, canvas_id)
    # 드로잉 서비스 인스턴스 가져오기
    drawing_service = get_drawing_service()
    # OpenAI 클라이언트 초기화
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    try:
        while True:
            # 클라이언트로부터 데이터 수신
            data = await websocket.receive_text()
            print(f"[WebSocket] 수신된 메시지: {data}")
            message = json.loads(data)
            
            if message["type"] == "voice":
                # base64 인코딩된 음성 데이터를 디코딩
                audio_data = base64.b64decode(message["audio_data"])
                
                # 오디오 처리 및 응답 생성
                result = await drawing_service.process_audio(audio_data, robot_id, canvas_id)
                
                # 사용자의 음성을 텍스트로 변환
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    temp_file.write(audio_data)
                    temp_file_path = temp_file.name
                
                try:
                    # 음성을 텍스트로 변환
                    with open(temp_file_path, 'rb') as audio_file:
                        transcript = drawing_service.client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file
                        )
                    user_text = transcript.text
                    
                    # 사용자 메시지를 저장소에 저장
                    # 1. drawing_service의 drawing_data 딕셔너리에서 현재 canvas_id에 해당하는 데이터를 조회
                    # 2. drawing_data가 존재하는 경우에만 메시지 저장을 진행
                    # 3. 사용자의 음성이 텍스트로 변환된 내용(user_text)을 채팅 이력에 추가
                    # 4. add_message 메서드를 통해 role은 "user"로, content는 변환된 텍스트로 저장
                    drawing_data = drawing_service.drawing_data.get(canvas_id)
                    if drawing_data:
                        drawing_data.add_message("user", user_text)
                    
                    # 사용자 메시지를 클라이언트에 전송
                    user_message = {
                        "type": "voice",
                        "text": user_text,
                        "is_user": True
                    }
                    await websocket.send_text(json.dumps(user_message))
                    
                    # AI 응답 전송
                    response = {
                        "type": "voice",
                        "text": result.text,
                        "audio_data": base64.b64encode(result.audio_data).decode('utf-8'),
                        "is_user": False
                    }
                    await websocket.send_text(json.dumps(response))
                    
                finally:
                    os.unlink(temp_file_path)
            
                
    except WebSocketDisconnect:
        # WebSocket 연결 종료 시 연결 해제
        print(f"\n[WebSocket] 클라이언트 연결 종료")
        manager.disconnect(websocket, canvas_id)
    except Exception as e:
        # 기타 예외 발생 시 에러 로깅 및 연결 해제
        print(f"Error in websocket handler: {str(e)}")
        manager.disconnect(websocket, canvas_id)



# 그림 분석을 처리하는 WebSocket 핸들러
async def handle_drawing_websocket(websocket: WebSocket):
    print("\n[WebSocket] 연결 시도 감지됨")
    await websocket.accept()
    print("[WebSocket] 연결 수락됨")
    
    drawing_service = get_drawing_service()
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    try:
        data = await websocket.receive_json()
        print(f"\n[WebSocket] 수신된 메시지: {data}")
        request = DrawingSocketRequest(**data)
        
        response = {"status": "success"}
        await websocket.send_json(response)
        print(f"[WebSocket] 전송된 응답: {response}")
        
        while True:
            data = await websocket.receive_json()
            print(f"\n[WebSocket] 메시지 수신")
            
            image_base64 = data.get("image_url")
            if not image_base64:
                continue
                
            print(f"[WebSocket] 이미지 분석 시작")
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """당신은 3~7세 아이들의 둘도 없는 친구입니다.
                        어린 아이의 시각에서 자연스럽게 어울리고 대화할 수 있습니다.
                        반말을 쓰며 친구답게 대화합니다.
                        
                        다음과 같은 특성과 전문성을 가지고 있습니다:
                        1. 따뜻하고 공감적인 태도로 아이들의 감정을 섬세하게 인지하고 반응합니다.
                        2. 아이의 발달 단계에 맞는 적절한 언어와 표현을 사용합니다. 
                        3. 긍정적인 강화와 격려를 통해 아이의 자존감을 높여줍니다.
                        4. 감정 코칭 전문가로서 아이의 감정을 인정하고 표현하도록 도와줍니다.
                        5. 놀이를 통한 치료적 접근을 활용합니다.
                        
                        대화 시 반드시 지켜야 할 규칙:
                        - 한 번의 응답에서 1-2개의 짧은 문장만 사용하도록 최대한 노력합니다.
                        - 아이가 이해하기 쉬운 단순한 단어를 선택합니다.
                        - 따뜻하고 친근한 어조를 유지합니다.
                        - 아이의 감정을 먼저 인정하고 공감합니다.
                        - 긍정적인 피드백을 제공합니다.
                        - 답변이 길어질 것 같으면 여러 번의 짧은 대화로 나눕니다."""
                    },
                    {
                        "role": "user",
                        "content": "이 그림에 대해 아이와 대화하듯이 친근하게 피드백해주세요. 반드시 1~3문장으로만 답변해주세요. 더 길게 답변하지 마세요."
                    }
                ]
            )
            
            feedback_text = response.choices[0].message.content
            print(f"[WebSocket] GPT 분석 결과: {feedback_text}")
            
            drawing_data = drawing_service.drawing_data.get(request.canvas_id)
            if drawing_data:
                drawing_data.update_image(f"data:image/png;base64,{image_base64}")
                drawing_data.add_analysis(feedback_text)
                print(f"[WebSocket] 분석 결과 저장 완료: canvas_id={request.canvas_id}")
            
            analysis_response = {
                "status": "success",
                "analysis": feedback_text
            }
            await websocket.send_json(analysis_response)
            print(f"[WebSocket] 분석 결과 전송 완료")
                
    except WebSocketDisconnect:
        print(f"\n[WebSocket] 클라이언트 연결 종료")
    except Exception as e:
        print(f"\n[WebSocket] 에러 발생: {str(e)}")
        await websocket.close() 