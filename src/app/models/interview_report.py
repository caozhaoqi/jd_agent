from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship


class InterviewReportExport(SQLModel, table=True):
    """面试报告导出记录表"""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    team_id: Optional[int] = Field(default=None, foreign_key="team.id", index=True)
    
    company_name: Optional[str] = Field(default=None, max_length=100)
    position: Optional[str] = Field(default=None, max_length=100)
    
    export_format: str = Field(max_length=20, description="导出格式: pdf, word, markdown")
    report_title: str = Field(max_length=200)
    
    meta_info: Optional[str] = Field(default=None, description="JSON格式的元数据")
    tech_questions: Optional[str] = Field(default=None, description="JSON格式的技术问题列表")
    hr_questions: Optional[str] = Field(default=None, description="JSON格式的HR问题列表")
    company_analysis: Optional[str] = None
    
    overall_score: Optional[int] = Field(default=None, ge=0, le=100)
    key_strengths: Optional[str] = Field(default=None, description="JSON格式的关键优势列表")
    areas_for_improvement: Optional[str] = Field(default=None, description="JSON格式的改进建议列表")
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now, sa_column_kwargs={"onupdate": datetime.utcnow})


class InterviewReportExportCreate(SQLModel):
    """创建导出请求"""
    company_name: Optional[str] = None
    position: Optional[str] = None
    export_format: str = Field(default="markdown", max_length=20)
    report_title: str = Field(default="面试报告", max_length=200)
    
    meta_info: Optional[dict] = None
    tech_questions: Optional[List[dict]] = None
    hr_questions: Optional[List[dict]] = None
    company_analysis: Optional[str] = None
    
    overall_score: Optional[int] = None
    key_strengths: Optional[List[str]] = None
    areas_for_improvement: Optional[List[str]] = None
    
    team_id: Optional[int] = None


class InterviewReportExportResponse(SQLModel):
    """导出响应"""
    id: int
    user_id: int
    team_id: Optional[int] = None
    company_name: Optional[str]
    position: Optional[str]
    export_format: str
    report_title: str
    created_at: datetime
    
    class Config:
        from_attributes = True
