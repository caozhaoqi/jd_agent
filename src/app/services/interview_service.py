import asyncio
from app.schemas.interview import InterviewReport, JDRequest
from app.chains.jd_parser import parse_jd_async
from app.chains.tech_gen import generate_tech_async
from app.chains.hr_gen import generate_hr_async
from app.chains.company_research import research_company
from app.utils.logger import logger

from app.core.knowledge_base import kb_engine  # 导入我们写的 RAG 引擎


async def generate_interview_guide(request: JDRequest) -> InterviewReport:
    logger.info("🤖 [Service] Starting generation with RAG...")

    try:
        # 1. 解析 JD
        jd_meta = await parse_jd_async(request.jd_text)

        # 2. 并行任务：(生成技术题需要先查库，所以这里稍微调整并行逻辑)
        # 我们先查库，因为查库很快 (毫秒级)
        logger.info(f"🔍 [RAG] Searching blog for: {jd_meta.tech_stack}")

        # 用技术栈关键词去查博客
        query_text = " ".join(jd_meta.tech_stack)
        kb_result = await kb_engine.search(query_text, top_k=3)

        blog_context = kb_result["context"]
        blog_sources = kb_result["sources"]

        if blog_sources:
            logger.info(f"📚 [RAG] Hit knowledge: {blog_sources}")
        else:
            logger.info("📭 [RAG] No relevant blog posts found.")

        # 3. 并行生成题目 (注入查到的 context)
        # 任务 A: 技术题 (带博客上下文)
        task_tech = generate_tech_async(
            jd_meta.tech_stack,
            jd_meta.years_required,
            kb_context=blog_context  # 传入知识
        )

        # 任务 B: 公司背调
        company_name = getattr(jd_meta, "company_name", "")
        task_research = research_company(company_name)

        tech_qs, company_info = await asyncio.gather(task_tech, task_research)

        # 任务 C: HR 题
        hr_qs = await generate_hr_async(jd_meta.soft_skills, company_info)

        # 4. 返回
        return InterviewReport(
            meta=jd_meta,
            tech_questions=tech_qs,
            hr_questions=hr_qs,
            system_design_question=None,
            reference_sources=blog_sources  # 🔴 返回来源给前端
        )

    except Exception as e:
        logger.error(f"❌ [Service Error]: {str(e)}")
        raise e
