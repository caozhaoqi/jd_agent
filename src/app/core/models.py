from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime
from pydantic import BaseModel

Base = declarative_base()

from typing import List, Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship


class UserProfile(SQLModel, table=True):
    """
    长期记忆表：存储用户的关键画像信息
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    category: str  # 类别，如: "tech_stack", "experience", "preference"
    content: str  # 内容，如: "精通 Python", "5年架构经验", "不接受外包"
    updated_at: datetime = Field(default_factory=datetime.now)

    # 建立与 User 的关联 (需要在 User 类里也加对应的 relationship)
    # user: Optional[User] = Relationship(back_populates="profiles")


# --- 数据库模型 ---
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: Optional[str] = Field(default=None)
    hashed_password: str
    chats: List["ChatSession"] = Relationship(back_populates="user")


class ChatSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    user_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.now)
    user: Optional[User] = Relationship(back_populates="chats")
    messages: List["ChatMessage"] = Relationship(back_populates="session")


class ChatMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="chatsession.id")
    role: str  # "user" or "assistant"
    content: str
    session: Optional[ChatSession] = Relationship(back_populates="messages")


class InterviewRecord(Base):
    """面试记录表"""

    __tablename__ = "interview_records"

    id = Column(Integer, primary_key=True)
    company_name = Column(String(100))
    jd_content = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Record {self.company_name}>"


class ChatRequest(BaseModel):
    session_id: int
    content: str


# ==========================================
# 1. 认证接口 (Auth)
# ==========================================
class AuthRequest(BaseModel):
    username: str
    password: str


# 定义请求体
class BlogQueryRequest(BaseModel):
    question: str


# 定义响应体
class BlogQueryResponse(BaseModel):
    answer: str
    sources: List[str]


# 定义响应模型
class RAGResponse(BaseModel):
    answer: str
    sources: List[str]


# --- 1. 定义请求体模型 (关键修复) ---
class RAGRequest(BaseModel):
    question: str


# 创建TTS请求模型
class TTSRequest(BaseModel):
    text: str = Field(..., description="待转换的文本")


# 定义请求模型
class ResumeJDMatchRequest(BaseModel):
    resume_text: str
    jd_text: str
