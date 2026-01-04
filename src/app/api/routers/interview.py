import json
import asyncio
from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.sql.functions import user
from sqlmodel import Session
from loguru import logger

from api.deps import get_current_user, get_session
from core.models import User, ChatSession, ChatMessage
from schemas import JDRequest, InterviewReport, APIException, ErrorCode
from services.interview_service import generate_interview_guide
from services.memory_service import update_long_term_memory
from services.mock_service import run_mock_interview_stream
from graph.workflow import app_graph
from core.stream_manager import init_stream_queue

router = APIRouter()


# ==========================================
# 4. 核心生成接口 (Core Logic)
# ==========================================
@router.post(
    "/guide",
    response_model=InterviewReport,
    summary="创建面试指南",
    description="根据提供的岗位JD生成完整的面试指南报告，包括公司分析、技术问题和HR问题。",
)
async def create_guide(
    request: JDRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    try:
        # 1. 生成报告
        thread_id = f"user_{user.id}_job_{hash(request.jd_text)}"
        report = await generate_interview_guide(request, db, user.id, thread_id)

        # 2. 存库
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
                    session_id=new_session.id, role="user", content=request.jd_text
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

            # ✅ 关键修改：把 ID 塞回报告里，传给前端
            report.session_id = new_session.id

        except Exception as db_e:
            logger.error(f"❌ [DB Error] {db_e}")
            # 数据库错误不影响主流程

        # 3. 更新长期记忆
        background_tasks.add_task(
            update_long_term_memory, db, user.id, f"User上传了JD: {request.jd_text}"
        )

        return report
    except Exception as e:
        logger.error(f"❌ [Generate Guide Error] {e}")
        raise APIException(
            status_code=500,
            code=ErrorCode.JD_PARSE_ERROR,
            message="生成面试指南失败",
            details={"error": str(e)},
        )


@router.post(
    "/guide/stream",
    summary="流式生成面试指南",
    description="根据提供的岗位JD流式生成面试指南，实时返回生成过程，支持DeepSeek思考过程展示。",
)
async def stream_generate_guide(
    request: JDRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """
    L5 级 Agent 流式生成接口 (支持 DeepSeek 思考过程)

    请求体:
    - jd_text: 岗位JD文本内容

    响应:
    流式返回SSE事件，类型包括:
    - type='result': 最终生成的面试指南JSON
    - type='error': 错误信息
    - type='intermediate': 中间处理步骤信息
    """
    try:
        thread_id = f"user_{user.id}_job_{hash(request.jd_text)}"

        async def generate_and_stream():
            try:
                # 初始化 stream_manager 队列
                from core.stream_manager import get_stream_queue, init_stream_queue

                init_stream_queue(thread_id=thread_id)

                # 创建一个队列用于收集所有需要发送的消息
                message_queue = asyncio.Queue()

                # 定义一个协程来处理 stream_manager 队列中的消息
                async def process_stream_queue():
                    queue = get_stream_queue(thread_id)
                    if not queue:
                        return

                    try:
                        while True:
                            msg = await queue.get()
                            if msg is None:  # 结束信号
                                break
                            # 将消息添加到消息队列
                            payload = json.dumps(msg, ensure_ascii=False)
                            await message_queue.put(f"data: {payload}\n\n")
                    except Exception as e:
                        logger.error(f"❌ [Queue Error] {e}")
                        # 发送错误信息
                        error_payload = json.dumps(
                            {"type": "error", "content": str(e)}, ensure_ascii=False
                        )
                        await message_queue.put(f"data: {error_payload}\n\n")

                # 定义一个协程来生成报告
                async def generate_report():
                    try:
                        # 1. 准备初始状态
                        initial_state = {
                            "jd_text": request.jd_text,
                            "user_id": user.id,
                            "interview_type": request.interview_type,
                            "iteration_count": 0,
                            "tech_stack": [],
                            "years_required": "",
                            "company_name": "",
                        }

                        config = {"configurable": {"thread_id": thread_id}}

                        # 2. 运行 Graph - 使用astream实现流式处理
                        final_state = None
                        async for event in app_graph.astream(
                            initial_state, config=config
                        ):
                            if event and "values" in event:
                                final_state = event["values"]

                        # 3. 处理并发送最终结果
                        # --- 组装 Report 逻辑 ---
                        # 1. 处理 Technical Questions
                        raw_tech_qs = final_state.get("tech_questions", [])
                        tech_qs_dicts = [
                            q.model_dump() if hasattr(q, "model_dump") else q
                            for q in raw_tech_qs
                        ]

                        # 2. 处理 HR Questions
                        raw_hr_qs = final_state.get("hr_questions", [])
                        hr_qs_dicts = [
                            q.model_dump() if hasattr(q, "model_dump") else q
                            for q in raw_hr_qs
                        ]

                        # 3. 简单构造 Meta
                        final_meta = {
                            "company_name": final_state.get("company_name"),
                            "tech_stack": final_state.get("tech_stack"),
                            "years_required": final_state.get("years_required"),
                            "soft_skills": [],  # 暂空
                        }

                        final_report = {
                            "meta": final_meta,
                            "tech_questions": tech_qs_dicts,
                            "hr_questions": hr_qs_dicts,
                            "company_analysis": final_state.get("company_info"),
                            "session_id": None,
                        }

                        # --- 存库逻辑 ---
                        try:
                            if db is not None:
                                title = (
                                    f"{final_meta['company_name']} 面试准备"
                                    if final_meta["company_name"]
                                    else "JD 分析"
                                )
                                new_sess = ChatSession(title=title, user_id=user.id)
                                db.add(new_sess)
                                db.commit()
                                db.refresh(new_sess)
                                final_report["session_id"] = new_sess.id
                                # 保存消息
                                db.add(
                                    ChatMessage(
                                        session_id=new_sess.id,
                                        role="user",
                                        content=request.jd_text,
                                    )
                                )
                                db.add(
                                    ChatMessage(
                                        session_id=new_sess.id,
                                        role="assistant",
                                        content=json.dumps(final_report),
                                    )
                                )
                                db.commit()
                        except Exception as db_e:
                            logger.error(f"DB Error: {db_e}")

                        # 发送最终结果
                        result_payload = json.dumps(
                            {"type": "result", "content": json.dumps(final_report)},
                            ensure_ascii=False,
                        )
                        await message_queue.put(f"data: {result_payload}\n\n")

                    except Exception as e:
                        logger.error(f"❌ [Generate Report Error] {e}")
                        # 发送错误信息
                        error_payload = json.dumps(
                            {"type": "error", "content": str(e)}, ensure_ascii=False
                        )
                        await message_queue.put(f"data: {error_payload}\n\n")

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

                # 发送结束信号
                yield "data: [DONE]\n\n"

            finally:
                # 清除队列
                from core.stream_manager import clear_queue

                clear_queue(thread_id)

        return StreamingResponse(
            generate_and_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        logger.error(f"❌ [Stream Generate Guide Error] {e}")

        # 对于流式响应，我们需要在生成器中处理错误
        async def error_generator():
            error_data = {
                "type": "error",
                "content": {
                    "status": "error",
                    "code": ErrorCode.JD_PARSE_ERROR,
                    "message": "生成面试指南失败",
                    "details": {"error": str(e)},
                },
            }
            yield f"data: {json.dumps(error_data)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(error_generator(), media_type="text/event-stream")


@router.post(
    "/feedback/{thread_id}",
    summary="AI任务反馈",
    description="用户对AI暂停的任务进行干预，支持强制通过或带意见重试。",
)
async def agent_feedback(
    thread_id: str,
    feedback: str,
    action: str = "retry",
    user: User = Depends(get_current_user),
):
    """
    用户对 AI 暂停的任务进行干预

    参数:
    - thread_id: 任务线程ID
    - feedback: 用户反馈内容
    - action: 操作类型，支持 "approve" (强制通过) 或 "retry" (带意见重试)，默认 "retry"

    响应:
    - status: 操作状态
    - message: 操作结果描述
    """
    try:
        config = {"configurable": {"thread_id": thread_id}}

        if action == "approve":
            # 强制更新状态：把分数改成 100，这样路由就会通过
            app_graph.update_state(
                config, {"quality_score": 100, "human_feedback": "强制通过"}
            )
        else:
            # 注入用户的修改意见
            app_graph.update_state(config, {"human_feedback": feedback})

        # 恢复执行 (Resume)
        # 这里的 None 表示继续执行下一步 (即进入 tech_lead 重写)
        async for event in app_graph.astream(None, config=config):
            pass

        return {"status": "success", "message": "任务已恢复执行"}
    except Exception as e:
        logger.error(f"Agent feedback error: {e}")
        raise APIException(
            status_code=500,
            code=ErrorCode.AGENT_WORKFLOW_ERROR,
            message="处理反馈失败",
            details={"error": str(e)},
        )


@router.post(
    "/mock-interview/stream",
    summary="流式模拟面试",
    description="根据提供的岗位JD启动流式模拟面试，实时返回面试官和候选人的对话过程。",
)
async def stream_mock_interview(
    request: JDRequest, user: User = Depends(get_current_user)
):
    """
    流式模拟面试接口

    请求体:
    - jd_text: 岗位JD文本内容

    响应:
    流式返回SSE事件，包括:
    - role='interviewer': 面试官提问
    - role='candidate': 候选人回答
    - role='system': 系统消息
    - role='reviewer': 面试点评
    - role='error': 错误信息
    - role='done': 面试结束信号
    """
    try:
        return StreamingResponse(
            run_mock_interview_stream(
                request.jd_text, interview_type=request.interview_type, rounds=3
            ),
            media_type="text/event-stream",
        )
    except Exception as e:
        logger.error(f"Mock interview stream error: {e}")
        raise APIException(
            status_code=500,
            code=ErrorCode.AGENT_WORKFLOW_ERROR,
            message="启动模拟面试失败",
            details={"error": str(e)},
        )
