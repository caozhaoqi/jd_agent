import sys
import os
import sqlite3

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(".."))

# 连接到数据库
conn = sqlite3.connect("../../sqlite.db")
cursor = conn.cursor()

# 查看当前user表结构
print("查看当前user表结构:")
cursor.execute("PRAGMA table_info(user)")
columns = cursor.fetchall()
for col in columns:
    print(col)

# 检查是否有email字段
has_email = any(col[1] == 'email' for col in columns)

if not has_email:
    print("\nemail字段缺失，正在添加...")
    try:
        cursor.execute("ALTER TABLE user ADD COLUMN email VARCHAR")
        print("email字段添加成功")
    except sqlite3.Error as e:
        print(f"添加email字段失败: {e}")
else:
    print("\nemail字段已经存在")

# 再次查看表结构
print("\n更新后的表结构:")
cursor.execute("PRAGMA table_info(user)")
columns = cursor.fetchall()
for col in columns:
    print(col)

# 查看所有用户记录
print("\n所有用户记录:")
cursor.execute("SELECT * FROM user")
users = cursor.fetchall()
for user in users:
    print(user)

conn.commit()
conn.close()

print("\n数据库修复完成")