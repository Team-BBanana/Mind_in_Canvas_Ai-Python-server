# Mind in Canvas AI Server

FastAPI 기반의 AI 서버로, OpenAI의 GPT-3.5-turbo 모델을 활용한 채팅 서비스를 제공합니다.

## 프로젝트 구조
```
app/
├── controllers/
│   └── chat_controller.py     # API 엔드포인트 정의
├── services/
│   └── chat_service/
│       ├── chat_service.py        # 인터페이스 정의
│       ├── chat_service_impl.py   # 구현체
│       └── chat_domain_service.py # OpenAI API 호출 로직
├── config.py                  # 환경 설정
└── main.py                    # FastAPI 앱 설정
```

## 기술 스택
- Python 3.10+
- FastAPI (v0.109.0)
  - 현대적이고 빠른 웹 프레임워크
  - 자동 API 문서화 (Swagger/ReDoc)
  - 비동기 처리 지원
- OpenAI API
  - openai v1.12.0 클라이언트 라이브러리
  - 세부 모델 미정
- Pydantic (v2.6.0)
  - 데이터 검증
  - 설정 관리 (pydantic-settings v2.1.1)
- Uvicorn (v0.27.0)
  - ASGI 서버
  - 고성능 비동기 처리

## 설치 방법

1. 저장소 클론
```bash
git clone [repository-url]
cd Mind_in_Canvas_Ai-Python-server
```

2. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows
```

3. 의존성 설치
```bash
pip install -r requirements.txt
```

4. 환경변수 설정
```bash
# .env 파일 생성
OPENAI_API_KEY=your-api-key-here
```

## 실행 방법

### 개발 서버 실행
```bash
# 기본 실행 (localhost에서만 접근 가능)
uvicorn app.main:app --reload

# 포트 직접 지정
uvicorn app.main:app --reload --port 8080

# 외부 접근 허용 (다른 기기에서 접근 가능)
uvicorn app.main:app --reload --host 0.0.0.0  # 주의: 개발 환경에서만 사용

# 외부 접근 및 포트 지정
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### 주요 옵션 설명
- `--reload`: 코드 변경 시 자동으로 서버 재시작 (개발 환경에서만 사용)
- `--host`: 서버 접근 허용 범위 설정
  - `127.0.0.1`: 로컬 접근만 허용 (기본값, 보안상 안전)
  - `0.0.0.0`: 모든 외부 접근 허용 (다른 기기에서 테스트 필요 시 사용)
- `--port`: 서버 포트 (기본값: 8000)
- `--workers`: 워커 프로세스 수 (기본값: 1)

### API 문서
서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 프로덕션 배포
프로덕션 환경에서는 `--reload` 옵션을 제거하고, 적절한 워커 수를 지정하는 것을 권장합니다:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API 엔드포인트

### 테스트 엔드포인트
- GET `/test`: OpenAI API 테스트

## 아키텍처 특징

### 계층형 구조
- Controller Layer: API 엔드포인트 및 요청 처리
- Service Layer: 비즈니스 로직 처리
- Domain Service Layer: 외부 API(OpenAI) 통신

### 주요 컴포넌트
1. ChatService (Interface)
   - 채팅 서비스의 기본 계약 정의
   - 메시지 처리를 위한 추상 메서드 제공

2. ChatServiceImpl
   - ChatService 인터페이스 구현
   - 사용자 메시지 처리 및 응답 관리

3. ChatDomainService
   - OpenAI API와의 직접적인 통신 담당
   - API 호출 및 응답 처리

## 에러 처리
- 서비스 레벨 에러 처리
- OpenAI API 관련 에러 처리
- HTTP 예외 처리

## 개발 가이드

### 새로운 기술 추가
1. 적절한 레이어에 코드 추가
2. 인터페이스 기반 설계 준수
3. 비동�� 처리 패턴 사용

### 코드 스타일
- Type Hints 사용
- 비동기 함수 사용 (async/await)
- 명확한 예외 처리

## 라이센스
<!-- Copyright © 2024 Mind in Canvas. All rights reserved. -->
- 없음

## 기여 방법
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### 보안 고려사항
외부 접근을 허용할 때(`--host 0.0.0.0`) 다음 보안 설정을 고려해야 합니다:

1. API 인증
   - API 키 또는 토큰 기반 인증 구현
   - 요청 헤더에 인증 정보 포함

2. Rate Limiting
   - 클라이언트별 요청 제한
   - DOS 공격 방지

3. CORS 설정
   - 허용된 도메인만 접근 가능하도록 설정
   - 현재 설정: 모든 도메인 허용 (`"*"`)

4. 방화벽 설정
   - 특정 IP 또는 IP 대역만 허용
   - 불필요한 포트 차단

### 프로덕션 배포
프로덕션 환경에서는 `--reload` 옵션을 제거하고, 적절한 워커 수를 지정하는 것을 권장합니다:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```
