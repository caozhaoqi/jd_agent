# 确保导入了 JDMetaData
import asyncio
from sqlmodel import Session

from app.core.stream_manager import send_data, init_stream_queue, send_done, send_token
from app.graph.workflow import app_graph
from app.schemas.interview import InterviewReport, JDRequest, JDMetaData
from loguru import logger

from app.services.memory_service import get_user_profile_str


async def generate_interview_guide(
    request: JDRequest, db: Session, user_id: int
) -> InterviewReport:
    logger.info("🚀 [L5 Agent] Starting Multi-Agent Swarm...")
    # 1. 获取记忆
    ltm_profile = get_user_profile_str(db, user_id)

    # 1. 准备初始状态
    thread_id = f"user_{user_id}_job_{hash(request.jd_text)}"
    initial_state = {
        "jd_text": request.jd_text,
        "user_id": user_id,
        "interview_type": request.interview_type,
        "iteration_count": 0,
        "tech_stack": [],  # 初始化空列表防止 KeyErr
        "years_required": "",  # 初始化
        "company_name": "",  # 初始化
        "thread_id": thread_id,  # ✅ 直接添加到state中
    }

    # 2. 运行 Graph
    config = {"configurable": {"thread_id": thread_id}}

    # ✅ 初始化队列
    queue = init_stream_queue(thread_id=thread_id)

    # ✅ 埋点：发送用户画像，传递thread_id
    tags = [line.strip("- ") for line in ltm_profile.split("\n") if line.strip()]
    await send_data("user_profile", tags, thread_id)

    # 运行到结束（或者暂停点）- 使用astream实现流式处理
    final_state = None
    async for event in app_graph.astream(initial_state, config=config):
        if event and "values" in event:
            final_state = event["values"]

    # 获取最终状态快照以检查是否需要人工介入
    snapshot = app_graph.get_state(config)
    if final_state is None:
        final_state = snapshot.values

    # 发送结束信号到队列 - 延迟一下确保所有节点的思考过程都已发送
    import asyncio

    await asyncio.sleep(0.5)
    await send_done(thread_id)

    # 3. 检查是否需要人工介入
    if snapshot.next and snapshot.next[0] == "human_node":
        # 构造临时的 Meta 数据（即使暂停了，Parser 应该已经跑完了）
        temp_meta = JDMetaData(
            tech_stack=final_state.get("tech_stack", []),
            years_required=final_state.get("years_required", "未知"),
            core_responsibility="正在分析中...",
            soft_skills=[],
            company_name=final_state.get("company_name", ""),
        )

        return InterviewReport(
            meta=temp_meta,  # 🟢 修复点：必须提供 meta
            tech_questions=final_state.get("tech_questions", []),
            hr_questions=[],
            system_design_question=None,
            # 利用 company_analysis 字段传达状态
            company_analysis=f"⚠️ 任务暂停：质检员建议修改 - {final_state.get('review_comment')}",
        )

    # 4. 正常结束，组装完整报告
    # 🟢 核心修复：显式构造 meta 对象
    final_meta = JDMetaData(
        tech_stack=final_state.get("tech_stack", []),
        years_required=final_state.get("years_required", "不限"),
        core_responsibility="AI 自动提取",  # 或者从 state 中获取
        soft_skills=[],  # 或者从 state 中获取
        company_name=final_state.get("company_name", ""),
    )

    return InterviewReport(
        meta=final_meta,  # 🟢 赋值 meta
        tech_questions=final_state.get("tech_questions", []),
        hr_questions=final_state.get("hr_questions", []),
        system_design_question=None,
        company_analysis=final_state.get("company_info", ""),
        reference_sources=[],  # 如果有 RAG 来源可以加上
    )
