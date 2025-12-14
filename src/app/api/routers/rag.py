from fastapi import APIRouter
from app.core.error_handler import raise_bad_request, raise_internal_error, raise_not_found
from pydantic import BaseModel
from typing import List
from app.chains.rag_chain import ask_knowledge_base
from app.core.models import RAGResponse, RAGRequest

router = APIRouter()



@router.post("/qa", response_model=RAGResponse)
async def query_knowledge_base(request: RAGRequest):
    """
    RAG 接口：基于本地知识库回答问题
    """
    try:
        # 注意：这里要用 request.question 获取数据
        result = await ask_knowledge_base(request.question)

        return RAGResponse(
            answer=result["answer"],
            sources=result["sources"]
        )
    except ValueError as e:
        # 返回友好的错误信息而不是崩溃
        return RAGResponse(answer=f"查询失败: {str(e)}", sources=[])
    except Exception as e:
        raise_internal_error(message="查询知识库失败", exc=e)