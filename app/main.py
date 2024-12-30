from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from app.controllers.drawing_controller import router as drawing_router
from app.controllers.socket_controller import router as socket_router

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 제공
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 라우터 등록
app.include_router(drawing_router)
app.include_router(socket_router)

@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")