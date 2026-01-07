from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime
from pydantic import BaseModel

Base = declarative_base()

from typing import List, Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship


from typing import List, Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship, Enum
import enum


class TeamRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class InvitationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Team(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    owner_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    members: List["TeamMember"] = Relationship(back_populates="team")
    invitations: List["TeamInvitation"] = Relationship(back_populates="team")
    interviews: List["TeamInterview"] = Relationship(back_populates="team")


class TeamMember(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="team.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    role: TeamRole = TeamRole.MEMBER
    joined_at: datetime = Field(default_factory=datetime.now)
    team: Optional[Team] = Relationship(back_populates="members")


class TeamInvitation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="team.id", index=True)
    code: str = Field(unique=True, index=True)
    email: Optional[str] = Field(default=None)
    role: TeamRole = TeamRole.MEMBER
    status: InvitationStatus = InvitationStatus.PENDING
    invited_by: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime
    team: Optional[Team] = Relationship(back_populates="invitations")


class TeamInterview(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="team.id", index=True)
    title: str
    candidate_name: Optional[str] = None
    position: Optional[str] = None
    status: str = "pending"
    created_by: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    team: Optional[Team] = Relationship(back_populates="interviews")


class UserProfile(SQLModel, table=True):
    """
    长期记忆表：存储用户的关键画像信息
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    category: str
    content: str
    updated_at: datetime = Field(default_factory=datetime.now)


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
