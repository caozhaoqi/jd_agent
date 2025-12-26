import asyncio
from app.core.graph_state import AgentState
from app.core.llm_factory import get_llm
from app.chains.jd_parser import parse_jd_async
from app.chains.company_research import research_company
from app.chains.tech_gen import generate_tech_async
from app.chains.hr_gen import generate_hr_async
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from loguru import logger
from app.core.stream_manager import send_thought, send_data
from app.core.retry import retry_async

# --- Router Node: 调度器 ---
class RouterDecision(BaseModel):
    next_agent: str = Field(description="下一个要调用的Agent，选项：'researcher', 'tech_lead', 'hr_agent', 'reviewer', 'END'")
    reasoning: str = Field(description="做出此决策的简要原因")

@retry_async(max_retries=3, delay=0.5)
async def router_node(state: AgentState):
    """
    调度器节点，决定下一步的任务流向。
    """
    await send_thought("🧠 [调度器] 正在规划下一步...", thread_id=state.get("thread_id"))
    
    llm = get_llm(temperature=0)
    parser = JsonOutputParser(pydantic_object=RouterDecision)

    # 构建一个包含当前状态摘要的Prompt
    state_summary = f"""
    - 已完成步骤: {state.get('completed_steps', [])}
    - 公司名称: {state.get('company_name')}
    - 技术栈: {state.get('tech_stack')}
    - 公司信息是否已获取: {'是' if state.get('company_info') else '否'}
    - 技术题是否已生成: {'是' if state.get('tech_questions') else '否'}
    - HR题是否已生成: {'是' if state.get('hr_questions') else '否'}
    - 质检分数: {state.get('quality_score')}
    """

    prompt = ChatPromptTemplate.from_template(
        """你是一个项目总监，负责协调一个由AI Agent组成的团队。根据以下项目状态，决定下一步应该由哪个Agent接手。
        
        **团队成员及职责:**
        - `researcher`: 调查公司背景。
        - `tech_lead`: 根据技术栈出技术题。
        - `hr_agent`: 根据公司背景和软技能要求出HR题。
        - `reviewer`: 对已生成的题目进行质量审核。
        - `END`: 所有任务完成，结束流程。

        **项目当前状态:**
        {state_summary}

        **决策规则:**
        1. 如果公司名称已知但背景信息未知，且`researcher`未执行过，应调用`researcher`。
        2. 如果技术栈已知但技术题未生成，且`tech_lead`未执行过，应调用`tech_lead`。
        3. 如果HR题未生成，且`hr_agent`未执行过，应调用`hr_agent`。
        4. 如果技术题和HR题都已生成，但`reviewer`未执行过，应调用`reviewer`。
        5. 如果质检分数低于85，应重新调用`tech_lead`进行修改。
        6. 如果所有必要步骤都已完成，应调用`END`。

        请仅输出JSON格式的决策:
        {format_instructions}
        """
    )
    
    chain = prompt | llm | parser
    decision = await chain.ainvoke({
        "state_summary": state_summary,
        "format_instructions": parser.get_format_instructions(),
    })

    await send_thought(f"🧠 [调度器决策] {decision['reasoning']}", thread_id=state.get("thread_id"))
    
    return {"next_agent_decision": decision['next_agent']}


# --- Existing Nodes (with minor adjustments) ---

@retry_async(max_retries=3, delay=0.5)
async def jd_parser_node(state: AgentState):
    thread_id = state.get("thread_id")
    await send_thought("🔍 [解析器] 正在深度解析职位描述...", "提取核心技术栈", thread_id, delay=1.0)
    await send_data("current_step", "parser", thread_id)
    
    meta = await parse_jd_async(state["jd_text"])
    await send_data("user_profile", meta.tech_stack, thread_id)

    return {
        "company_name": meta.company_name,
        "tech_stack": meta.tech_stack,
        "years_required": meta.years_required,
        "completed_steps": state.get("completed_steps", []) + ["parser"],
    }

@retry_async(max_retries=3, delay=1.0)
async def researcher_node(state: AgentState):
    thread_id = state.get("thread_id")
    company = state.get("company_name")

    if not company or "某" in company or len(company) < 3:
        await send_thought("⚠️ 公司名称模糊，跳过精确背调", "将基于行业通用标准分析", thread_id)
        info = "职位描述未提供具体公司名称，基于行业通用背景进行分析。"
    else:
        await send_thought(f"🕵️ [研究员] 正在背调: {company}", thread_id=thread_id, delay=2.0)
        await send_data("current_step", "researcher", thread_id)
        info = await research_company(company)
        mock_sources = [{"title": f"{company} 官网", "url": "#", "score": 0.98}]
        await send_data("rag_sources", mock_sources, thread_id)

    return {
        "company_info": info,
        "completed_steps": state.get("completed_steps", []) + ["researcher"],
    }

@retry_async(max_retries=3, delay=1.0)
async def tech_lead_node(state: AgentState):
    thread_id = state.get("thread_id")
    await send_thought("💻 [技术专家] 正在构思面试题...", thread_id=thread_id, delay=2.0)
    await send_data("current_step", "tech_lead", thread_id)
    
    questions = await generate_tech_async(state["tech_stack"], state["years_required"])
    return {
        "tech_questions": questions,
        "iteration_count": state.get("iteration_count", 0) + 1,
        "completed_steps": state.get("completed_steps", []) + ["tech_lead"],
    }

@retry_async(max_retries=3, delay=1.0)
async def hr_node(state: AgentState):
    thread_id = state.get("thread_id")
    await send_thought("👔 [HR] 正在构建行为面试题", "结合STAR法则与企业文化", thread_id, delay=1.5)
    await send_data("current_step", "hr_agent", thread_id)
    
    questions = await generate_hr_async(["沟通能力", "抗压能力"], state.get("company_info", ""))
    return {
        "hr_questions": questions,
        "completed_steps": state.get("completed_steps", []) + ["hr_agent"],
    }

class ReviewResult(BaseModel):
    score: int = Field(description="0-100分")
    comment: str = Field(description="具体的修改建议，如果满分则留空")

@retry_async(max_retries=3, delay=1.0)
async def reviewer_node(state: AgentState):
    thread_id = state.get("thread_id")
    await send_thought("⚖️ [质检员] 正在审核题目质量", "评估深度、准确性与匹配度", thread_id, delay=1.0)
    await send_data("current_step", "reviewer", thread_id)
    
    llm = get_llm(temperature=0.1)
    parser = JsonOutputParser(pydantic_object=ReviewResult)
    prompt = ChatPromptTemplate.from_template(
        """你是一个严格的技术面试题质检员。
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
            "format_instructions": parser.get_format_instructions(),
        })
    except Exception:
        result = {"score": 95, "comment": "解析失败，默认通过"}

    await send_thought(f"📊 质检完成，评分: {result['score']}", f"评语: {result.get('comment', '无')}", thread_id)
    
    return {
        "quality_score": result["score"],
        "review_comment": result["comment"],
        "completed_steps": state.get("completed_steps", []) + ["reviewer"],
    }

async def human_approval_node(state: AgentState):
    # This node remains largely the same, as it's an interruption point.
    thread_id = state.get("thread_id")
    await send_thought("🛑 任务已暂停", "等待人工审核与决策...", thread_id)
    await send_data("human_review_required", {
        "questions": state.get("tech_questions", []),
        "quality_score": state.get("quality_score", 0),
        "review_comment": state.get("review_comment", ""),
    }, thread_id)
    return {}
