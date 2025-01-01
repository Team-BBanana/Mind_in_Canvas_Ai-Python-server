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
from app.models.drawing import DrawingAnalysis, DrawingData
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
            
            elif message["type"] == "image":
                try:
                    # 이미지 데이터 확인
                    image_base64 = message.get("image_data")
                    if not image_base64:
                        continue
                    
                    # 1. GPT-4 Vision으로 이미지 분석
                    vision_response = client.chat.completions.create(
                        model="gpt-4-vision-preview",
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "이 그림을 분석해주세요. 다음 정보가 필요합니다:\n1. 사용된 주요 색상들\n2. 그림에서 느껴지는 감정\n3. 그림의 주요 내용\n4. 대화를 이어가기 위한 문맥 정보"},
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
                            ]
                        }],
                        max_tokens=500
                    )
                    
                    analysis_text = vision_response.choices[0].message.content
                    
                    # 2. 분석 결과를 구조화된 데이터로 파싱
                    lines = analysis_text.split('\n')
                    colors = []
                    emotion = ""
                    content = ""
                    context = ""
                    
                    for line in lines:
                        if "색상" in line:
                            colors = [color.strip() for color in line.split(':')[1].split(',')]
                        elif "감정" in line:
                            emotion = line.split(':')[1].strip()
                        elif "내용" in line:
                            content = line.split(':')[1].strip()
                        elif "문맥" in line:
                            context = line.split(':')[1].strip()
                    
                    drawing_data = drawing_service.drawing_data.get(canvas_id)
                    if drawing_data:
                        
                        feedback_response = client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[
                                {
                                    "role": "system",
                                    "content": "당신은 아이들의 그림을 보고 따뜻한 정서적 피드백을 제공하는 AI 선생님입니다. 아이의 감정을 이해하고, 그림을 더 발전시킬 수 있도록 격려하는 메시지를 2-3문장으로 생성해주세요."
                                },
                                {
                                    "role": "user",
                                    "content": f"아이의 이름: {drawing_data.name}\n나이: {drawing_data.age if drawing_data.age else '미상'}\n분석 결과:\n- 색상: {', '.join(colors)}\n- 감정: {emotion}\n- 내용: {content}\n- 문맥: {context}"
                                }
                            ]
                        )
                        
                        feedback_text = feedback_response.choices[0].message.content
                        drawing_data.add_message("assistant", feedback_text)
                        
                        # 4. 피드백을 TTS로 음성 변환
                        audio_response = client.audio.speech.create(
                            model="tts-1",
                            voice="nova",
                            input=feedback_text,
                            speed=1.0
                        )
                        
                        # 5. 같은 canvas_id를 사용하는 클라이언트에게 음성 피드백 전송
                        voice_message = {
                            "type": "voice",
                            "text": feedback_text,
                            "audio_data": base64.b64encode(audio_response.content).decode('utf-8'),
                            "is_user": False
                        }
                        await manager.broadcast_to_canvas(json.dumps(voice_message), canvas_id)
                        
                except Exception as e:
                    print(f"이미지 처리 중 오류 발생: {str(e)}")
                    error_response = {
                        "status": "error",
                        "message": f"이미지 처리 중 오류 발생: {str(e)}"
                    }
                    await websocket.send_text(json.dumps(error_response))
                
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
    # WebSocket 연결 수락
    print("\n[WebSocket] 연결 시도 감지됨")
    await websocket.accept()
    print("[WebSocket] 연결 수락됨")
    
    # 드로잉 서비스 및 OpenAI 클라이언트 초기화
    drawing_service = get_drawing_service()
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    try:
        # 클라이언트로부터 초기 연결 데이터 수신
        data = await websocket.receive_json()
        print(f"\n[WebSocket] 수신된 메시지: {data}")
        request = DrawingSocketRequest(**data)
        
        # 연결 성공 응답 전송
        response = {"status": "success"}
        await websocket.send_json(response)
        print(f"[WebSocket] 전송된 응답: {response}")
        
        # 지속적인 이미지 업데이트 처리 루프
        while True:
            try:
                # 이미지 데이터 수신
                data = await websocket.receive_json()
                print(f"\n[WebSocket] 수신된 메시지: {data}")
                
                # base64 이미지 데이터 확인
                image_base64 = data.get("image_data")
                if image_base64:
                    # 이미지를 handle_websocket으로 전달
                    await manager.forward_image(request.canvas_id, image_base64)
                    
                    # 성공 응답 전송
                    response = {"status": "success", "message": "Image forwarded"}
                    await websocket.send_json(response)
                    print(f"[WebSocket] 전송된 응답: {response}")
                    continue
                    
                try:
                    print(f"[WebSocket] 이미지 분석 시작")
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
                                        "image_url": {
                                            "url": f"data:image/png;base64,{image_base64}"
                                        }
                                    }
                                ]
                            }
                        ],
                        max_tokens=500
                    )
                    
                    # GPT 응답 텍스트 추출
                    analysis_text = response.choices[0].message.content
                    print(f"[WebSocket] GPT 분석 결과: {analysis_text}")
                    
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
                    print(f"[WebSocket] 분석 결과 객체 생성: {analysis}")
                    
                    # 분석 결과를 드로잉 서비스에 저장
                    drawing_data = drawing_service.drawing_data.get(request.canvas_id)
                    if drawing_data:
                        drawing_data.update_image(f"data:image/png;base64,{image_base64}")
                        drawing_data.add_analysis(analysis)
                        print(f"[WebSocket] 분석 결과 저장 완료: canvas_id={request.canvas_id}")
                    
                    # 분석 결과 응답 전송
                    analysis_response = {
                        "status": "success",
                        "analysis": {
                            "colors": colors,
                            "emotion": emotion,
                            "content": content,
                            "context": context
                        }
                    }
                    await websocket.send_json(analysis_response)
                    print(f"[WebSocket] 분석 결과 전송 완료")
                    
                except Exception as e:
                    print(f"\n[WebSocket] 이미지 분석 에러: {str(e)}")
                    error_response = {
                        "status": "error",
                        "message": f"이미지 분석 중 오류 발생: {str(e)}"
                    }
                    await websocket.send_json(error_response)
                    continue
                    
            except json.JSONDecodeError as e:
                print(f"\n[WebSocket] JSON 디코딩 에러: {str(e)}")
                error_response = {
                    "status": "error",
                    "message": "Invalid JSON format"
                }
                await websocket.send_json(error_response)
                print(f"[WebSocket] 에러 응답 전송: {error_response}")
                
    except WebSocketDisconnect:
        print(f"\n[WebSocket] 클라이언트 연결 종료")
    except Exception as e:
        print(f"\n[WebSocket] 에러 발생: {str(e)}")
        await websocket.close() 