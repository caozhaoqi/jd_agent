from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from core.error_handler import (
    raise_bad_request,
    raise_internal_error,
    raise_not_found,
)
from pydantic import BaseModel
from typing import List, AsyncGenerator
import json
from chains.rag_chain import ask_knowledge_base
from core.models import RAGResponse, RAGRequest, User
from api.deps import get_current_user
import asyncio

router = APIRouter()


@router.post("/qa", response_model=RAGResponse)
async def query_knowledge_base(request: RAGRequest):
    """
    RAG 接口：基于本地知识库回答问题
    """
    try:
        # 注意：这里要用 request.question 获取数据
        result = await ask_knowledge_base(request.question)

        return RAGResponse(answer=result["answer"], sources=result["sources"])
    except ValueError as e:
        # 返回友好的错误信息而不是崩溃
        return RAGResponse(answer=f"查询失败: {str(e)}", sources=[])
    except Exception as e:
        raise_internal_error(message="查询知识库失败", exc=e)


@router.post(
    "/qa/stream", summary="流式RAG接口", description="基于本地知识库流式回答问题"
)
async def stream_query_knowledge_base(request: RAGRequest):
    """
    流式RAG接口：基于本地知识库流式回答问题
    """
    try:
        from chains.rag_chain import (
            get_rewrite_chain,
            format_docs_with_source,
            extract_sources,
        )
        from chains.rag_chain import compression_retriever, prompt
        from chains.rag_chain import ChatOpenAI
        from core.config import settings

        # 1. 查询改写
        rewrite_chain = get_rewrite_chain()
        better_question = await rewrite_chain.ainvoke({"x": request.question})

        # 2. 检索文档
        docs = await compression_retriever.ainvoke(better_question)
        sources = extract_sources(docs)
        context = format_docs_with_source(docs)

        # 3. 获取流式LLM
        llm = ChatOpenAI(
            model_name=settings.LLM_MODEL_NAME,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_API_BASE,
            temperature=0.1,
            streaming=True,
        )

        # 4. 构建流式生成器
        async def generate():
            try:
                # 发送开始信号
                yield 'data: {"type": "start", "message": "开始生成回答..."}\n\n'

                # 流式生成回答
                full_answer = ""

                # 使用LLM的流式生成
                async for chunk in llm.astream(
                    prompt.format(context=context, question=better_question)
                ):
                    if hasattr(chunk, "content"):
                        content = chunk.content
                        full_answer += content
                        # 转义特殊字符
                        escaped_content = content.replace("\\", "\\\\").replace(
                            '"', '\\"'
                        )
                        yield f'data: {{"type": "chunk", "content": "{escaped_content}", "sources": {json.dumps(sources)}}}\n\n'

                # 发送结束信号
                escaped_full_answer = full_answer.replace("\\", "\\\\").replace(
                    '"', '\\"'
                )
                yield f'data: {{"type": "end", "content": "{escaped_full_answer}", "sources": {json.dumps(sources)}}}\n\n'
            except Exception as e:
                error_msg = str(e).replace("\\", "\\\\").replace('"', '\\"')
                yield f'data: {{"type": "error", "content": "{error_msg}", "sources": {json.dumps(sources)}}}\n\n'

        return StreamingResponse(generate(), media_type="text/event-stream")
    except ValueError as e:
        # 将e作为参数传递给error_generator
        async def error_generator(exc):
            error_msg = str(exc).replace("\\", "\\\\").replace('"', '\\"')
            yield f'data: {{"type": "error", "content": "{error_msg}"}}\n\n'

        return StreamingResponse(error_generator(e), media_type="text/event-stream")
    except Exception as e:
        # 将e作为参数传递给error_generator
        async def error_generator(exc):
            error_msg = f"查询知识库失败: {str(exc)}".replace("\\", "\\\\").replace(
                '"', '\\"'
            )
            yield f'data: {{"type": "error", "content": "{error_msg}"}}\n\n'

        return StreamingResponse(error_generator(e), media_type="text/event-stream")
