# Mind in Canvas AI - Python Server

마인드 인 캔버스 프로젝트의 AI 서버 컴포넌트입니다. 이 서버는 그림 분석과 음성 대화를 처리합니다.

## 주요 기능

### 1. 그림 분석 (Drawing Analysis)
- 실시간 그림 분석을 위한 WebSocket 연결 제공
- GPT-4 Vision API를 사용한 그림 분석
- 분석 내용:
  - 사용된 주요 색상
  - 그림에서 느껴지는 감정
  - 그림의 주요 내용
  - 대화 문맥 정보

### 2. 음성 대화 (Voice Interaction)
- 실시간 음성 통신을 위한 WebSocket 연결 제공
- 음성을 텍스트로 변환 (STT)
- AI 응답 생성 및 음성 합성 (TTS)
- 대화 내역 저장 및 관리

## API 엔드포인트

### HTTP 엔드포인트
- `POST /drawing/new`: 새로운 드로잉 세션 생성
  - Request Body: `robot_id`, `name`, `age`, `canvas_id`
  - Response: 초기 음성 메시지와 오디오 데이터

- `GET /drawing/chat-history/{canvas_id}`: 특정 캔버스의 대화 내역 조회

### WebSocket 엔드포인트
- `/ws/drawing/{robot_id}/{canvas_id}`: 음성 대화용 WebSocket
  - 음성 데이터 송수신
  - 실시간 대화 처리

- `/drawing/send`: 그림 분석용 WebSocket
  - 실시간 그림 분석
  - 이미지 URL 기반 분석 결과 전송

## 기술 스택
- FastAPI
- OpenAI GPT-4 Vision API
- OpenAI Whisper API (STT)
- OpenAI TTS API
- WebSocket

## 설치 및 실행

1. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
```

2. 의존성 설치
```bash
pip install -r requirements.txt
```

3. 환경 변수 설정
```bash
export OPENAI_API_KEY="your-api-key"
```

4. 서버 실행
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8081
```

## 데이터 구조

### DrawingData
- 사용자 정보 (이름, 나이)
- 로봇 ID
- 캔버스 ID
- 현재 이미지 URL
- 대화 내역
- 그림 분석 결과

### DrawingAnalysis
- 사용된 색상 목록
- 감정 분석
- 그림 내용
- 대화 문맥

## 주의사항
- WebSocket 연결 시 올바른 JSON 형식의 메시지를 전송해야 합니다.
- 음성 데이터는 base64로 인코딩되어야 합니다.
- 모든 이미지 URL은 공개적으로 접근 가능해야 합니다.
