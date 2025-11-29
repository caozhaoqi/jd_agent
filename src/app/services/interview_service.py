import asyncio
from app.schemas.interview import InterviewReport, JDRequest
from app.chains.jd_parser import parse_jd_async
from app.chains.tech_gen import generate_tech_async
from app.chains.hr_gen import generate_hr_async
from app.chains.company_research import research_company
from app.chains.critique import critique_tech_questions_async  # 导入反思链
from app.utils.logger import logger
from app.core.knowledge_base import kb_engine
from sqlmodel import Session
from app.core.memory import get_recent_chat_history  # 导入短期记忆工具
# 🔴 导入长期记忆工具 (如果没有请确保之前已创建 app/services/memory_service.py)
from app.services.memory_service import get_user_profile_str


async def generate_interview_guide(
        request: JDRequest,
        db: Session,  # 接收数据库 Session
        user_id: int  # 接收当前用户 ID
) -> InterviewReport:
    logger.info("🤖 [Service] Starting generation with Memory & RAG & Reflection...")

    try:
        # 1. 获取记忆 (Memory)
        # 短期记忆 (最近对话)
        chat_history = get_recent_chat_history(db, user_id)
        # 🔴 长期记忆 (用户画像)
        ltm_profile = get_user_profile_str(db, user_id)

        logger.info(f"🧠 [Memory] Loaded {len(chat_history)} recent msgs. Profile len: {len(ltm_profile)}")

        # 2. 解析 JD
        jd_meta = await parse_jd_async(request.jd_text)

        # 3. RAG 检索 (查博客)
        logger.info(f"🔍 [RAG] Searching blog for: {jd_meta.tech_stack}")
        query_text = " ".join(jd_meta.tech_stack)
        kb_result = await kb_engine.search(query_text, top_k=3)
        blog_context = kb_result["context"]
        blog_sources = kb_result["sources"]

        if blog_sources:
            logger.info(f"📚 [RAG] Hit knowledge: {blog_sources}")

        # 4. 第一轮生成 (Drafting Phase)
        # 🔴 核心修复：这里必须传入 user_profile 参数！
        task_tech_draft = generate_tech_async(
            tech_stack=jd_meta.tech_stack,
            level=jd_meta.years_required,
            kb_context=blog_context,
            chat_history=chat_history,  # 传入短期记忆
            user_profile=ltm_profile  # 🔴 传入长期记忆 (修复 KeyError)
        )

        company_name = getattr(jd_meta, "company_name", "")
        task_research = research_company(company_name)

        # 并发执行初稿生成和背调
        tech_qs_draft, company_info = await asyncio.gather(task_tech_draft, task_research)

        # 5. 反思环节 (Reflection Phase)
        final_tech_qs = await critique_tech_questions_async(
            original_questions=tech_qs_draft,
            level=jd_meta.years_required
        )

        # 6. 生成 HR 题
        hr_qs = await generate_hr_async(jd_meta.soft_skills, company_info)

        # 7. 返回
        return InterviewReport(
            meta=jd_meta,
            tech_questions=final_tech_qs,
            hr_questions=hr_qs,
            system_design_question=None,
            reference_sources=blog_sources
        )

    except Exception as e:
        logger.error(f"❌ [Service Error]: {str(e)}")
        raise e