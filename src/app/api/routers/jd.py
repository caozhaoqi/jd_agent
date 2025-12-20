from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from loguru import logger

# 导入你需要的 schema 和 service
from app.schemas.interview import JDRequest, InterviewReport
from app.services.interview_service import generate_interview_guide
from app.core.llm_factory import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import asyncio

import jwt
import json
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
)
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
from app.core.stream_manager import init_stream_queue, clear_queue

# --- 内部模块导入 ---
# 1. 数据库与鉴权
from app.core.db_auth import (
    get_session,
    get_password_hash,
    verify_password,
    create_access_token,
    SECRET_KEY,
    ALGORITHM,
)
from app.core.models import (
    User,
    ChatSession,
    ChatMessage,
    UserProfile,
    ChatRequest,
    AuthRequest,
    BlogQueryRequest,
    BlogQueryResponse,
    RAGResponse,
)
from app.core.stream_manager import init_stream_queue, clear_queue
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
from app.core.sse_manager import sse_manager
from app.utils.file_parser import parse_resume_file
from app.chains.resume_extractor import extract_resume_features

# 1. 创建 Router 实例
router = APIRouter()


# 2. 将原 endpoints.py 中 JD 相关的接口移过来
# 注意：把 @app.post 改为 @router.post


@router.post("/generate-guide")
async def create_guide(
    request: JDRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """
    流式生成面试指南 (适配 DeepSeek 思考 UI)
    """
    thread_id = f"user_{user.id}_job_{hash(request.jd_text)}"

    async def generate_and_stream():
        from app.core.stream_manager import get_stream_queue

        # 创建一个队列用于收集所有需要发送的消息
        message_queue = asyncio.Queue()

        # 定义一个协程来处理 stream_manager 队列中的消息
        async def process_stream_queue():
            queue = None
            # 无限期等待队列初始化完成，确保能获取到队列
            while True:
                queue = get_stream_queue(thread_id)
                if queue:
                    logger.info(f"✅ [Process Queue] 获取队列成功: {thread_id}")
                    break
                await asyncio.sleep(0.1)

            try:
                while True:
                    logger.info(f"⏳ [Process Queue] 等待队列消息: {thread_id}")
                    msg = await queue.get()
                    logger.info(
                        f"📥 [Process Queue] 收到队列消息: {msg}, thread_id: {thread_id}"
                    )
                    if msg is None:  # 结束信号
                        logger.info(f"📤 [Process Queue] 收到结束信号: {thread_id}")
                        # 不在这里发送[DONE]，而是在所有内容都发送完成后统一发送
                        break
                    # 将消息添加到消息队列
                    payload = json.dumps(msg, ensure_ascii=False)
                    await message_queue.put(f"data: {payload}\n\n")
                    logger.info(
                        f"📤 [Process Queue] 发送消息到前端: {payload}, thread_id: {thread_id}"
                    )
            except Exception as e:
                logger.error(f"❌ [Queue Error] {e}, thread_id: {thread_id}")
                # 发送错误信息
                error_payload = json.dumps(
                    {"type": "error", "content": str(e)}, ensure_ascii=False
                )
                await message_queue.put(f"data: {error_payload}\n\n")
            # 不再在process_stream_queue中清除队列，而是在所有协程完成后清除

        # 定义一个协程来生成报告
        async def generate_report():
            try:
                logger.info(f"🚀 [Generate Report] 开始生成报告: {thread_id}")
                report = await generate_interview_guide(request, db, user.id)
                logger.info(f"✅ [Generate Report] 报告生成成功: {thread_id}, report内容: {type(report)}")

                # 存库
                try:
                    title = (
                        f"{report.meta.company_name} 面试准备"
                        if report.meta.company_name
                        else "岗位 JD 分析"
                    )
                    new_session = ChatSession(title=title, user_id=user.id)
                    db.add(new_session)
                    db.commit()
                    db.refresh(new_session)

                    # 保存消息记录
                    db.add(
                        ChatMessage(
                            session_id=new_session.id,
                            role="user",
                            content=request.jd_text,
                        )
                    )
                    db.add(
                        ChatMessage(
                            session_id=new_session.id,
                            role="assistant",
                            content=report.model_dump_json(),
                        )
                    )
                    db.commit()

                    # 关键修改：把 ID 塞回报告里，传给前端
                    report.session_id = new_session.id
                    logger.info(f"💾 [Generate Report] 报告已保存到数据库: {thread_id}, session_id: {new_session.id}")
                except Exception as e:
                    logger.error(f"❌ [DB Error] {e}")

                # 更新长期记忆
                background_tasks.add_task(
                    update_long_term_memory,
                    db,
                    user.id,
                    f"User上传了JD: {request.jd_text}",
                )

                # 发送结束信号到流管理器队列
                from app.core.stream_manager import send_done
                await send_done(thread_id)
                logger.info(f"📤 [Generate Report] 发送结束信号: {thread_id}")

                return report
            except Exception as e:
                logger.error(f"❌ [Generate Report Error] {e}")
                # 发送错误信息
                error_payload = json.dumps(
                    {"type": "error", "content": str(e)}, ensure_ascii=False
                )
                await message_queue.put(f"data: {error_payload}\n\n")
                return None

        # 并行运行所有协程
        report_task = asyncio.create_task(generate_report())
        queue_task = asyncio.create_task(process_stream_queue())

        # 实时发送消息队列中的内容
        while True:
            # 检查报告和队列任务是否都完成
            if report_task.done() and queue_task.done():
                break

            try:
                # 非阻塞地获取消息，如果没有消息则继续循环
                msg = await asyncio.wait_for(message_queue.get(), timeout=0.1)
                if msg is not None:
                    yield msg
            except asyncio.TimeoutError:
                # 没有消息，继续循环
                continue

        # 等待报告生成完成
        report = await report_task

        # 如果报告生成失败，不发送最终结果
        if report is not None:
            # 格式化报告为Markdown字符串
            def format_report_to_markdown(report):
                meta = report.meta
                tech_questions = report.tech_questions
                hr_questions = report.hr_questions
                company_analysis = report.company_analysis

                markdown = f"## 📊 {meta.company_name or '岗位'} 分析\n\n**技术栈**: `{', '.join(meta.tech_stack)}`\n\n"
                if company_analysis:
                    markdown += f"> 🏢 **公司**: {company_analysis}\n\n"
                markdown += "### 🛠️ 推荐技术题\n"
                for i, q in enumerate(tech_questions, 1):
                    markdown += f"**Q{i}: {q.question}**\n> {q.reference_answer}\n\n"
                if hr_questions and len(hr_questions) > 0:
                    markdown += "### 🧑💼 推荐HR题\n"
                    for i, q in enumerate(hr_questions, 1):
                        markdown += (
                            f"**Q{i}: {q.question}**\n> {q.reference_answer}\n\n"
                        )
                return markdown

            # 生成Markdown内容
            markdown_content = format_report_to_markdown(report)

            # 逐token发送内容
            from app.core.stream_manager import send_token

            for char in markdown_content:
                # 使用更合适的发送速度，确保流畅的打字机效果
                await asyncio.sleep(0.015)  # 稍微提高速度，让体验更流畅
                token_payload = json.dumps(
                    {"type": "token", "content": char}, ensure_ascii=False
                )
                yield f"data: {token_payload}\n\n"

            # 发送报告元数据给前端
            meta_payload = json.dumps(
                {"type": "data", "key": "report_meta", "value": report.model_dump()},
                ensure_ascii=False,
            )
            yield f"data: {meta_payload}\n\n"
            logger.info(f"📤 [Generate and Stream] 发送报告元数据: {thread_id}")

            # 发送结果消息，通知前端解析完成
            result_payload = json.dumps(
                {"type": "result", "content": report.model_dump()},
                ensure_ascii=False,
            )
            yield f"data: {result_payload}\n\n"
            logger.info(f"📤 [Generate and Stream] 发送结果消息: {thread_id}")

        # 发送结束信号
        yield f"data: [DONE]\n\n"

        # 所有消息发送完成后，清除队列
        from app.core.stream_manager import clear_queue

        clear_queue(thread_id)
        logger.info(
            f"🧹 [Generate and Stream] 所有消息发送完成，队列已清除: {thread_id}"
        )

    return StreamingResponse(
        generate_and_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/stream/system-design")
async def stream_system_design(
    tech_stack: str, topic: str, user: User = Depends(get_current_user)
):
    """
    流式生成系统设计题答案 (打字机效果)
    """
    llm = get_llm(temperature=0.7)

    prompt = ChatPromptTemplate.from_template(
        "请基于 {tech_stack} 技术栈，详细设计一个 {topic} 系统。请包含架构图描述、数据库选型和核心难点。"
    )

    chain = prompt | llm | StrOutputParser()

    async def generate_stream():
        # 创建SSE连接
        client_id, send_queue = await sse_manager.add_connection()

        try:
            async for chunk in chain.astream(
                {"tech_stack": tech_stack, "topic": topic}
            ):
                # 发送数据到客户端
                await send_queue.put(f"data: {chunk}\n\n")
                # 直接yield数据，保持兼容
                yield f"data: {chunk}\n\n"

            # 发送结束信号
            await send_queue.put("data: [DONE]\n\n")
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Stream generation error: {e}")
            # 发送错误信号
            await send_queue.put(f"data: [ERROR]\n\n")
            yield f"data: [ERROR]\n\n"
        finally:
            # 确保连接被移除
            await sse_manager.remove_connection(client_id)

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
