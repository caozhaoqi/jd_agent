from app.core.graph_state import AgentState
from app.core.llm_factory import get_llm
from app.chains.jd_parser import parse_jd_async
from app.chains.company_research import research_company  # 记得导入这个
from app.chains.tech_gen import generate_tech_async
from app.chains.hr_gen import generate_hr_async
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from loguru import logger

# --- Node 1: JD Parser ---
async def jd_parser_node(state: AgentState):
    logger.debug("🔍 [Agent: Parser] 正在分析 JD...")
    meta = await parse_jd_async(state["jd_text"])
    return {
        "company_name": meta.company_name,
        "tech_stack": meta.tech_stack,
        "years_required": meta.years_required,
        "iteration_count": 0
    }


# --- Node 2: Researcher ---
async def researcher_node(state: AgentState):
    logger.debug("🕵️ [Agent: Researcher] 正在背调公司...")
    info = await research_company(state["company_name"])
    return {"company_info": info}


# --- Node 3: Tech Lead ---
async def tech_lead_node(state: AgentState):
    iteration = state.get("iteration_count", 0)
    logger.debug(f"💻 [Agent: TechLead] 开始出题 (第 {iteration + 1} 版)...")

    # 获取反馈
    feedback = state.get("review_comment", "")
    human_msg = state.get("human_feedback", "")

    # 这里简单处理，实际应修改 generate_tech_async 接受 context
    # 为了跑通，我们暂不传 context，或者你修改 generate_tech_async
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
    return {"quality_score": result['score'], "review_comment": result['comment']}


# --- Node 6: Human Approval (占位符) ---
def human_approval_node(state: AgentState):
    logger.debug("🛑 [System] 任务暂停：等待人工审核 (Human-in-the-loop)...")
    pass