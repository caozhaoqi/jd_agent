from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional, List

class ExperienceReportBase(SQLModel):
    session_id: str = Field(index=True)
    user_id: str = Field(index=True)
    title: str
    company_name: Optional[str] = None
    position_name: Optional[str] = None
    overall_score: int = Field(ge=1, le=100)
    key_strengths: List[str] = Field(default_factory=list)
    areas_for_improvement: List[str] = Field(default_factory=list)
    detailed_feedback: str
    interview_summary: str
    recommended_actions: List[str] = Field(default_factory=list)

class ExperienceReport(ExperienceReportBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})

class ExperienceReportCreate(ExperienceReportBase):
    pass

class ExperienceReportRead(ExperienceReportBase):
    id: int
    created_at: datetime
    updated_at: datetime

class ExperienceReportUpdate(SQLModel):
    title: Optional[str] = None
    overall_score: Optional[int] = Field(default=None, ge=1, le=100)
    key_strengths: Optional[List[str]] = None
    areas_for_improvement: Optional[List[str]] = None
    detailed_feedback: Optional[str] = None
    interview_summary: Optional[str] = None
    recommended_actions: Optional[List[str]] = None
