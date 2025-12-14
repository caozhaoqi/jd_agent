from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.core.graph_state import AgentState

# ✅ 核心修复：显式导入所有节点函数
from app.graph.nodes import (
    jd_parser_node,
    researcher_node,
    tech_lead_node,
    hr_node,
    reviewer_node,
    human_approval_node
)


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
        logger.debug(f"⚠️ [Router] 质量评分 {state.get('quality_score')} < 85，需要人工审核")
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

# 2. Parser -> 并行执行
workflow.add_edge("parser", "tech_lead")
workflow.add_edge("parser", "hr_agent")
workflow.add_edge("parser", "researcher")

# 3. 分支汇聚
workflow.add_edge("hr_agent", END)
workflow.add_edge("researcher", END)

# 4. 质量控制循环
workflow.add_edge("tech_lead", "reviewer")

workflow.add_conditional_edges(
    "reviewer",
    qa_router,
    {
        "approved": END,
        "human_review_needed": "human_node"
    }
)

# 5. 人工确认后 -> 重写
workflow.add_edge("human_node", "tech_lead")

# --- 持久化配置 ---
checkpointer = MemorySaver()

# 编译图
app_graph = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["human_node"]  # 遇到 human_node 前自动暂停
)