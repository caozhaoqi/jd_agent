from sqlmodel import SQLModel, create_engine, Session, select
from .models import User, ChatSession, ChatMessage
from models.interview_report import InterviewReportExport
import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from .config import settings

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
async_sqlite_url = f"sqlite+aiosqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url)
async_engine = create_async_engine(async_sqlite_url)
async_session_maker = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db_dependency() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# 2. 密码加密工具
# 从 settings 对象安全地获取密钥
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"


def verify_password(plain_password, hashed_password):
    # Ensure both are bytes
    if isinstance(plain_password, str):
        plain_password = plain_password.encode("utf-8")
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode("utf-8")
    return bcrypt.checkpw(plain_password, hashed_password)


def get_password_hash(password):
    # bcrypt limits password length to 72 bytes
    if isinstance(password, str):
        password_bytes = password.encode("utf-8")
    else:
        password_bytes = password

    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]

    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)

    # Return as string for storage in database
    return hashed.decode("utf-8")


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=60 * 24)  # 1天过期
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    """
    验证JWT令牌
    - 返回令牌中的用户信息
    - 令牌无效时抛出异常
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("令牌已过期")
    except jwt.InvalidTokenError:
        raise ValueError("无效的令牌")
