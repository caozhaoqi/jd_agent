from sqlmodel import SQLModel, create_engine, Session, select
from app.core.models import User, ChatSession, ChatMessage
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta

# 1. 数据库设置 (使用 SQLite)
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

# 2. 密码加密工具
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "your-secret-key-change-it" # 生产环境请放 .env
ALGORITHM = "HS256"

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=60*24) # 1天过期
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)