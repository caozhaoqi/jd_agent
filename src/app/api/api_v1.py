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
    logs,
    team,
    blog,
    interview_style,
    report_export,
    knowledge_graph,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(resume.router, prefix="/resume", tags=["Resume"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(
    interview.router, prefix="/interview", tags=["Interview"]
)
api_router.include_router(audio.router, prefix="/audio", tags=["Audio"])
api_router.include_router(rag.router, prefix="/qa", tags=["RAG"])
api_router.include_router(webrtc.router, prefix="/webrtc", tags=["WebRTC"])
api_router.include_router(jd.router, prefix="/jd", tags=["JD"])
api_router.include_router(
    video_analysis.router, prefix="/video", tags=["Video Analysis"]
)
api_router.include_router(confluence.router, prefix="/confluence", tags=["Confluence"])
api_router.include_router(logs.router, prefix="/logs", tags=["Logs"])
api_router.include_router(team.router, prefix="/teams", tags=["Teams"])
api_router.include_router(blog.router, prefix="/blog", tags=["Blog"])
api_router.include_router(interview_style.router, prefix="/interview-style", tags=["Interview Style"])
api_router.include_router(report_export.router, prefix="/report-export", tags=["Report Export"])
api_router.include_router(knowledge_graph.router, prefix="/knowledge-graph", tags=["Knowledge Graph"])
