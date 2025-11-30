from typing import List, Optional  # <--- 1. 必须导入 Optional
from pydantic import BaseModel, Field


# 1. 接收前端传来的 JD
class JDRequest(BaseModel):
    jd_text: str = Field(..., description="岗位描述的完整文本")
    resume_text: Optional[str] = Field(None, description="可选：候选人简历")


# 2. JD 解析后的结构化数据
class JDMetaData(BaseModel):
    tech_stack: List[str] = Field(description="技术栈列表，如 Python, K8s")
    years_required: str = Field(description="经验要求")
    core_responsibility: str = Field(description="核心职责摘要")
    soft_skills: List[str] = Field(description="软技能列表")
    company_name: Optional[str] = Field(default="", description="公司名称")


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