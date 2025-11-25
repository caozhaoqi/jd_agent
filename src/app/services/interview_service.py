import asyncio
from app.schemas.interview import InterviewReport, JDRequest
from app.chains.jd_parser import parse_jd_async
from app.chains.tech_gen import generate_tech_async
from app.chains.hr_gen import generate_hr_async
from app.chains.company_research import research_company


async def generate_interview_guide(request: JDRequest) -> InterviewReport:
    # 1. 第一步：解析 JD (这是前置依赖，必须等待)
    # 假设你已经把 jd_parser 里的 invoke 改成了 ainvoke
    jd_meta = await parse_jd_async(request.jd_text)

    # 提取公司名称 (假设 JD 解析里提取了 company_name)
    # 如果 JD 里没写，可以尝试提取，这里演示用
    company_name = getattr(jd_meta, "company_name", "")

    # 2. 第二步：开启并行任务 (Fire and Forget)
    # 我们创建三个独立的 Task，让他们同时在后台跑

    # 任务 A: 生成技术题
    task_tech = generate_tech_async(jd_meta.tech_stack, jd_meta.years_required)

    # 任务 B: 公司背调 (网络 IO 密集型)
    task_research = research_company(company_name)

    # 等待 B 完成后再做任务 C (HR题依赖公司背调结果)
    # 或者，如果 HR 题不强依赖背调，也可以完全并行。
    # 这里演示最高效的：Tech 和 (Research + HR) 并行

    async def hr_pipeline():
        # 子流程：先查公司，再出 HR 题
        company_info = await task_research
        # 将公司情报喂给 HR 生成器
        return await generate_hr_async(jd_meta.soft_skills, company_info)

    # 3. 核心优化：使用 asyncio.gather 并发等待
    # 这行代码会同时启动 tech 和 hr_pipeline
    # 总耗时 = max(耗时_tech, 耗时_hr_pipeline)
    tech_qs, hr_qs = await asyncio.gather(
        task_tech,
        hr_pipeline()
    )

    # 4. 组装结果
    return InterviewReport(
        meta=jd_meta,
        tech_questions=tech_qs,
        hr_questions=hr_qs,
        system_design_question=None
    )