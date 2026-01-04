#!/usr/bin/env python3
"""
JD Agent 全接口测试脚本
系统性测试所有API端点的可用性和功能
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any

class APITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
        
        # 设置请求头
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'JD-Agent-APITester/1.0'
        })
    
    def log_test(self, test_name: str, status: str, response_time: float, 
                status_code: int = None, details: str = ""):
        """记录测试结果"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_name": test_name,
            "status": status,
            "response_time": round(response_time, 3),
            "status_code": status_code,
            "details": details
        }
        self.results.append(result)
        
        # 打印结果
        status_symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_symbol} {test_name}: {status} ({response_time:.3f}s)")
        if details:
            print(f"   详情: {details}")
    
    def test_endpoint(self, method: str, endpoint: str, data: Dict = None, 
                     headers: Dict = None, test_name: str = None) -> Dict:
        """测试单个端点"""
        url = f"{self.base_url}{endpoint}"
        if not test_name:
            test_name = f"{method.upper()} {endpoint}"
        
        try:
            start_time = time.time()
            
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, headers=headers, timeout=30)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, headers=headers, timeout=30)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            response_time = time.time() - start_time
            
            # 判断结果
            if response.status_code < 400:
                status = "PASS"
                details = f"状态码: {response.status_code}"
            else:
                status = "FAIL"
                details = f"状态码: {response.status_code}, 错误: {response.text[:200]}"
            
            self.log_test(test_name, status, response_time, response.status_code, details)
            
            return {
                "success": status == "PASS",
                "status_code": response.status_code,
                "response_time": response_time,
                "response_data": response.text[:500] if response.text else "",
                "headers": dict(response.headers)
            }
            
        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            self.log_test(test_name, "ERROR", response_time, details=str(e))
            return {
                "success": False,
                "error": str(e),
                "response_time": response_time
            }
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始JD Agent全接口测试")
        print("=" * 80)
        
        # 1. 基础健康检查
        print("\n📋 1. 基础健康检查测试")
        print("-" * 40)
        
        self.test_endpoint("GET", "/", test_name="根路径检查")
        self.test_endpoint("GET", "/docs", test_name="API文档页面")
        self.test_endpoint("GET", "/openapi.json", test_name="OpenAPI规范")
        self.test_endpoint("GET", "/health", test_name="健康检查端点")
        
        # 2. RAG相关接口
        print("\n📋 2. RAG相关接口测试")
        print("-" * 40)
        
        # 测试知识库查询
        self.test_endpoint("POST", "/api/v1/qa/qa", {
            "question": "什么是机器学习？"
        }, test_name="知识库查询")
        
        # 测试聊天接口（需要用户认证，暂时跳过）
        # self.test_endpoint("POST", "/chat/stream", {
        #     "message": "你好，请介绍一下JD Agent的功能"
        # }, test_name="聊天流式接口")
        
        # 3. 简历相关接口
        print("\n📋 3. 简历相关接口测试")
        print("-" * 40)
        
        # 简历解析（需要文件上传，暂时跳过）
        # self.test_endpoint("POST", "/api/v1/resume/upload", {}, test_name="简历解析")
        
        # 简历匹配（需要文件上传，暂时跳过）
        # self.test_endpoint("POST", "/api/v1/resume/match", {}, test_name="简历匹配")
        
        # 4. 职位描述解析接口
        print("\n📋 4. 职位描述解析接口测试")
        print("-" * 40)
        
        # 职位描述解析
        self.test_endpoint("POST", "/api/v1/jd/generate-guide", {
            "jd_text": "我们需要招聘一位Python开发工程师，负责后端开发工作。",
            "company_name": "测试公司",
            "job_title": "Python开发工程师"
        }, test_name="职位描述解析")
        
        # 职位分析
        self.test_endpoint("POST", "/api/v1/jd/stream/system-design", {
            "jd_text": "我们需要招聘一位Python开发工程师，负责后端开发工作。",
            "question": "系统设计相关问题"
        }, test_name="职位分析")
        
        # 爬取职位信息
        self.test_endpoint("POST", "/api/v1/jd/crawl-jobs", {
            "keywords": "Python开发",
            "max_results": 5
        }, test_name="爬取职位信息")
        
        # 5. 面经相关接口
        print("\n📋 5. 面经相关接口测试")
        print("-" * 40)
        
        # 获取面试题库
        self.test_endpoint("POST", "/api/v1/interview/guide", {
            "jd_text": "我们需要招聘一位Python开发工程师，负责后端开发工作。",
            "company_name": "测试公司",
            "job_title": "Python开发工程师"
        }, test_name="生成面试指南")
        
        # 6. 音频处理接口
        print("\n📋 6. 音频处理接口测试")
        print("-" * 40)
        
        # 音频转文本（需要音频文件上传，暂时跳过）
        # self.test_endpoint("POST", "/api/v1/audio/transcribe", {}, test_name="音频转文本")
        
        # 文本转音频（需要认证，暂时跳过）
        # self.test_endpoint("POST", "/api/v1/audio/tts", {
        #     "text": "你好，这是测试音频"
        # }, test_name="文本转音频")
        
        # 7. Confluence集成接口
        print("\n📋 7. Confluence集成接口测试")
        print("-" * 40)
        
        # Confluence状态
        self.test_endpoint("GET", "/api/v1/confluence/status", test_name="Confluence状态")
        
        # Confluence搜索
        self.test_endpoint("POST", "/api/v1/confluence/query", {
            "query": "技术文档"
        }, test_name="Confluence搜索")
        
        # 8. 监控和统计接口
        print("\n📋 8. 监控和统计接口测试")
        print("-" * 40)
        
        # Prometheus指标
        self.test_endpoint("GET", "/metrics", test_name="Prometheus指标")
        
        # 生成测试报告
        self.generate_report()
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "=" * 80)
        print("📊 接口测试报告")
        print("=" * 80)
        
        # 统计结果
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r["status"] == "PASS"])
        failed_tests = len([r for r in self.results if r["status"] == "FAIL"])
        error_tests = len([r for r in self.results if r["status"] == "ERROR"])
        
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests} ✅")
        print(f"失败: {failed_tests} ❌")
        print(f"错误: {error_tests} ⚠️")
        print(f"成功率: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "0%")
        
        # 响应时间统计
        response_times = [r["response_time"] for r in self.results if r["response_time"] > 0]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            print(f"\n响应时间统计:")
            print(f"平均: {avg_time:.3f}s")
            print(f"最快: {min_time:.3f}s")
            print(f"最慢: {max_time:.3f}s")
        
        # 失败的测试详情
        if failed_tests > 0 or error_tests > 0:
            print(f"\n❌ 失败的测试详情:")
            for result in self.results:
                if result["status"] in ["FAIL", "ERROR"]:
                    print(f"  - {result['test_name']}: {result['details']}")
        
        print(f"\n测试完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 保存详细报告到文件
        with open(f"api_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        print(f"详细报告已保存到文件")

def main():
    """主函数"""
    tester = APITester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()