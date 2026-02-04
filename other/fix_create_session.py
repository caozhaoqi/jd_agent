import sqlite3
import datetime

def create_test_session():
    conn = sqlite3.connect('/Users/caozhaoqi/PycharmProjects/JD_agent/database.db')
    cursor = conn.cursor()
    
    # 为test用户（ID=2）创建一个新会话
    user_id = 2
    now = datetime.datetime.now().isoformat()
    
    # 创建测试会话（使用正确的表结构）
    cursor.execute(
        "INSERT INTO ChatSession (user_id, title, created_at) VALUES (?, ?, ?)",
        (user_id, "测试面试会话", now)
    )
    
    session_id = cursor.lastrowid
    print(f"为用户ID {user_id} 创建会话成功: ID {session_id}")
    
    # 创建一些测试消息（使用role而不是sender）
    messages = [
        (session_id, "user", "请介绍一下你自己"),
        (session_id, "assistant", "我是一名前端开发工程师，有3年工作经验...")
    ]
    
    cursor.executemany(
        "INSERT INTO ChatMessage (session_id, role, content) VALUES (?, ?, ?)",
        messages
    )
    
    print(f"创建了 {len(messages)} 条测试消息")
    
    # 提交并关闭连接
    conn.commit()
    
    # 验证会话是否创建成功
    cursor.execute("SELECT * FROM ChatSession WHERE user_id=? AND id=?", (user_id, session_id))
    session = cursor.fetchone()
    print(f"创建的会话: {session}")
    
    # 验证消息是否创建成功
    cursor.execute("SELECT * FROM ChatMessage WHERE session_id=?", (session_id,))
    msgs = cursor.fetchall()
    for msg in msgs:
        print(f"消息: {msg}")
    
    conn.close()

if __name__ == "__main__":
    create_test_session()