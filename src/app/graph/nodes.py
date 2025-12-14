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
# ✅ 引入重试装饰器
from app.core.retry import retry_async


# --- Node 1: JD Parser ---
@retry_async(max_retries=3, delay=0.5, backoff=1.5)
async def jd_parser_node(state: AgentState):
    await send_thought("🔍 [Parser] 正在深度解析 JD...", "提取核心技术栈")
    # ✅ 触发 Dashboard 更新: 步骤高亮
    await send_data("current_step", "parser")

    meta = await parse_jd_async(state["jd_text"])

    # ✅ 触发 Dashboard 更新: 用户画像 (Tech Stack)
    await send_data("user_profile", meta.tech_stack)

    return {
        "company_name": meta.company_name,
        "tech_stack": meta.tech_stack,
        "years_required": meta.years_required,
        "iteration_count": 0
    }


# --- Node 2: Researcher ---
@retry_async(max_retries=3, delay=1.0, backoff=2.0)
async def researcher_node(state: AgentState):
    company = state.get("company_name")

    # 1. 预判：如果是模糊指代，直接跳过搜索
    # 简单判断：是否包含 "某", "知名", "头部" 且不包含 "公司" 或字数太少
    if not company or "某" in company or len(company) < 4:
        await send_thought("⚠️ 公司名称模糊，跳过精确背调", "将基于行业通用标准分析")
        return {"company_info": "JD 未提供具体公司名称，基于行业通用背景进行分析。"}

    await send_thought(f"🕵️ [Researcher] 正在背调: {state.get('company_name')}")
    # ✅ 触发 Dashboard 更新
    await send_data("current_step", "researcher")

    info = await research_company(state["company_name"])

    # ✅ 触发 Dashboard 更新: RAG 来源 (模拟数据，实际应从 research_company 返回)
    # 如果 research_company 返回的是字符串，这里可以构造一个假的或者修改 chain 返回结构
    mock_sources = [
        {"title": f"{state.get('company_name')} 官网", "url": "#", "score": 0.98},
        {"title": "AI 商业分析报告", "url": "#", "score": 0.85}
    ]
    await send_data("rag_sources", mock_sources)

    return {"company_info": info}


# --- Node 3: Tech Lead ---
@retry_async(max_retries=3, delay=1.0, backoff=2.0)
async def tech_lead_node(state: AgentState):
    await send_thought("💻 [TechLead] 正在构思面试题...")
    # ✅ 触发 Dashboard 更新
    await send_data("current_step", "tech_lead")

    questions = await generate_tech_async(
        state["tech_stack"],
        state["years_required"]
    )
    return {"tech_questions": questions, "iteration_count": state.get("iteration_count", 0) + 1}


# --- Node 4: HR Agent ---
@retry_async(max_retries=3, delay=1.0, backoff=2.0)
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


@retry_async(max_retries=3, delay=1.0, backoff=2.0)
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
    logger.debug("🛑 [System] 任务暂停：等待人工审核...")
    await send_thought("🛑 任务已暂停", "等待人工审核与决策...")
    
    # 获取当前状态信息用于人工审核
    current_questions = state.get("tech_questions", [])
    review_comment = state.get("review_comment", "")
    quality_score = state.get("quality_score", 0)
    
    # 发送详细的审核信息给前端
    await send_data("human_review_required", {
        "type": "tech_questions",
        "questions": current_questions,
        "quality_score": quality_score,
        "review_comment": review_comment,
        "iteration_count": state.get("iteration_count", 0)
    })
    
    # 如果已经有人工反馈，则应用反馈
    if state.get("human_feedback"):
        logger.info(f"✅ [Human] 收到人工反馈: {state['human_feedback']}")
        await send_thought(f"✅ 已应用人工反馈", state['human_feedback'])
        # 重置质量分数为90分（通过），并更新迭代计数
        return {
            "quality_score": 90,
            "review_comment": f"人工审核通过: {state['human_feedback']}",
            "human_feedback": None  # 清空反馈，避免重复应用
        }
    
    # 如果没有人工反馈，继续等待（由前端通过API提交反馈）
    return {}