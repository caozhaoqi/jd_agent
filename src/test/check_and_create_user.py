#!/usr/bin/env python3
"""
在src目录下检查数据库表结构并创建测试用户
"""

import sqlite3
import sys
import os

# 使用正确的数据库文件路径
db_path = os.path.join(os.getcwd(), "database.db")
print(f"数据库文件路径: {db_path}")

# 连接到数据库
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. 检查user表结构
print("\n1. 检查user表结构:")
cursor.execute("PRAGMA table_info(user)")
columns = cursor.fetchall()
for col in columns:
    print(f"  - {col[1]}: {col[2]}")

# 2. 创建测试用户
print("\n2. 创建测试用户:")

# 首先检查是否已存在
cursor.execute("SELECT * FROM user WHERE username = 'test_user'")
existing = cursor.fetchone()

if existing:
    print("  测试用户已存在")
else:
    # 生成密码哈希 (简单版本用于测试)
    import bcrypt

    password = "test_password"
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    hashed_str = hashed.decode("utf-8")

    # 创建用户
    cursor.execute(
        "INSERT INTO user (username, email, hashed_password) VALUES (?, ?, ?)",
        ("test_user", "test@example.com", hashed_str),
    )

    # 检查插入结果
    cursor.execute("SELECT * FROM user WHERE username = 'test_user'")
    new_user = cursor.fetchone()
    if new_user:
        print(f"  测试用户创建成功: ID={new_user[0]}")
    else:
        print("  测试用户创建失败")

# 3. 生成JWT令牌
print("\n3. 生成JWT令牌:")
from app.core.db_auth import create_access_token

token = create_access_token({"sub": "test_user"})
print(f"  JWT令牌: {token}")

# 4. 测试认证查询
print("\n4. 测试认证查询:")
cursor.execute(
    "SELECT id, username, email, hashed_password FROM user WHERE username = 'test_user'"
)
user = cursor.fetchone()
if user:
    print(f"  查询成功: {user}")
else:
    print("  查询失败")

conn.commit()
conn.close()

print("\n操作完成！")
