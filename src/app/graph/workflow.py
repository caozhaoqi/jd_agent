from typing import List, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.core.graph_state import AgentState
from loguru import logger

# 导入所有节点函数
from app.graph.nodes import (
    jd_parser_node,
    researcher_node,
    tech_lead_node,
    hr_node,
    reviewer_node,
    human_approval_node,
    router_node,  # 导入新的调度器节点
)


# --- 路由逻辑 ---
def route_next_agent(state: AgentState) -> str:
    """
    根据调度器节点的决策，路由到下一个Agent。
    """
    decision = state.get("next_agent_decision")
    if decision == "END":
        return END
    return decision


# --- 构建图 ---
workflow = StateGraph(AgentState)

# 添加节点
workflow.add_node("parser", jd_parser_node)
workflow.add_node("researcher", researcher_node)
workflow.add_node("tech_lead", tech_lead_node)
workflow.add_node("hr_agent", hr_node)
workflow.add_node("reviewer", reviewer_node)
workflow.add_node("human_node", human_approval_node)
workflow.add_node("router", router_node)  # 添加调度器节点

# 编排流程
# 1. Start -> Parser
workflow.set_entry_point("parser")

# 2. Parser 完成后，进入调度器
workflow.add_edge("parser", "router")

# 3. 调度器根据决策路由到不同的Agent
workflow.add_conditional_edges(
    "router",
    route_next_agent,
    {
        "researcher": "researcher",
        "tech_lead": "tech_lead",
        "hr_agent": "hr_agent",
        "reviewer": "reviewer",
        END: END,  # 调度器可以直接决定结束
    },
)

# 4. 各个Agent完成任务后，再次回到调度器，由调度器决定下一步
workflow.add_edge("researcher", "router")
workflow.add_edge("tech_lead", "router")
workflow.add_edge("hr_agent", "router")

# 5. Reviewer 节点后的逻辑：如果需要人工介入，则进入 human_node，否则回到调度器
def route_after_reviewer(state: AgentState) -> str:
    if state.get("quality_score", 0) < 85:
        return "human_node"
    return "router" # 质检通过，回到调度器，调度器会决定END

workflow.add_conditional_edges(
    "reviewer",
    route_after_reviewer,
    {
        "human_node": "human_node",
        "router": "router",
    },
)

# 6. 人工介入后，回到调度器，调度器会决定重新生成或结束
workflow.add_edge("human_node", "router")


# --- 持久化配置 ---
checkpointer = MemorySaver()

# 编译图
app_graph = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["human_node"],  # 遇到 human_node 前自动暂停
)
