from fastapi import APIRouter
from app.api.routers import auth, resume, chat, interview, audio, rag, webrtc

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(resume.router, prefix="/resume", tags=["Resume"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(interview.router, tags=["Interview"])  # 包含 /generate-guide, /agent/feedback 等
api_router.include_router(audio.router, prefix="/audio", tags=["Audio"])
api_router.include_router(rag.router, prefix="/qa", tags=["RAG"])
api_router.include_router(webrtc.router, prefix="/webrtc", tags=["WebRTC"])
