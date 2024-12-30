# 필요한 타입 힌팅을 위한 Dict 임포트
from typing import Dict
# OpenAI API 클라이언트 사용을 위한 임포트
from openai import OpenAI
# 서비스 인터페이스와 오디오 처리 결과 타입 임포트
from app.services.drawing_service.drawing_service import DrawingService, AudioProcessingResult
# 그림 관련 데이터 모델 클래스들 임포트
from app.models.drawing import NewDrawingRequest, DrawingData
# OpenAI API 키 설정값 임포트
from app.config import OPENAI_API_KEY
# 임시 파일 생성을 위한 모듈 임포트
import tempfile
# 파일 시스템 작업을 위한 모듈 임포트
import os
# 로깅 기능을 위한 모듈 임포트
import logging

# 이 모듈의 로거 인스턴스 생성
logger = logging.getLogger(__name__)


# DrawingService 인터페이스를 구현하는 실제 서비스 클래스
class DrawingServiceImpl(DrawingService):

    # 그림 데이터 저장소 초기화
    # 초기화 메서드
    # 초기화 중 발생한 에러 로깅 및 재발생
    # OpenAI API 클라이언트 초기화
    # API 키가 설정되지 않았다면 에러 발생
    # 캔버스 ID를 키로 사용하는 그림 데이터 저장소 초기화  
    def __init__(self):
        try:
            # OpenAI API 클라이언트 초기화
            self.client = OpenAI(api_key=OPENAI_API_KEY)
            # API 키가 설정되지 않았다면 에러 발생
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다")
            # 캔버스 ID를 키로 사용하는 그림 데이터 저장소 초기화
            self.drawing_data: Dict[str, DrawingData] = {}
        except Exception as e:
            # 초기화 중 발생한 에러 로깅 및 재발생
            logger.error(f"DrawingServiceImpl 초기화 오류: {str(e)}", exc_info=True)
            raise




    # 텍스트를 음성으로 변환하는 유틸리티 메서드
    def _create_tts_response(self, text: str) -> bytes:
        """TTS 응답을 생성하는 공통 함수"""
        # OpenAI TTS API를 호출하여 음성 생성
        speech_response = self.client.audio.speech.create(
            model="tts-1",      # 사용할 TTS 모델
            voice="nova",       # 음성 화자 설정
            input=text,         # 변환할 텍스트
            speed=1.0           # 음성 재생 속도
        )
        # 생성된 음성 데이터 반환
        return speech_response.content



    # 새로운 그림 그리기 세션을 시작하는 메서드
    async def handle_new_drawing(self, request: NewDrawingRequest) -> str:
        try:
            # 새 그림 요청 처리 시작 로깅
            logger.info(f"Processing new drawing request for canvas_id: {request.canvas_id}")
            
            # 새로운 그림 데이터 객체 생성 및 저장
            drawing_data = DrawingData(
                robot_id=request.robot_id,
                name=request.name,
                age=request.age,
                canvas_id=request.canvas_id
            )
            # 캔버스 ID로 데이터 저장
            self.drawing_data[request.canvas_id] = drawing_data
            # 데이터 저장 완료 로깅
            logger.debug(f"Drawing data stored for canvas_id: {request.canvas_id}")

            # 사용자 나이에 따른 초기 인사말 텍스트 생성
            age_text = f"{request.age}살" if request.age else "어린"
            initial_text = f"""안녕!, 귀여운 {age_text} 나이의 {request.name} 친구야!!
                            만나서 너무 반가워!!  
                            오늘 우리 함께 재미있는 그림을 그려볼까요? 
                            어떤 멋진 그림을 그리고 싶은지 이야기해주세요!"""
            
            # 생성된 텍스트를 데이터에 저장
            drawing_data.prompt = initial_text
            # 대화 기록에 AI 메시지로 추가
            drawing_data.add_message("ai", initial_text)
            # 초기 텍스트 생성 로깅
            logger.debug(f"Generated initial text for canvas_id {request.canvas_id}: {drawing_data.prompt}")

            # 텍스트를 음성으로 변환하여 저장
            drawing_data.audio_data = self._create_tts_response(initial_text)
            # 성공적인 처리 완료 로깅
            logger.info(f"Successfully processed new drawing request for canvas_id: {request.canvas_id}")

            # 성공 상태 반환
            return "success"

        except Exception as e:
            # 에러 발생 시 로깅 및 에러 메시지 반환
            logger.error(f"Error in handle_new_drawing: {str(e)}", exc_info=True)
            return f"error: {str(e)}"




    # 사용자의 음성 입력을 처리하고 응답하는 메서드
    async def process_audio(self, audio_data: bytes, robot_id: str, canvas_id: str) -> AudioProcessingResult:
        try:
            # 오디오 처리 시작 로깅
            logger.info(f"Processing audio for canvas_id: {canvas_id}")
            # 캔버스 ID로 그림 데이터 조회
            drawing_data = self.drawing_data.get(canvas_id)
            # 데이터가 없으면 에러 발생
            if not drawing_data:
                raise ValueError(f"Drawing data not found for canvas_id: {canvas_id}")
            
            # 음성 데이터를 임시 WAV 파일로 저장
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
                # 임시 파일 생성 로깅
                logger.debug(f"Created temporary file: {temp_file_path}")

            try:
                # 음성을 텍스트로 변환 (Speech-to-Text)
                with open(temp_file_path, 'rb') as audio_file:
                    transcript = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                # 변환된 텍스트 저장
                user_text = transcript.text
                # 사용자 메시지를 대화 기록에 추가
                drawing_data.add_message("user", user_text)
                # 변환된 텍스트 로깅
                logger.debug(f"Transcribed text: {user_text}")

                # GPT 모델을 사용하여 응답 생성
                chat_response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": """당신은 아이들과 대화하는 친근한 AI 선생님입니다.
                        아이의 이야기에 대해 짧고 긍정적인 정서적 피드백만 제공하세요.
                        그림에 대한 구체적인 제안이나 수정사항은 언급하지 말고,
                        아이의 감정과 생각을 지지하고 격려하는 답변만 해주세요.
                        답변은 1-2문장으로 매우 짧게 해주세요."""},
                        {"role": "user", "content": user_text}
                    ]
                )
                # GPT 응답 텍스트 추출
                response_text = chat_response.choices[0].message.content
                # AI 응답을 대화 기록에 추가
                drawing_data.add_message("ai", response_text)
                # 생성된 응답 로깅
                logger.debug(f"Generated response: {response_text}")

                # 응답 텍스트를 음성으로 변환
                audio_content = self._create_tts_response(response_text)
                # 성공적인 처리 완료 로깅
                logger.info(f"Successfully processed audio for canvas_id: {canvas_id}")

                # 처리 결과 반환
                return AudioProcessingResult(
                    text=response_text,
                    audio_data=audio_content
                )

            finally:
                # 임시 파일 삭제
                os.unlink(temp_file_path)
                # 파일 삭제 로깅
                logger.debug(f"Deleted temporary file: {temp_file_path}")

        except Exception as e:
            # 에러 발생 시 로깅
            logger.error(f"Error processing audio: {str(e)}", exc_info=True)
            # 기본 에러 응답 메시지
            error_text = "죄송해요, 잘 이해하지 못했어요. 다시 한 번 말씀해 주시겠어요?"
            if drawing_data:
                # 에러 메시지를 대화 기록에 추가
                drawing_data.add_message("ai", error_text)
            try:
                # 에러 메시지를 음성으로 변환
                audio_content = self._create_tts_response(error_text)
                return AudioProcessingResult(
                    text=error_text,
                    audio_data=audio_content
                )
            except Exception as tts_error:
                # TTS 변환 실패 시 로깅 및 에러 발생
                logger.error(f"Error generating error response: {str(tts_error)}", exc_info=True)
                raise






    # # 프롬프트 생성을 위한 헬퍼 메서드 (현재 주석 처리됨)
    # def _create_prompt_request(self, data: DrawingData) -> str:
    #     age_text = f"{data.age}살" if data.age else "어린이"
    #     return f"""
    #     {data.name}라는 {age_text} 아이가 그림을 그리려고 합니다.
    #     아이의 흥미를 유발하고 창의력을 자극할 수 있도록, 그림 그리기를 시작하기 전에
    #     아이에게 해줄 말을 만들어주세요. 다음 내용을 포함해주세요:
    #     1. 아이의 이름을 부르며 친근하게 인사
    #     2. 그림 그리기의 즐거움에 대한 이야기
    #     3. 아이의 상상력을 자극할 수 있는 질문이나 제안
    #     4. 응원과 격려의 메시지
        
    #     답변은 2-3문장으로 짧고 명확하게 해주세요.
    #     """
    #     """