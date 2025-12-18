import sys
import os
import sqlite3

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(".."))

from app.core.db_auth import engine

# 直接使用SQLite命令修复数据库
print("正在检查数据库...")

# 连接到SQLite数据库
conn = sqlite3.connect(
    ":memory:" if "sqlite:///:memory:" in str(engine.url) else "sqlite.db"
)
cursor = conn.cursor()

# 检查user表结构
print("检查user表结构...")
cursor.execute("PRAGMA table_info(user)")
columns = cursor.fetchall()
print("当前表结构:")
for col in columns:
    print(col)

# 直接删除并重新创建user表
print("正在重新创建user表...")
cursor.execute("DROP TABLE IF EXISTS user")
cursor.execute(
    """
CREATE TABLE user (
    id INTEGER PRIMARY KEY,
    username VARCHAR NOT NULL UNIQUE,
    email VARCHAR,
    hashed_password VARCHAR NOT NULL
)
"""
)

# 检查其他相关表
print("检查其他表...")
tables = ["chatsession", "chatmessage", "userprofile"]
for table in tables:
    cursor.execute(f"DROP TABLE IF EXISTS {table}")

# 创建chatsession表
cursor.execute(
    """
CREATE TABLE chatsession (
    id INTEGER PRIMARY KEY,
    title VARCHAR NOT NULL,
    user_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user (id)
)
"""
)

# 创建chatmessage表
cursor.execute(
    """
CREATE TABLE chatmessage (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL,
    role VARCHAR NOT NULL,
    content TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES chatsession (id)
)
"""
)

# 创建userprofile表
cursor.execute(
    """
CREATE TABLE userprofile (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    category VARCHAR NOT NULL,
    content TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user (id)
)
"""
)

conn.commit()
conn.close()

print("数据库表修复完成")

# 现在重新创建测试用户
from sqlmodel import Session
from app.core.db_auth import get_password_hash, create_access_token
from app.core.models import User

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
