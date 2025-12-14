# 创建测试用户并生成JWT令牌
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(".."))

from sqlmodel import Session
from app.core.db_auth import get_session, get_password_hash, create_access_token, engine
from app.core.models import User, SQLModel

# 创建数据库表
SQLModel.metadata.create_all(engine)

# 创建测试用户
from sqlmodel import select

with Session(engine) as session:
    # 检查用户是否已存在
    existing_user = session.exec(select(User).where(User.username == "test_user")).first()
    if existing_user:
        print("测试用户已存在")
        user = existing_user
    else:
        # 创建新用户
        hashed_password = get_password_hash("test_password")
        user = User(
            username="test_user",
            email="test@example.com",
            hashed_password=hashed_password
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        print("测试用户创建成功")

    # 生成JWT令牌
    token = create_access_token(data={"sub": user.username})
    print(f"测试用户ID: {user.id}")
    print(f"JWT令牌: {token}")
