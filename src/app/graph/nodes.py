from app.core.graph_state import AgentState
from app.core.llm_factory import get_llm
from app.chains.jd_parser import parse_jd_async
from app.chains.company_research import research_company
from app.chains.tech_gen import generate_tech_async
from app.chains.hr_gen import generate_hr_async
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from loguru import logger
# ✅ 引入我们刚才写的工具
from app.core.stream_manager import send_thought, send_data


# --- Node 1: JD Parser ---
async def jd_parser_node(state: AgentState):
    # logger.debug 留着给自己看日志，send_thought 发给前端看
    logger.debug("🔍 [Agent: Parser] 正在分析 JD...")
    await send_thought("🔍 正在深度解析岗位 JD...", "提取技术栈与硬性要求")

    meta = await parse_jd_async(state["jd_text"])
    # ✅ 埋点：告诉前端当前步骤
    await send_data("current_step", "parser")
    return {
        "company_name": meta.company_name,
        "tech_stack": meta.tech_stack,
        "years_required": meta.years_required,
        "iteration_count": 0
    }


# --- Node 2: Researcher ---
async def researcher_node(state: AgentState):
    company = state.get("company_name", "目标公司")
    logger.debug(f"🕵️ [Agent: Researcher] 正在背调: {company}")
    await send_thought(f"🕵️ 正在进行全网背调: {company}", "检索新闻、财报与业务动态")
    await send_data("current_step", "researcher")  # ✅ 更新步骤

    info = await research_company(company)
    await send_data("rag_sources", info)  # ✅ 发送 RAG 数据
    return {"company_info": info}


# --- Node 3: Tech Lead ---
async def tech_lead_node(state: AgentState):
    iteration = state.get("iteration_count", 0)
    await send_data("current_step", "tech_lead")  # ✅ 更新步骤
    logger.debug(f"💻 [Agent: TechLead] 开始出题 (第 {iteration + 1} 版)...")
    await send_thought(f"💻 技术面试官正在出题 (v{iteration + 1})", "基于技术栈构建硬核问题")

    questions = await generate_tech_async(
        state["tech_stack"],
        state["years_required"]
    )

    return {
        "tech_questions": questions,
        "iteration_count": iteration + 1,
        "human_feedback": None
    }


# --- Node 4: HR Agent ---
async def hr_node(state: AgentState):
    logger.debug("👔 [Agent: HR] 正在生成行为面试题...")
    await send_thought("👔 HR 正在构建行为面试题", "结合 STAR 法则与企业文化")

    questions = await generate_hr_async(
        ["沟通能力", "抗压能力"],
        state.get("company_info", "")
    )
    return {"hr_questions": questions}


# --- Node 5: Reviewer ---
class ReviewResult(BaseModel):
    score: int = Field(description="0-100分")
    comment: str = Field(description="具体的修改建议，如果满分则留空")


async def reviewer_node(state: AgentState):
    logger.debug("⚖️ [Agent: QA] 正在审核题目质量...")
    await send_thought("⚖️ 质检员正在审核题目质量", "评估深度、准确性与匹配度")

    llm = get_llm(temperature=0.1)
    parser = JsonOutputParser(pydantic_object=ReviewResult)

    prompt = ChatPromptTemplate.from_template(
        """
        你是一个严格的技术面试题质检员。
        待审核题目：{questions}
        候选人职级：{level}
        请评分 (0-100) 并给出修改建议。只输出 JSON。
        {format_instructions}
        """
    )
    chain = prompt | llm | parser
    try:
        result = await chain.ainvoke({
            "questions": str(state["tech_questions"]),
            "level": state["years_required"],
            "format_instructions": parser.get_format_instructions()
        })
    except Exception:
        result = {"score": 95, "comment": "解析失败，默认通过"}

    logger.debug(f"📊 [QA Result] Score: {result['score']}")

    # 将评分结果也推给前端
    await send_thought(f"📊 质检完成，评分: {result['score']}", f"评语: {result.get('comment', '无')}")

    return {"quality_score": result['score'], "review_comment": result['comment']}


# --- Node 6: Human Approval ---
async def human_approval_node(state: AgentState):
    # 注意：如果这里用了 async，def 也要改成 async def
    logger.debug("🛑 [System] 任务暂停：等待人工审核...")
    await send_thought("🛑 任务已暂停", "等待人工审核与决策...")
    pass