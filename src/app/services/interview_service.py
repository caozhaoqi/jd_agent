import asyncio
from app.schemas.interview import InterviewReport, JDRequest
from app.chains.jd_parser import parse_jd_async
from app.chains.tech_gen import generate_tech_async
from app.chains.hr_gen import generate_hr_async
from app.chains.company_research import research_company
from app.utils.logger import logger


async def generate_interview_guide(request: JDRequest) -> InterviewReport:
    logger.info("🤖 [Service] Starting interview guide generation...")
    logger.debug(f"📄 [JD Content Preview]: {request.jd_text[:50]}...")  # 只记录前50个字防止刷屏

    try:
        # 1. 解析 JD
        logger.info("⏳ Parsing JD...")
        jd_meta = await parse_jd_async(request.jd_text)
        logger.debug(f"✅ JD Parsed: Tech={jd_meta.tech_stack}, Company={jd_meta.company_name}")

        # 2. 并行生成
        logger.info("🚀 Launching parallel tasks (Tech + Research)...")
        task_tech = generate_tech_async(jd_meta.tech_stack, jd_meta.years_required)
        task_research = research_company(jd_meta.company_name)

        tech_qs, company_info = await asyncio.gather(task_tech, task_research)
        logger.info("✅ Parallel tasks completed.")

        # 3. 生成 HR 题
        logger.info("⏳ Generating HR questions...")
        hr_qs = await generate_hr_async(jd_meta.soft_skills, company_info)

        # 4. 返回
        logger.success("🎉 Guide generated successfully!")
        return InterviewReport(...)

    except Exception as e:
        logger.error(f"❌ [Service Error]: {str(e)}")
        raise e  # 抛出给中间件处理