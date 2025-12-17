from fastapi import APIRouter
from app.api.routers import auth, resume, chat, interview, audio, rag, webrtc, jd

api_router = APIRouter()

# 导入所有现有的路由
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(resume.router, prefix="/resume", tags=["Resume"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(interview.router, prefix="/interview", tags=["Interview"])
api_router.include_router(audio.router, prefix="/audio", tags=["Audio"])
api_router.include_router(rag.router, prefix="/qa", tags=["RAG"])
api_router.include_router(webrtc.router, prefix="/webrtc", tags=["WebRTC"])
api_router.include_router(jd.router, prefix="/jd", tags=["JD"])
