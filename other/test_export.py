import requests
import json

# 登录获取token
login_url = "http://localhost:8000/api/v1/auth/login"
login_data = {
    "username": "test",
    "password": "test"
}

response = requests.post(login_url, json=login_data)
if response.status_code == 200:
    token = response.json()["data"]["access_token"]
    print(f"登录成功，获取到token: {token}")
    
    # 测试导出功能
    export_url = "http://localhost:8000/api/v1/report-export/export"
    export_data = {
        "session_id": 1,
        "export_format": "markdown",
        "report_title": "测试面试报告"
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    export_response = requests.post(export_url, json=export_data, headers=headers)
    if export_response.status_code == 200:
        print("导出成功!")
        print(f"导出内容: {export_response.text[:200]}...")
    else:
        print(f"导出失败，状态码: {export_response.status_code}")
        print(f"错误信息: {export_response.text}")
else:
    print(f"登录失败，状态码: {response.status_code}")
    print(f"错误信息: {response.text}")
