from typing import List, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.core.graph_state import AgentState
from loguru import logger

# ✅ 核心修复：显式导入所有节点函数
from app.graph.nodes import (
    jd_parser_node,
    researcher_node,
    tech_lead_node,
    hr_node,
    reviewer_node,
    human_approval_node,
)


# --- 动态智能体组合逻辑 ---
def evaluate_jd_complexity(state: AgentState) -> str:
    """
    评估JD的复杂度等级
    - 根据技术栈数量、要求年限和JD长度判断
    """
    tech_stack_len = len(state.get("tech_stack", []))
    years_required = state.get("years_required", "0-1")
    jd_len = len(state.get("jd_text", ""))

    # 复杂度评估规则
    if tech_stack_len > 8 or "5-10" in years_required or jd_len > 3000:
        return "high"
    elif tech_stack_len > 4 or "3-5" in years_required or jd_len > 1500:
        return "medium"
    else:
        return "low"


def select_agents(complexity: str, interview_type: str = "comprehensive") -> List[str]:
    """
    根据JD复杂度和面试类型动态选择智能体组合
    - 高复杂度：完整智能体团队
    - 中复杂度：核心智能体团队
    - 低复杂度：简化智能体团队
    """
    # 基础智能体集合
    base_agents = ["parser", "reviewer"]

    # 根据面试类型添加特定智能体
    if interview_type in ["tech", "comprehensive", "management"]:
        base_agents.append("tech_lead")

    if interview_type in ["hr", "comprehensive", "behavioral"]:
        base_agents.append("hr_agent")

    # 只有高复杂度或综合面试才添加researcher
    if complexity == "high" or interview_type == "comprehensive":
        base_agents.append("researcher")

    return base_agents


# --- 路由逻辑 ---
def qa_router(state: AgentState):
    """
    质量控制路由逻辑
    - 处理正常的质量评分
    - 处理异常情况（如解析失败、网络错误等）
    - 防止死循环
    """
    from loguru import logger

    try:
        # 1. 强制通过机制 (防止死循环)
        if state.get("iteration_count", 0) > 3:
            logger.warning("⚠️ [Router] 循环次数过多，强制通过")
            return "approved"

        # 2. 检查是否有错误状态
        if state.get("error"):
            logger.warning(f"⚠️ [Router] 检测到错误状态: {state['error']}")
            return "human_review_needed"

        # 3. 只有分数高才通过
        if state.get("quality_score", 0) >= 85:
            return "approved"

        # 4. 分数低 -> 进入人工介入环节
        logger.debug(
            f"⚠️ [Router] 质量评分 {state.get('quality_score')} < 85，需要人工审核"
        )
        return "human_review_needed"
    except Exception as e:
        logger.error(f"❌ [Router] 路由逻辑错误: {e}")
        # 异常情况下默认进入人工审核环节
        return "human_review_needed"


# --- 构建图 ---
workflow = StateGraph(AgentState)

# 添加节点
workflow.add_node("parser", jd_parser_node)
workflow.add_node("researcher", researcher_node)
workflow.add_node("tech_lead", tech_lead_node)
workflow.add_node("hr_agent", hr_node)
workflow.add_node("reviewer", reviewer_node)
workflow.add_node("human_node", human_approval_node)

# 编排流程
# 1. Start -> Parser
workflow.set_entry_point("parser")


# 2. Parser -> 根据激活的智能体进行条件路由
# --- 路由逻辑 ---
def route_agents(state: AgentState) -> Optional[str]:
    active_agents = state.get("active_agents", [])
    if "researcher" in active_agents:
        return "researcher"
    if "hr_agent" in active_agents:
        return "hr_agent"
    return None


# 添加条件边，根据活跃智能体选择路由
workflow.add_conditional_edges(
    "parser",
    route_agents,
    {
        "researcher": "researcher",
        "hr_agent": "hr_agent",
        None: "tech_lead",  # 没有匹配智能体时直接进入tech_lead
    },
)

# 3. 分支汇聚 - 确保所有路径最终都经过tech_lead和reviewer
workflow.add_edge("hr_agent", "tech_lead")
workflow.add_edge("researcher", "tech_lead")

# 4. 质量控制循环
workflow.add_edge("tech_lead", "reviewer")

workflow.add_conditional_edges(
    "reviewer", qa_router, {"approved": END, "human_review_needed": "human_node"}
)

# 5. 人工确认后 -> 重写
workflow.add_edge("human_node", "tech_lead")

# --- 持久化配置 ---
checkpointer = MemorySaver()

# 编译图
app_graph = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["human_node"],  # 遇到 human_node 前自动暂停
)
