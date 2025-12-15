import requests
import json
import time

# 测试用户信息
username = "test_user"
password = "test_password"

# 测试JD内容
jd_text = """
28Nov.2025
神州邦邦正在招聘
python开发工程师<短期项目半年+>
天津/15-17K/5-10年/本科
职位详情
技术能力要求-、Python语言精通Python语法、数据结构、多线程/多进程编程，熟悉内存管理与性能调优。熟练使用Python常用库(如requests、pandas、numpy、logging等)Flask框架
具备Flask全栈开发经验，熟悉其路由设计、中间件开发、模板渲染、请求/响应处理机制。掌握Flask扩展库(如Flask-RESTful、Flask-SQLAlchemy、Flask-Migrate、Flask-Login等)的集成与应用。熟悉WSGI服务器(如Gunicorn、uWSGl)部署，具备生产环境优化能力。
"""

# 创建请求头
headers = {
    "Content-Type": "application/json"
}

# 登录获取令牌
session = requests.Session()
login_data = {
    "username": username,
    "password": password
}

login_response = session.post(
    "http://localhost:8000/api/v1/auth/login",
    headers=headers,
    data=json.dumps(login_data)
)

print(f"登录响应: {login_response.text}")
login_result = login_response.json()
if login_result.get("status") != "success":
    print("登录失败")
    exit(1)

token = login_result["data"]["access_token"]
headers["Authorization"] = f"Bearer {token}"

# 创建请求数据
data = {
    "jd_text": jd_text
}

# 发送请求
response = session.post(
    "http://localhost:8000/api/v1/jd/generate-guide",
    headers=headers,
    data=json.dumps(data),
    stream=True
)

# 处理SSE响应
print("开始接收SSE响应...")
try:
    for line in response.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            print(f"收到: {decoded_line}")
            # 如果收到结束信号，退出循环
            if "[DONE]" in decoded_line:
                print("收到结束信号，停止接收")
                break
except KeyboardInterrupt:
    print("用户中断接收")
finally:
    response.close()
    session.close()
