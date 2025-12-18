from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Union
from app.utils.logger import logger
from app.confluence.confluence_rag import confluence_kb_engine

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

    Args:
        request: 查询请求，包含查询字符串和返回结果数量

    Returns:
        查询结果和来源链接
    """
    try:
        logger.info(f"🔍 查询Confluence知识库: {request.query}")

        # 调用知识库搜索功能
        result = confluence_kb_engine.search(query=request.query, top_k=request.top_k)

        return ConfluenceQueryResponse(
            context=result["context"], sources=result["sources"]
        )

    except Exception as e:
        logger.error(f"❌ 查询Confluence知识库失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/status")
async def get_confluence_kb_status():
    """
    获取Confluence Wiki知识库状态

    Returns:
        知识库状态信息
    """
    try:
        # 检查向量库是否加载成功
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
        logger.error(f"❌ 获取Confluence知识库状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")
