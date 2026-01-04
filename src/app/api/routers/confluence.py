from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List, Any
from utils.logger import logger
from confluence.confluence_rag import confluence_kb_engine
from core.error_handler import raise_internal_error

router = APIRouter()


class ConfluenceQueryRequest(BaseModel):
    """Confluence查询请求模型"""

    query: str
    top_k: int = 3


class ConfluenceQueryResponse(BaseModel):
    """Confluence查询响应模型"""

    context: str
    sources: List[Dict[str, str]]


@router.post("/query", response_model=ConfluenceQueryResponse)
async def query_confluence_kb(request: ConfluenceQueryRequest):
    """
    查询Confluence Wiki知识库
    """
    try:
        logger.info(f"🔍 查询Confluence知识库: {request.query}")
        result = await confluence_kb_engine.search(
            query=request.query, top_k=request.top_k
        )
        return ConfluenceQueryResponse(
            context=result["context"], sources=result["sources"]
        )
    except Exception as e:
        logger.error(f"查询Confluence知识库失败: {e}")
        raise_internal_error("查询Confluence知识库失败", exc=e)


@router.get("/status")
async def get_confluence_kb_status():
    """
    获取Confluence Wiki知识库状态
    """
    try:
        is_available = confluence_kb_engine.vector_store is not None
        return {
            "status": "available" if is_available else "unavailable",
            "message": (
                "Confluence Wiki知识库已就绪"
                if is_available
                else "Confluence Wiki知识库未初始化或索引不存在"
            ),
        }
    except Exception as e:
        logger.error(f"获取Confluence知识库状态失败: {e}")
        raise_internal_error("获取Confluence知识库状态失败", exc=e)
