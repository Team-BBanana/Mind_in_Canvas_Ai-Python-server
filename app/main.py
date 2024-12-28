from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.controllers.chat_controller import router as chat_controller

app = FastAPI(title="AI Server API")

# 허용할 도메인 리스트
# origins = [
#     "http://localhost",
#     "http://localhost:3000",
#     "https://your-frontend-domain.com",
# ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 허용할 출처
    allow_credentials=True,
    allow_methods=["*"],    # 허용할 HTTP 메서드
    allow_headers=["*"],    # 허용할 헤더
)

# 라우터 등록
app.include_router(chat_controller)