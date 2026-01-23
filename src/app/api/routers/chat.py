import json
import asyncio
from fastapi import APIRouter, Depends
from core.error_handler import raise_not_found, raise_internal_error
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from loguru import logger

from api.deps import get_current_user, get_session
from core.models import User, ChatSession, ChatMessage, ChatRequest
from core.llm_factory import get_llm
from core.config import settings
from core.stream_manager import init_stream_queue
from core.sse_manager import sse_manager
from chains.rag_chain import ask_knowledge_base

router = APIRouter()


@router.get("/history/sessions")
def get_sessions(
    user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    """获取当前用户的所有会话列表"""
    try:
        return session.exec(
            select(ChatSession)
            .where(ChatSession.user_id == user.id)
            .order_by(ChatSession.id.desc())
        ).all()
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        raise_internal_error("获取会话列表失败", exc=e)


@router.get("/history/messages/{session_id}")
def get_messages(
    session_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """获取指定会话的详细消息"""
    chat = session.get(ChatSession, session_id)
    if not chat or chat.user_id != user.id:
        raise_not_found("会话不存在")
    return chat.messages


@router.post("/history/sessions")
def create_session(
    title: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """创建新的会话"""
    try:
        new_session = ChatSession(
            user_id=user.id,
            title=title
        )
        session.add(new_session)
        session.commit()
        session.refresh(new_session)
        return new_session
    except Exception as e:
        logger.error(f"创建会话失败: {e}")
        raise_internal_error("创建会话失败", exc=e)


@router.post("/stream")
async def stream_chat(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """通用多轮对话流式接口"""
    init_stream_queue()

    session = db.get(ChatSession, req.session_id)
    if not session:
        raise_not_found("会话不存在")

    user_msg = ChatMessage(session_id=req.session_id, role="user", content=req.content)
    db.add(user_msg)
    db.commit()

    recent_msgs = session.messages[-10:]
    last_user_msg = req.content
    system_prompt = "你是一个专业的 AI 求职助手，负责解答用户的技术问题。"

    if "模拟面试" in last_user_msg or "开始面试" in last_user_msg:
        system_prompt = "你现在是【面试官模式】。请基于该会话的上下文（JD 和 简历），向候选人提出一个具体的面试问题。要求：1. 每次只问一个问题。2. 问题要犀利、具体。3. 等待用户回答后，再进行追问或点评。"
    elif "面试" in session.title:
        system_prompt = "你是一名严厉但专业的面试官。请根据求职者的回答进行追问，考察其技术深度。"

    lc_messages = [SystemMessage(content=system_prompt)]
    for m in recent_msgs:
        lc_messages.append(
            HumanMessage(content=m.content)
            if m.role == "user"
            else AIMessage(content=m.content)
        )

    llm = get_llm(temperature=0.7, streaming=True, model=settings.MODEL_NAME)
    chain = llm | StrOutputParser()

    async def generate_and_stream():
        client_id, send_queue = await sse_manager.add_connection()
        try:
            thought_payload = json.dumps(
                {"type": "thought", "content": "正在分析上下文..."}, ensure_ascii=False
            )
            await send_queue.put(f"data: {thought_payload}\n\n")
            yield f"data: {thought_payload}\n\n"

            full_response = ""
            async for chunk in chain.astream(lc_messages):
                full_response += chunk
                token_payload = json.dumps(
                    {"type": "token", "content": chunk}, ensure_ascii=False
                )
                await send_queue.put(f"data: {token_payload}\n\n")
                yield f"data: {token_payload}\n\n"

            if full_response:
                ai_msg = ChatMessage(
                    session_id=req.session_id, role="assistant", content=full_response
                )
                db.add(ai_msg)
                db.commit()

            await send_queue.put("data: [DONE]\n\n")
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"流式聊天处理失败: {e}")
            err_payload = json.dumps({"type": "error", "content": str(e)})
            yield f"data: {err_payload}\n\n"
            yield "data: [DONE]\n\n"
        finally:
            await sse_manager.remove_connection(client_id)

    return StreamingResponse(
        generate_and_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
