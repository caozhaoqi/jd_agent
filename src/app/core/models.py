from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

from typing import List, Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship

# --- 数据库模型 ---
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
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
    role: str # "user" or "assistant"
    content: str
    session: Optional[ChatSession] = Relationship(back_populates="messages")

class InterviewRecord(Base):
    """面试记录表"""
    __tablename__ = 'interview_records'

    id = Column(Integer, primary_key=True)
    company_name = Column(String(100))
    jd_content = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Record {self.company_name}>"