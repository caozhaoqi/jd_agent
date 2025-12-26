from typing import TypedDict, List, Optional

class AgentState(TypedDict):
    # --- 基础输入 ---
    jd_text: str
    user_id: int
    thread_id: str
    interview_type: str = "comprehensive"

    # --- 中间态 ---
    company_name: Optional[str]
    tech_stack: List[str]
    years_required: str

    # --- 各 Agent 产出 ---
    company_info: Optional[str]
    tech_questions: List[dict]
    hr_questions: List[dict]

    # --- 质量控制循环 ---
    quality_score: int
    review_comment: str
    human_feedback: Optional[str]
    iteration_count: int
    error: Optional[str]

    # --- 高级 Agent 流程控制字段 ---
    # 记录已完成的节点，防止循环
    completed_steps: List[str]
    # 调度器节点的决策结果
    next_agent_decision: str
