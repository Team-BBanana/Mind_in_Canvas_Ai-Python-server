from typing import Dict, Optional, List
from app.services.drawing_service.drawing_service import DrawingService, AudioProcessingResult
from app.models.drawing import NewDrawingRequest, DrawingData, DoneDrawingRequest, ChatMessage
from app.config import OPENAI_API_KEY
import tempfile
import sys
import os
import logging
import openai
import requests
import base64
from io import BytesIO
from PIL import Image

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))  # 추가된 코드


# 로깅 설정
logger = logging.getLogger(__name__)


class DrawingServiceImpl(DrawingService):
    def __init__(self):
        try:
            # OpenAI API 클라이언트 초기화
            self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다")
            
            # 캔버스 ID를 키로 사용하는 그림 데이터 저장소 초기화
            self.drawing_data: Dict[str, DrawingData] = {}
        
        except Exception as e:
            logger.error(f"DrawingServiceImpl 초기화 오류: {str(e)}", exc_info=True)
            raise

    # 🛠️ 공통 헬퍼 메서드

    def _handle_error(self, error: Exception, context: str) -> str:
        """공통 오류 처리 메서드"""
        logger.error(f"Error in {context}: {str(error)}", exc_info=True)
        return f"error: {str(error)}"

    def _generate_initial_text(self, name: str, age: Optional[int]) -> str:
        """초기 대화 텍스트 생성"""
        age_text = f"{age}살" if age else "어린"
        return (
            f"안녕!, 귀여운 {age_text} 나이의 {name} 친구야!! 만나서 너무 반가워!! "
            f"오늘 우리 함께 재미있는 그림을 그려볼까요? 어떤 멋진 그림을 그리고 싶은지 이야기해주세요!"
        )

    def _generate_ai_response(self, user_text: str) -> str:
        """AI 모델을 통해 응답 생성"""
        chat_response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "당신은 아이들과 대화하는 친근한 AI 선생님입니다."},
                {"role": "user", "content": user_text}
            ]
        )
        return chat_response.choices[0].message.content

    def _create_tts_response(self, text: str) -> bytes:
        """TTS 응답을 생성"""
        speech_response = openai.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=text,
            speed=1.0
        )
        return speech_response.content

    # 🧠 GPT-3.5-Turbo를 사용한 대화 요약
    def _summarize_conversation(self, chat_history: List[ChatMessage]) -> str:
        """대화 기록을 요약합니다 (GPT-3.5-Turbo 사용)."""
        try:
            if not chat_history:
                return "대화 기록이 존재하지 않습니다."

            messages = [{"role": msg.role, "content": msg.text} for msg in chat_history]

            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "다음 대화 내용을 요약해 주세요."}
                ] + messages
            )
            summary = response.choices[0].message.content.strip()
            logger.debug(f"Conversation summary: {summary}")
            return summary
        
        except Exception as e:
            return self._handle_error(e, "_summarize_conversation")

    # 🧠 GPT-4-Turbo를 사용한 이미지 분석
    def _analyze_final_image(self, image_url: str, chat_history: List[ChatMessage]) -> str:
        """이미지 분석을 수행합니다 (GPT-4-Turbo 사용)."""
        try:
            logger.info(f"Downloading image from S3: {image_url}")

            # 1. S3에서 이미지 다운로드
            response = requests.get(image_url)
            if response.status_code != 200:
                raise ValueError(f"Failed to download image from S3. Status code: {response.status_code}")
            
            image_data = BytesIO(response.content)
            image_base64 = base64.b64encode(image_data.getvalue()).decode('utf-8')
            
            logger.info("Successfully downloaded and encoded the image from S3.")

            # chat_history를 문자열로 변환
            conversation = "\n".join([f"{msg.role}: {msg.text}" for msg in chat_history])
            
            response = openai.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": """
                        당신은 3~7세 아이들의 둘도 없는 친구입니다.
                        어린 아이의 시각에서 자연스럽게 아이의 그림을 이해하고 피드백 할 수 있습니다.
                        아이의 그림에 대해서 1~2 문장 내외의 따뜻한 피드백을 제공합니다.
                        """
                    },
                    {"role": "user", "content": f"대화 내용:\n{conversation}"},
                    {"role": "user", "content": f"data:image/png;base64,{image_base64}"}
                ]
                # max_tokens=300
            )
            analysis = response.choices[0].message.content.strip()
            logger.debug(f"Image analysis result: {analysis}")
            return analysis
        
        except requests.exceptions.RequestException as re:
            logger.error(f"Network error while downloading image: {str(re)}", exc_info=True)
            return self._handle_error(re, "_analyze_final_image")
        
        except ValueError as ve:
            logger.error(f"Value error: {str(ve)}", exc_info=True)
            return self._handle_error(ve, "_analyze_final_image")
        
        except Exception as e:
            logger.error(f"Unexpected error in image analysis: {str(e)}", exc_info=True)
            return self._handle_error(e, "_analyze_final_image")



    # 🧠 GPT-4-Turbo를 사용한 그림 제목 생성
    def _generate_drawing_name(self, analysis: str, summary: str) -> str:
        """그림 제목을 생성합니다 (GPT-4-Turbo 사용)."""
        try:
            prompt = (
                f"그림 분석 결과: {analysis}\n"
                f"대화 요약: {summary}\n"
                f"위 내용을 바탕으로 창의적이고 매력적인 그림 제목을 한 문장으로 생성해주세요."
            )
            
            response = openai.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": "그림 제목을 창의적으로 생성해주세요."},
                    {"role": "user", "content": prompt}
                ]
            )
            drawing_name = response.choices[0].message.content.strip()
            logger.debug(f"Generated drawing name: {drawing_name}")
            return drawing_name
        
        except Exception as e:
            return self._handle_error(e, "_generate_drawing_name")

    # 🧠 GPT-4-Turbo + DALL-E-3를 사용한 배경 이미지 생성
    def _generate_background_image(self, image_url: str, chat_history: List[ChatMessage]) -> str:
        """아이의 그림을 해석하고 어울리는 배경 이미지를 생성합니다 (GPT-4-Turbo + DALL-E-3 사용)."""
        try:
            logger.info(f"Downloading image from S3: {image_url}")


            # 🖼️ 1. 이미지 다운로드 및 Base64 인코딩
            response = requests.get(image_url)
            if response.status_code != 200:
                raise ValueError(f"Failed to download image from S3. Status code: {response.status_code}")
            
            image_data = BytesIO(response.content)
            image_base64 = base64.b64encode(image_data.getvalue()).decode('utf-8')
            
            logger.info("Successfully downloaded and encoded the image from S3.")
            
            # 💬 2. 대화 이력 포맷팅
            conversation = "\n".join([f"{msg.role}: {msg.text}" for msg in chat_history])
            
            # 🧠 3. GPT-4-Turbo로 아이 눈높이에서 그림 해석 및 DALL-E 프롬프트 생성
            logger.info("Generating background prompt using GPT-4-Turbo...")
            gpt_response = openai.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": """
                        당신은 3~7세 아이들의 둘도 없는 친구입니다.
                        어린 아이의 시각에서 그림을 따뜻하게 이해하고 해석합니다.
                        아이의 그림을 바탕으로 어울리는 배경을 상상하고 설명하며 dalle 3 모델용 프롬프트를 생성합니다.
                        """
                    },
                    {
                        "role": "user", 
                        "content": f"대화 내용:\n{conversation}"
                    },
                    {
                        "role": "user",
                        "content": f"data:image/png;base64,{image_base64}"
                    }
                ],
                max_tokens=200
            )
            
            # 응답 데이터 유효성 검증
            if not gpt_response.choices or not gpt_response.choices[0].message.content:
                raise ValueError("GPT 응답이 유효하지 않습니다.")
            
            background_description = gpt_response.choices[0].message.content.strip()
            logger.info(f"Background description from GPT-4-Turbo: {background_description}")

            # 🎨 4. DALL-E-3로 배경 이미지 생성
            logger.info("Generating background image using DALL-E-3...")
            dalle_response = openai.images.generate(
                model="dall-e-3",
                prompt=(
                    f"아이의 창의적 그림을 위한 배경: {background_description}. "
                    "어린이 친화적이고 부드러운 색상과 동화 같은 분위기로 구성해주세요."
                ),
                size="1024x1024"
            )
            
            # 응답 데이터 유효성 검증
            if not dalle_response.data or not dalle_response.data[0].url:
                raise ValueError("DALL-E 응답이 유효하지 않습니다.")
            
            background_image_url = dalle_response.data[0].url
            logger.debug(f"생성된 배경 이미지 URL: {background_image_url}")
            return background_image_url
        
        except requests.exceptions.RequestException as re:
            logger.error(f"Network error while downloading image: {str(re)}", exc_info=True)
            return self._handle_error(re, "_generate_background_image")
        
        except ValueError as ve:
            logger.error(f"Value error: {str(ve)}", exc_info=True)
            return self._handle_error(ve, "_generate_background_image")
        
        except Exception as e:
            logger.error(f"Unexpected error in background generation: {str(e)}", exc_info=True)
            return self._handle_error(e, "_generate_background_image")



    # 🖌️ API 메서드

    async def handle_new_drawing(self, request: NewDrawingRequest) -> str:
        try:
            logger.info(f"Processing new drawing request for canvas_id: {request.canvas_id}")
            if not request.robot_id or not request.name or not request.canvas_id:
                raise ValueError("Missing required fields in NewDrawingRequest.")
            
            drawing_data = DrawingData(
                robot_id=request.robot_id,
                name=request.name,
                age=request.age,
                canvas_id=request.canvas_id
            )
            self.drawing_data[request.canvas_id] = drawing_data
            
            initial_text = self._generate_initial_text(request.name, request.age)
            drawing_data.prompt = initial_text
            drawing_data.add_message("assistant", initial_text)
            drawing_data.audio_data = self._create_tts_response(initial_text)
            
            logger.info(f"Successfully processed new drawing request for canvas_id: {request.canvas_id}")
            return "success"

        except ValueError as ve:
            logger.error(f"Validation error in handle_new_drawing: {str(ve)}")
            return f"error: {str(ve)}"

        except Exception as e:
            return self._handle_error(e, "handle_new_drawing")



    async def handle_done_drawing(self, request: DoneDrawingRequest) -> str:
        try:
            logger.info(f"Processing done drawing request for canvas_id: {request.canvas_id}")
            
            drawing_data = self.drawing_data.get(request.canvas_id)
            if not drawing_data:
                return self._handle_error(ValueError("No drawing data found"), "handle_done_drawing")
            
            drawing_data.image_id = request.image_url
            drawing_data.summary = self._summarize_conversation(drawing_data.chat_history)
            drawing_data.analysis = self._analyze_final_image(request.image_url, drawing_data.chat_history)
            drawing_data.drawing_name = self._generate_drawing_name(drawing_data.analysis, drawing_data.summary)
            drawing_data.image_id = self._generate_background_image(request.image_url, drawing_data.chat_history)
            
            final_message = (
                f"우와! 정말 멋진 그림이 완성되었어요! "
                f"이 그림의 이름은 '{drawing_data.drawing_name}' 이고, "
                f"이 그림은 {drawing_data.analysis} 느낌이 나는 작품이에요."
            )
            drawing_data.add_message("ai", final_message)
            drawing_data.audio_data = self._create_tts_response(final_message)
            
            logger.info(f"Successfully processed done drawing request for canvas_id: {request.canvas_id}")
            return "success"

        except Exception as e:
            return self._handle_error(e, "handle_done_drawing")






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
                    transcript = openai.audio.transcriptions.create(
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
                chat_response = openai.chat.completions.create(
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