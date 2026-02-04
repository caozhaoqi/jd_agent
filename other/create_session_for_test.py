import sqlite3
import datetime

def create_test_session_for_existing_user():
    conn = sqlite3.connect('/Users/caozhaoqi/PycharmProjects/JD_agent/database.db')
    cursor = conn.cursor()
    
    # 为test用户（ID=2）创建一个新会话
    user_id = 2
    now = datetime.datetime.now().isoformat()
    
    # 创建测试会话
    cursor.execute(
        "INSERT INTO ChatSession (user_id, title, job_position, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, "测试面试会话", "前端开发工程师", now, now)
    )
    
    session_id = cursor.lastrowid
    print(f"为用户ID {user_id} 创建会话成功: ID {session_id}")
    
    # 创建一些测试消息
    messages = [
        (session_id, "user", "请介绍一下你自己", now),
        (session_id, "assistant", "我是一名前端开发工程师，有3年工作经验...", now)
    ]
    
    cursor.executemany(
        "INSERT INTO ChatMessage (session_id, sender, content, created_at) VALUES (?, ?, ?, ?)",
        messages
    )
    
    print(f"创建了 {len(messages)} 条测试消息")
    
    # 提交并关闭连接
    conn.commit()
    
    # 验证会话是否创建成功
    cursor.execute("SELECT * FROM ChatSession WHERE user_id=? AND id=?", (user_id, session_id))
    session = cursor.fetchone()
    print(f"创建的会话: {session}")
    
    conn.close()

if __name__ == "__main__":
    create_test_session_for_existing_user()