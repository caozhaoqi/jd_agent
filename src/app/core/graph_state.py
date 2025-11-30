from typing import TypedDict, List, Optional, Annotated
import operator


# 定义合并策略：对于 list 类型，我们希望是追加而不是覆盖
def merge_list(a: List, b: List) -> List:
    return a + b


class AgentState(TypedDict):
    # --- 基础输入 ---
    jd_text: str
    user_id: int

    # --- 中间态 ---
    company_name: Optional[str]
    tech_stack: List[str]
    years_required: str

    # --- 各 Agent 产出 ---
    company_info: Optional[str]
    # 使用 Annotated 标记，当多个节点写入时自动合并列表 (可选，或手动管理)
    tech_questions: List[dict]
    hr_questions: List[dict]

    # --- 质量控制循环 ---
    quality_score: int
    review_comment: str  # AI 质检员的具体修改建议
    human_feedback: Optional[str]  # 人工介入时的指令
    iteration_count: int  # 循环计数器