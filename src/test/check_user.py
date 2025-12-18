import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(".."))

from sqlmodel import Session, select
from app.core.db_auth import engine
from app.core.models import User

with Session(engine) as session:
    # 查询所有用户
    users = session.exec(select(User)).all()
    print(f"数据库中用户数量: {len(users)}")
    for user in users:
        print(
            f"用户ID: {user.id}, 用户名: {user.username}, 邮箱: {user.email}, 密码字段: {hasattr(user, 'hashed_password')}"
        )
        if hasattr(user, "hashed_password"):
            print(f"密码长度: {len(user.hashed_password)}")
        else:
            print("缺少hashed_password字段")
