import json
import asyncio
from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlmodel import Session
from loguru import logger

from app.api.deps import get_current_user, get_session
from app.core.models import User, ChatSession, ChatMessage
from app.schemas.interview import JDRequest, InterviewReport
from app.services.interview_service import generate_interview_guide
from app.services.memory_service import update_long_term_memory
from app.services.mock_service import run_mock_interview_stream
from app.graph.workflow import app_graph
from app.core.stream_manager import init_stream_queue

router = APIRouter()


# ==========================================
# 4. 核心生成接口 (Core Logic)
# ==========================================
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


@router.post("/stream/generate-guide")  # 新增一个流式接口
async def stream_generate_guide(
        request: JDRequest,
        # user: User = Depends(get_current_user),
        # db: Session = Depends(get_session)
):
    # 测试用：模拟用户和数据库
    from app.core.models import User
    from sqlmodel import Session
    user = User(id=1, username="test_user", email="test@example.com")
    db = None
    """
    L5 级 Agent 流式生成接口 (支持 DeepSeek 思考过程)
    """

    # 1. 初始化队列 (ContextVar 会自动绑定到当前 task)
    queue = init_stream_queue()

    # 2. 定义后台运行任务
    async def run_graph_background():
        try:
            initial_state = {
                "jd_text": request.jd_text,
                "user_id": user.id,
                "iteration_count": 0,
                "tech_stack": [],
                "years_required": "",
                "company_name": ""
            }

            thread_id = f"user_{user.id}_job_{hash(request.jd_text)}"
            config = {"configurable": {"thread_id": thread_id}}

            # 运行 Graph
            final_state = await app_graph.ainvoke(initial_state, config=config)

            # 运行结束，把最终结果构造成 token 类型发出去
            # 注意：这里我们把整个 Report 打包成一个 JSON 字符串发过去
            # 前端收到 type='result' 时，直接渲染最终报告
            from app.schemas.interview import InterviewReport, JDMetaData

            # --- 🟢 核心修复开始 ---
            # 1. 处理 Technical Questions
            raw_tech_qs = final_state.get("tech_questions", [])
            # 如果是 Pydantic 对象，转为 dict；如果是 dict (如解析失败fallback)，保持原样
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

            # ... 组装 Report 逻辑 (同 interview_service) ...
            # 为了演示，简单组装
            # 简单构造 Meta
            final_meta = {
                "company_name": final_state.get("company_name"),
                "tech_stack": final_state.get("tech_stack"),
                "years_required": final_state.get("years_required"),
                "soft_skills": []  # 暂空
            }

            final_report = {
                "meta": final_meta,
                "tech_questions": tech_qs_dicts,
                "hr_questions": hr_qs_dicts,
                "company_analysis": final_state.get("company_info"),
                "session_id": None
            }

            # --- 存库逻辑 (可选，建议加上) ---
            try:
                if db is not None:
                    title = f"{final_meta['company_name']} 面试准备" if final_meta['company_name'] else "JD 分析"
                    new_sess = ChatSession(title=title, user_id=user.id)
                    db.add(new_sess)
                    db.commit()
                    db.refresh(new_sess)
                    final_report["session_id"] = new_sess.id
                    # 保存消息
                    db.add(ChatMessage(session_id=new_sess.id, role="user", content=request.jd_text))
                    db.add(ChatMessage(session_id=new_sess.id, role="assistant", content=json.dumps(final_report)))
                    db.commit()
            except Exception as db_e:
                logger.error(f"DB Error: {db_e}")

            await queue.put({
                "type": "result",  # 标记为最终结果
                "content": json.dumps(final_report)
            })


        except Exception as e:

            logger.error(f"❌ [Graph Error] {e}")  # 打印错误堆栈

            await queue.put({"type": "error", "content": str(e)})

        finally:
            # 发送结束信号
            await queue.put(None)

            # 3. 启动后台任务

    task = asyncio.create_task(run_graph_background())

    # 4. 定义生成器 (消费队列)
    async def event_generator():
        while True:
            # 等待队列消息
            data = await queue.get()

            if data is None:  # 结束信号
                yield "data: [DONE]\n\n"
                break

            # 发送 SSE
            yield f"data: {json.dumps(data)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")



@router.post("/agent/feedback")
async def agent_feedback(thread_id: str, feedback: str, action: str = "retry"):
    """
    用户对 AI 暂停的任务进行干预
    action: "approve" (强制通过) | "retry" (带意见重试)
    """
    config = {"configurable": {"thread_id": thread_id}}

    if action == "approve":
        # 强制更新状态：把分数改成 100，这样路由就会通过
        app_graph.update_state(config, {"quality_score": 100, "human_feedback": "强制通过"})
    else:
        # 注入用户的修改意见
        app_graph.update_state(config, {"human_feedback": feedback})

    # 恢复执行 (Resume)
    # 这里的 None 表示继续执行下一步 (即进入 tech_lead 重写)
    async for event in app_graph.astream(None, config=config):
        pass

    return {"status": "Resumed"}

@router.post("/stream/mock-interview")
async def stream_mock_interview(request: JDRequest):
    return StreamingResponse(run_mock_interview_stream(request.jd_text, rounds=3), media_type="text/event-stream")
