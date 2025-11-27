import asyncio
from app.schemas.interview import InterviewReport, JDRequest
from app.chains.jd_parser import parse_jd_async
from app.chains.tech_gen import generate_tech_async
from app.chains.hr_gen import generate_hr_async
from app.chains.company_research import research_company
from app.utils.logger import logger


async def generate_interview_guide(request: JDRequest) -> InterviewReport:
    logger.info("🤖 [Service] Starting interview guide generation...")

    try:
        # 1. 解析 JD
        logger.info("⏳ Parsing JD...")
        jd_meta = await parse_jd_async(request.jd_text)
        logger.debug(f"✅ JD Parsed: Tech={jd_meta.tech_stack}")

        # 2. 并行任务：生成技术题 + 公司背调
        logger.info("🚀 Launching parallel tasks (Tech + Research)...")

        # 任务 A
        task_tech = generate_tech_async(jd_meta.tech_stack, jd_meta.years_required)

        # 任务 B (假设 JD 解析里提取了 company_name，如果没有默认空字符串)
        company_name = getattr(jd_meta, "company_name", "")
        task_research = research_company(company_name)

        # 并发等待
        tech_qs, company_info = await asyncio.gather(task_tech, task_research)
        logger.info("✅ Parallel tasks completed.")

        # 3. 生成 HR 题 (依赖公司背景)
        logger.info("⏳ Generating HR questions...")
        hr_qs = await generate_hr_async(jd_meta.soft_skills, company_info)

        # 4. 返回结果
        logger.success("🎉 Guide generated successfully!")

        # 🔴 核心修复点在这里：必须使用关键字参数 (meta=..., tech_questions=...)
        return InterviewReport(
            meta=jd_meta,  # 必须写 meta=
            tech_questions=tech_qs,  # 必须写 tech_questions=
            hr_questions=hr_qs,  # 必须写 hr_questions=
            system_design_question=None  # 必须写 system_design_question=
        )

    except Exception as e:
        logger.error(f"❌ [Service Error]: {str(e)}")
        # 再次抛出异常，以便让外层的 Middleware 捕获并返回 500
        raise e