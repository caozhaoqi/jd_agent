from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List
from app.services.blog_service import chat_with_blog
from app.api.deps import get_current_user
from app.core.models import User

router = APIRouter()


class BlogQueryRequest(BaseModel):
    question: str


class BlogQueryResponse(BaseModel):
    answer: str
    sources: List[str]


@router.post("/chat", response_model=BlogQueryResponse)
async def chat_blog(request: BlogQueryRequest, user: User = Depends(get_current_user)):
    """博客查询接口"""
    result = await chat_with_blog(request.question)
    return BlogQueryResponse(answer=result["answer"], sources=result["sources"])
