import sqlite3
import datetime
import jwt

def get_user_id_from_token(token):
    try:
        # 获取token中的username，不需要验证密钥
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload.get("sub")
    except Exception as e:
        print(f"解析token失败: {e}")
        return None

def create_test_session():
    conn = sqlite3.connect('/Users/caozhaoqi/PycharmProjects/JD_agent/database.db')
    cursor = conn.cursor()
    
    # 先获取testuser123的用户ID
    cursor.execute("SELECT id FROM User WHERE username='testuser123'")
    user = cursor.fetchone()
    
    if user:
        user_id = user[0]
        print(f"找到用户: testuser123, ID: {user_id}")
        
        # 创建测试会话
        now = datetime.datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO ChatSession (user_id, title, job_position, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, "测试会话", "软件工程师", now, now)
        )
        
        session_id = cursor.lastrowid
        print(f"创建会话成功: ID {session_id}")
        
        # 提交并关闭连接
        conn.commit()
        
        # 测试获取会话列表
        cursor.execute("SELECT * FROM ChatSession WHERE user_id=?", (user_id,))
        sessions = cursor.fetchall()
        print(f"用户 {user_id} 的会话数量: {len(sessions)}")
    else:
        print("未找到用户 testuser123")
    
    conn.close()

if __name__ == "__main__":
    create_test_session()