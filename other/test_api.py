import requests
import json

# 测试登录获取token
def test_login():
    login_url = 'http://localhost:8000/api/v1/auth/login'
    login_data = {
        "username": "czq",
        "password": "123456"
    }
    
    try:
        response = requests.post(login_url, json=login_data)
        print(f"Login response: {response.status_code}")
        print(f"Login data: {response.json()}")
        return response.json().get('data', {}).get('access_token')
    except Exception as e:
        print(f"Login error: {e}")
        return None

# 测试获取会话列表
def test_get_sessions(token=None):
    sessions_url = 'http://localhost:8000/api/v1/report-export/sessions'
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    try:
        response = requests.get(sessions_url, headers=headers)
        print(f"Sessions response: {response.status_code}")
        print(f"Sessions data: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.json()
    except Exception as e:
        print(f"Sessions error: {e}")
        return None

if __name__ == "__main__":
    print("Testing API...")
    token = test_login()
    print(f"Token: {token}")
    if token:
        test_get_sessions(token)
    else:
        # 尝试不使用token访问（看是否有公开访问）
        print("\nTrying without token...")
        test_get_sessions()