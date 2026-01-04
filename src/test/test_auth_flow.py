#!/usr/bin/env python3
"""
JD Agent 认证流程测试脚本
测试注册、登录和认证状态验证
"""

import requests
import json
import time
from datetime import datetime

class AuthFlowTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        
    def log_result(self, test_name, success, status_code=None, message="", data=None):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "success": success,
            "status_code": status_code,
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status_emoji = "✅" if success else "❌"
        print(f"{status_emoji} {test_name}: {message}")
        if status_code:
            print(f"   状态码: {status_code}")
        if data and not success:
            print(f"   响应数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
        print()
        
    def test_register(self, username="testuser001", password="testpass123"):
        """测试用户注册"""
        print("🔐 测试用户注册...")
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/register",
                json={"username": username, "password": password},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                self.log_result("用户注册", True, 200, "注册成功", result)
                return True
            else:
                self.log_result("用户注册", False, response.status_code, "注册失败", response.json())
                return False
                
        except Exception as e:
            self.log_result("用户注册", False, None, f"请求异常: {str(e)}")
            return False
    
    def test_login(self, username="testuser001", password="testpass123"):
        """测试用户登录"""
        print("🔑 测试用户登录...")
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"username": username, "password": password},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                token = result.get("data", {}).get("access_token")
                
                if token:
                    # 设置后续请求的认证头
                    self.session.headers.update({
                        "Authorization": f"Bearer {token}"
                    })
                    self.log_result("用户登录", True, 200, "登录成功，获取到token", {"token_length": len(token)})
                    return token
                else:
                    self.log_result("用户登录", False, 200, "登录响应中未找到token", result)
                    return None
            else:
                self.log_result("用户登录", False, response.status_code, "登录失败", response.json())
                return None
                
        except Exception as e:
            self.log_result("用户登录", False, None, f"请求异常: {str(e)}")
            return None
    
    def test_protected_endpoint(self):
        """测试需要认证的端点"""
        print("🛡️ 测试受保护端点...")
        
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/chat/history/sessions",
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                self.log_result("受保护端点访问", True, 200, "成功访问受保护资源", {"data_type": type(result).__name__})
                return True
            elif response.status_code == 401:
                self.log_result("受保护端点访问", False, 401, "认证失败，需要重新登录")
                return False
            else:
                self.log_result("受保护端点访问", False, response.status_code, "访问失败", response.json())
                return False
                
        except Exception as e:
            self.log_result("受保护端点访问", False, None, f"请求异常: {str(e)}")
            return False
    
    def test_session_persistence(self):
        """测试会话持久性"""
        print("💾 测试会话持久性...")
        
        # 创建新的session来模拟浏览器重新打开
        new_session = requests.Session()
        new_session.headers.update(self.session.headers)
        
        try:
            response = new_session.get(
                f"{self.base_url}/api/v1/chat/history/sessions",
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                self.log_result("会话持久性", True, 200, "Token在会话间保持有效")
                return True
            else:
                self.log_result("会话持久性", False, response.status_code, "Token在会话间失效")
                return False
                
        except Exception as e:
            self.log_result("会话持久性", False, None, f"请求异常: {str(e)}")
            return False
    
    def run_full_flow(self):
        """运行完整的认证流程测试"""
        print("🚀 开始JD Agent认证流程测试")
        print("=" * 60)
        
        # 1. 测试注册
        register_success = self.test_register()
        
        # 2. 测试登录
        token = self.test_login()
        
        # 3. 测试受保护端点
        if token:
            protected_success = self.test_protected_endpoint()
            
            # 4. 测试会话持久性
            persistence_success = self.test_session_persistence()
        else:
            protected_success = False
            persistence_success = False
        
        # 生成报告
        self.generate_report()
        
        return {
            "register": register_success,
            "login": token is not None,
            "protected": protected_success,
            "persistence": persistence_success
        }
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "=" * 60)
        print("📊 认证流程测试报告")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - passed_tests
        
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests} ✅")
        print(f"失败: {failed_tests} ❌")
        print(f"成功率: {(passed_tests/total_tests*100):.1f}%")
        
        # 详细的测试结果
        print(f"\n📋 详细测试结果:")
        for result in self.test_results:
            status_emoji = "✅" if result["success"] else "❌"
            print(f"{status_emoji} {result['test_name']}: {result['message']}")
            if result['status_code']:
                print(f"   状态码: {result['status_code']}")
        
        # 如果有失败的测试，提供诊断建议
        if failed_tests > 0:
            print(f"\n🔍 诊断建议:")
            failed_tests_list = [r for r in self.test_results if not r["success"]]
            
            for failed in failed_tests_list:
                test_name = failed["test_name"]
                if test_name == "用户注册":
                    print("   - 检查用户名是否已存在，或服务器是否正常")
                elif test_name == "用户登录":
                    print("   - 检查用户名密码是否正确，或用户是否已注册")
                elif test_name == "受保护端点访问":
                    print("   - 检查token是否正确设置，或是否已过期")
                elif test_name == "会话持久性":
                    print("   - 检查token存储方式，或浏览器设置")
        
        print(f"\n测试完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def main():
    """主函数"""
    print("JD Agent 认证流程测试工具")
    print("请确保服务器正在运行在 http://localhost:8000")
    print()
    
    # 检查服务器是否可访问
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ 服务器连接正常")
        else:
            print("❌ 服务器响应异常")
            return
    except Exception as e:
        print(f"❌ 无法连接到服务器: {e}")
        print("请确保服务器正在运行: python src/app/main.py")
        return
    
    # 运行测试
    tester = AuthFlowTester()
    results = tester.run_full_flow()
    
    print(f"\n🎯 总体结果:")
    if all(results.values()):
        print("✅ 所有测试通过！认证系统工作正常")
        print("如果前端仍有问题，可能是前端状态管理或路由问题")
    else:
        print("❌ 部分测试失败，需要检查服务器配置")

if __name__ == "__main__":
    main()