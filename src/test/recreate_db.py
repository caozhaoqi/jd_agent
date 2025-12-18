import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(".."))

from sqlmodel import Session
from app.core.db_auth import get_session, get_password_hash, create_access_token, engine
from app.core.models import User, SQLModel, ChatSession, ChatMessage, UserProfile

# 重新创建数据库表
print("正在重新创建数据库表...")
SQLModel.metadata.drop_all(engine)
SQLModel.metadata.create_all(engine)
print("数据库表创建成功")

# 重新创建测试用户
print("正在创建测试用户...")
with Session(engine) as session:
    hashed_password = get_password_hash("test_password")
    user = User(
        username="test_user", email="test@example.com", hashed_password=hashed_password
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    print(f"测试用户创建成功: ID={user.id}, 用户名={user.username}, 邮箱={user.email}")

    # 生成JWT令牌
    token = create_access_token(data={"sub": user.username})
    print(f"JWT令牌: {token}")
