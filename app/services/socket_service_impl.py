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
    
    # 초기화 시 canvas_id별로 WebSocket 연결을 저장하는 딕셔너리 초기화
    # 음성 처리를 위한 WebSocket 연결 저장
    # canvas_id별 텍스트 저장
    def __init__(self):
        # canvas_id별로 WebSocket 연결을 저장하는 딕셔너리 초기화
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # 음성 처리를 위한 WebSocket 연결 저장
        self.voice_connections: Dict[str, WebSocket] = {}
        # canvas_id별 텍스트 저장
        self.text_storage: Dict[str, str] = {}


    # WebSocket 연결 수립
    async def connect(self, websocket: WebSocket, canvas_id: str, is_voice=False):
        await websocket.accept()
        if is_voice:
            self.voice_connections[canvas_id] = websocket
        else:
            if canvas_id not in self.active_connections:
                self.active_connections[canvas_id] = []
            self.active_connections[canvas_id].append(websocket)


    # WebSocket 연결 해제
    def disconnect(self, websocket: WebSocket, canvas_id: str, is_voice=False):
        if is_voice:
            if canvas_id in self.voice_connections:
                del self.voice_connections[canvas_id]
        else:
            if canvas_id in self.active_connections:
                self.active_connections[canvas_id].remove(websocket)
                if not self.active_connections[canvas_id]:
                    del self.active_connections[canvas_id]
                 
                    
    # 텍스트 저장
    def store_text(self, canvas_id: str, text: str):
        self.text_storage[canvas_id] = text
        print(f"[텍스트 저장] canvas_id: {canvas_id}, text: {text}")
        
        
    # 텍스트 조회
    def get_text(self, canvas_id: str) -> str:
        return self.text_storage.get(canvas_id)


    
# ConnectionManager 인스턴스 생성
manager = ConnectionManager()


# 음성 메시지를 처리하는 WebSocket 핸들러
async def handle_websocket(websocket: WebSocket, robot_id: str, canvas_id: str):
    
    # WebSocket 연결 수립
    await manager.connect(websocket, canvas_id, is_voice=True)
    
    # 드로잉 서비스 인스턴스 생성
    drawing_service = get_drawing_service()
    
    # OpenAI API 클라이언트 생성
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    try:
        while True:
            # 저장된 텍스트 확인
            text = manager.get_text(canvas_id)
            
            # 텍스트가 있으면
            if text:
                # TTS 변환
                print(f"[WebSocket] TTS 변환 시작: {text}")
                audio_response = client.audio.speech.create(
                    model="tts-1",
                    voice="nova",
                    input=text,
                    speed=1.0
                )
                
                # 음성 응답 전송
                response = {
                    "type": "voice",
                    "text": text,
                    "audio_data": base64.b64encode(audio_response.content).decode('utf-8'),
                    "is_user": False
                }
                await websocket.send_text(json.dumps(response))
                
                print("[WebSocket] 음성 응답 전송 완료")
                
                # 텍스트 삭제 (한 번 전송 후)
                manager.text_storage.pop(canvas_id, None)
                continue  # 다음 루프로 바로 넘어감
            
            # 클라이언트로부터 데이터 수신
            data = await websocket.receive_text()
            # print(f"[WebSocket] 수신된 메시지: {data}")
            message = json.loads(data)
            
            # 클라이언트로부터 데이터 수신
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
                    
                    # 드로잉 데이터 조회
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
                
                # 임시 파일 삭제
                finally:
                    os.unlink(temp_file_path)
            
    # 클라이언트 연결 종료  
    except WebSocketDisconnect:
        print(f"\n[WebSocket] 클라이언트 연결 종료")
        manager.disconnect(websocket, canvas_id, is_voice=True)
        
        

# 그림 분석을 처리하는 WebSocket 핸들러
async def handle_drawing_websocket(websocket: WebSocket):
    print("\n[WebSocket] 연결 시도 감지됨")
    await websocket.accept()
    print("[WebSocket] 연결 수락됨")
    
    # 드로잉 서비스 인스턴스 생성
    drawing_service = get_drawing_service()
    
    # OpenAI API 클라이언트 생성
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    
    # 클라이언트로부터 데이터 수신
    try:
        data = await websocket.receive_json()
        print(f"\n[WebSocket] 수신된 메시지: {data}")
        request = DrawingSocketRequest(**data)
        canvas_id = request.canvas_id
        
        
        # 피드백 요청 메시지 전송
        response = {"status": "success"}
        await websocket.send_json(response)
        print(f"[WebSocket] 전송된 응답: {response}")
        
        
        while True:
            # 클라이언트로부터 데이터 수신
            data = await websocket.receive_json()
            print(f"\n[WebSocket] 메시지 수신")
            
            
            # 이미지 데이터 조회
            image_base64 = data.get("image_url")
            if not image_base64:
                continue
        
                
            # 이미지 분석 시작
            print(f"[WebSocket] 이미지 분석 시작")
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": """
                                    You are a close friend of children aged 3-7 years old.
                                    You can naturally interact and communicate from a child's perspective.
                                    You speak casually and friendly like a close friend.

                                    You have the following characteristics and expertise:
                                    1. You respond sensitively to children's emotions with a warm and empathetic attitude.
                                    2. You use appropriate language and expressions for the child's developmental stage.
                                    3. You enhance children's self-esteem through positive reinforcement and encouragement.
                                    4. As an emotional coaching expert, you help children recognize and express their emotions.
                                    5. You utilize therapeutic approaches through play.

                                    Rules that must be followed during conversation:
                                    - Try to use only 1-2 short sentences in each response.
                                    - Choose simple words that children can easily understand.
                                    - Maintain a warm and friendly tone.
                                    - First acknowledge and empathize with the child's emotions.
                                    - Provide positive feedback.
                                    - If the answer might get long, break it into multiple short conversations.
                                    - ALWAYS respond in Korean using casual, friendly language suitable for children.
                                    - Use Korean expressions and words that Korean children aged 3-7 can easily understand.
                                    - Your responses must ALWAYS be in Korean, regardless of the input language.
                                    """
                    },
                    {
                        "role": "user",
                        "content": f"Here is a drawing made by a child: {image_base64}\n\nPlease provide friendly feedback about this drawing as if you're talking to the child. Please respond with only 1-3 sentences in Korean. Use casual, friendly Korean language suitable for children. Do not make the response any longer."
                    }
                ],
                max_tokens=300
            )
            
            # 분석 결과 조회
            feedback_text = response.choices[0].message.content
            print(f"[WebSocket] GPT 분석 결과: {feedback_text}")
            
            # 텍스트 저장
            manager.store_text(canvas_id, feedback_text)
            
            # 분석 결과 응답 전송
            analysis_response = {
                "type": "ai_response",
                "status": "success",
                "text": feedback_text,
            }
            await websocket.send_json(analysis_response)
            print(f"[WebSocket] 분석 결과 전송 완료")
                
    except WebSocketDisconnect:
        print(f"\n[WebSocket] 클라이언트 연결 종료")
    except Exception as e:
        print(f"\n[WebSocket] 에러 발생: {str(e)}")
        await websocket.close() 