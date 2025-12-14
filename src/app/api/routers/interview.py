import json
import asyncio
from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.sql.functions import user
from sqlmodel import Session
from loguru import logger

from app.api.deps import get_current_user, get_session
from app.core.models import User, ChatSession, ChatMessage
from app.schemas import JDRequest, InterviewReport, APIException, ErrorCode
from app.services.interview_service import generate_interview_guide
from app.services.memory_service import update_long_term_memory
from app.services.mock_service import run_mock_interview_stream
from app.graph.workflow import app_graph
from app.core.stream_manager import init_stream_queue

router = APIRouter()


# ==========================================
# 4. 核心生成接口 (Core Logic)
# ==========================================
@router.post("/guide", response_model=InterviewReport, summary="创建面试指南", description="根据提供的岗位JD生成完整的面试指南报告，包括公司分析、技术问题和HR问题。")
async def create_guide(
        request: JDRequest,
        background_tasks: BackgroundTasks,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_session),
):
    try:
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

        except Exception as db_e:
            logger.error(f"❌ [DB Error] {db_e}")
            # 数据库错误不影响主流程

        # 3. 更新长期记忆
        background_tasks.add_task(update_long_term_memory, db, user.id, f"User上传了JD: {request.jd_text}")

        return report
    except Exception as e:
        logger.error(f"❌ [Generate Guide Error] {e}")
        raise APIException(
            status_code=500,
            code=ErrorCode.JD_PARSE_ERROR,
            message="生成面试指南失败",
            details={"error": str(e)}
        )


@router.post("/guide/stream", summary="流式生成面试指南", description="根据提供的岗位JD流式生成面试指南，实时返回生成过程，支持DeepSeek思考过程展示。")
async def stream_generate_guide(
        request: JDRequest,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_session)
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
        # 创建共享队列
        shared_queue = asyncio.Queue()
        
        # 测试用：模拟用户和数据库
        from app.core.models import User
        from sqlmodel import Session
        # 测试账户
        # user = User(id=1, username="test_user", email="test@example.com")
        # db = None

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
                
                # 将队列与thread_id关联
                init_stream_queue(shared_queue, thread_id)

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

                await shared_queue.put({
                    "type": "result",  # 标记为最终结果
                    "content": json.dumps(final_report)
                })

            except Exception as e:
                logger.error(f"❌ [Graph Error] {e}")  # 打印错误堆栈
                await shared_queue.put({"type": "error", "content": {
                    "status": "error",
                    "code": ErrorCode.JD_PARSE_ERROR,
                    "message": "生成面试指南失败",
                    "details": {"error": str(e)}
                }})

            finally:
                # 发送结束信号
                await shared_queue.put(None)

        # 3. 启动后台任务
        task = asyncio.create_task(run_graph_background())

        # 4. 定义生成器 (消费队列)
        async def event_generator():
            while True:
                # 等待队列消息
                data = await shared_queue.get()

                if data is None:  # 结束信号
                    yield "data: [DONE]\n\n"
                    break

                # 发送 SSE
                yield f"data: {json.dumps(data)}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except Exception as e:
        logger.error(f"❌ [Stream Generate Guide Error] {e}")
        # 对于流式响应，我们需要在生成器中处理错误
        # 这里返回一个包含错误信息的流式响应
        async def error_generator():
            error_data = {
                "type": "error",
                "content": {
                    "status": "error",
                    "code": ErrorCode.JD_PARSE_ERROR,
                    "message": "生成面试指南失败",
                    "details": {"error": str(e)}
                }
            }
            yield f"data: {json.dumps(error_data)}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(error_generator(), media_type="text/event-stream")



@router.post("/feedback/{thread_id}", summary="AI任务反馈", description="用户对AI暂停的任务进行干预，支持强制通过或带意见重试。")
async def agent_feedback(
    thread_id: str, 
    feedback: str, 
    action: str = "retry",
    user: User = Depends(get_current_user)
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
            app_graph.update_state(config, {"quality_score": 100, "human_feedback": "强制通过"})
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
            details={"error": str(e)}
        )

@router.post("/mock-interview/stream", summary="流式模拟面试", description="根据提供的岗位JD启动流式模拟面试，实时返回面试官和候选人的对话过程。")
async def stream_mock_interview(request: JDRequest, user: User = Depends(get_current_user)):
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
        return StreamingResponse(run_mock_interview_stream(request.jd_text, rounds=3), media_type="text/event-stream")
    except Exception as e:
        logger.error(f"Mock interview stream error: {e}")
        raise APIException(
            status_code=500,
            code=ErrorCode.AGENT_WORKFLOW_ERROR,
            message="启动模拟面试失败",
            details={"error": str(e)}
        )
