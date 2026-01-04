from fastapi import APIRouter
from api.routers import (
    auth,
    resume,
    chat,
    interview,
    audio,
    rag,
    webrtc,
    jd,
    video_analysis,
    confluence,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(resume.router, prefix="/resume", tags=["Resume"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(
    interview.router, prefix="/interview", tags=["Interview"]
)  # 包含 /generate-guide, /agent/feedback 等
api_router.include_router(audio.router, prefix="/audio", tags=["Audio"])
api_router.include_router(rag.router, prefix="/qa", tags=["RAG"])
api_router.include_router(webrtc.router, prefix="/webrtc", tags=["WebRTC"])
api_router.include_router(jd.router, prefix="/jd", tags=["JD"])
api_router.include_router(
    video_analysis.router, prefix="/video", tags=["Video Analysis"]
)
api_router.include_router(confluence.router, prefix="/confluence", tags=["Confluence"])
