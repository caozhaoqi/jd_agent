from typing import List, Optional  # <--- 1. 必须导入 Optional
from pydantic import BaseModel, Field, field_validator


# 1. 接收前端传来的 JD
class JDRequest(BaseModel):
    jd_text: str = Field(..., description="岗位描述的完整文本")
    resume_text: Optional[str] = Field(None, description="可选：候选人简历")
    interview_type: str = Field(
        "comprehensive",
        description="面试类型，支持：tech(技术面试)、hr(HR面试)、comprehensive(综合面试)、behavioral(行为面试)、management(管理面试)",
    )


# 2. JD 解析后的结构化数据
# 2. JD 解析后的结构化数据
class JDMetaData(BaseModel):
    tech_stack: List[str] = Field(
        default_factory=list, description="技术栈列表，如 Python, K8s"
    )

    # 🟢 核心修复：允许为 None，并提供默认值
    years_required: Optional[str] = Field(default="不限", description="经验要求")

    core_responsibility: str = Field(
        default="暂无核心职责描述", description="核心职责摘要"
    )
    soft_skills: List[str] = Field(default_factory=list, description="软技能列表")

    # 同样给公司名称加个容错
    company_name: Optional[str] = Field(default="", description="公司名称")

    # 🟢 进阶修复：如果 LLM 显式返回了 null (None)，强制转为默认字符串
    # 这一步是为了防止后续代码(如生成题目时)用到 years_required 报错
    @field_validator("years_required", mode="before")
    @classmethod
    def handle_none_years(cls, v):
        if v is None:
            return "不限"
        return v


# 3. 单个面试题结构
class InterviewQuestion(BaseModel):
    category: str = Field(description="类别：基础/原理/架构/HR")
    question: str = Field(description="面试题")
    reference_answer: str = Field(description="参考回答要点")


# 4. 最终返回给前端的报告
class InterviewReport(BaseModel):

    # ✅ 新增字段
    session_id: Optional[int] = Field(None, description="数据库中的会话ID")

    meta: JDMetaData
    tech_questions: List[InterviewQuestion]
    hr_questions: List[InterviewQuestion]

    # <--- 核心修改：加上 Optional[...] = None，允许该字段为空
    system_design_question: Optional[InterviewQuestion] = None

    # ✅ 新增这个字段：公司背景分析结果
    company_analysis: Optional[str] = Field(None, description="公司背景调研总结")

    # 🔴 新增字段：参考来源
    reference_sources: List[str] = Field(default=[], description="参考的博客文章列表")
