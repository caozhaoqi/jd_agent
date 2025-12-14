from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
# 导入你需要的 schema 和 service
from app.schemas.interview import JDRequest, InterviewReport
from app.services.interview_service import generate_interview_guide
from app.core.llm_factory import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import asyncio

import jwt
import json
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from loguru import logger
from pydantic import BaseModel
from sqlmodel import Session, select
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json  # 记得导入 json

from app.chains.rag_chain import ask_knowledge_base
# 确保导入了必要的工具
from app.core.stream_manager import init_stream_queue

# --- 内部模块导入 ---
# 1. 数据库与鉴权
from app.core.db_auth import get_session, get_password_hash, verify_password, create_access_token, SECRET_KEY, ALGORITHM
from app.core.models import User, ChatSession, ChatMessage, UserProfile, ChatRequest, AuthRequest, BlogQueryRequest, \
    BlogQueryResponse, RAGResponse
from app.core.stream_manager import init_stream_queue
from app.graph.workflow import app_graph

# 2. Schema 数据模型
from app.schemas.interview import JDRequest, InterviewReport
from app.services.blog_service import chat_with_blog

# 3. 业务服务逻辑
from app.services.interview_service import generate_interview_guide
from app.services.memory_service import update_long_term_memory
from app.services.mock_service import run_mock_interview_stream

# 4. 核心工具与链
from app.core.llm_factory import get_llm
from app.utils.file_parser import parse_resume_file
from app.chains.resume_extractor import extract_resume_features


# 1. 创建 Router 实例
router = APIRouter()

# 2. 将原 endpoints.py 中 JD 相关的接口移过来
# 注意：把 @app.post 改为 @router.post

@router.post("/generate-guide", response_model=InterviewReport)
async def create_guide(
        request: JDRequest,
        background_tasks: BackgroundTasks,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_session),
):
    # 1. 生成报告
    report = await generate_interview_guide(request, db, user.id)

    # 2. 存库
    try:
        title = f"{report.meta.company_name} 面试准备" if report.meta.company_name else "岗位 JD 分析"
        new_session = ChatSession(title=title, user_id=user.id)
        db.add(new_session)
        db.commit()
        db.refresh(new_session)

        # 保存消息记录
        db.add(ChatMessage(session_id=new_session.id, role="user", content=request.jd_text))
        db.add(ChatMessage(session_id=new_session.id, role="assistant", content=report.model_dump_json()))
        db.commit()

        # ✅ 关键修改：把 ID 塞回报告里，传给前端
        report.session_id = new_session.id

    except Exception as e:
        logger.error(f"❌ [DB Error] {e}")

    # 3. 更新长期记忆
    background_tasks.add_task(update_long_term_memory, db, user.id, f"User上传了JD: {request.jd_text}")

    return report

@router.post("/stream/system-design")
async def stream_system_design(tech_stack: str, topic: str):
    """
    流式生成系统设计题答案 (打字机效果)
    """
    llm = get_llm(temperature=0.7)

    prompt = ChatPromptTemplate.from_template(
        "请基于 {tech_stack} 技术栈，详细设计一个 {topic} 系统。请包含架构图描述、数据库选型和核心难点。"
    )

    chain = prompt | llm | StrOutputParser()

    async def generate_stream():
        async for chunk in chain.astream({"tech_stack": tech_stack, "topic": topic}):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream"
    )
