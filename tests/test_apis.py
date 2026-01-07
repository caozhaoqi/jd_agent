#!/usr/bin/env python3
"""
API 测试脚本
测试所有后端 API 端点
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Optional

BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"
API_V2 = f"{BASE_URL}/api/v2"


class APITester:
    def __init__(self):
        self.token: Optional[str] = None
        self.user_id: Optional[int] = None
        self.team_id: Optional[int] = None
        self.invitation_code: Optional[str] = None
        self.member_id: Optional[int] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.test_results = []

    def log(self, test_name: str, success: bool, message: str = ""):
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} | {test_name}: {message}")
        self.test_results.append({
            "test": test_name,
            "status": "PASS" if success else "FAIL",
            "message": message
        })

    async def init_session(self):
        self.session = aiohttp.ClientSession(
            headers={"Content-Type": "application/json"}
        )

    async def close_session(self):
        if self.session:
            await self.session.close()

    async def auth_header(self) -> dict:
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    async def request(
        self, method: str, endpoint: str, data: dict = None, use_auth: bool = True,
        is_json: bool = True, files: dict = None
    ) -> tuple:
        url = f"{API_V1}{endpoint}"
        headers = await self.auth_header() if use_auth else {}
        if self.session is None:
            await self.init_session()

        try:
            if method.upper() == "GET":
                async with self.session.get(url, headers=headers) as resp:
                    return resp.status, await resp.json()
            elif method.upper() == "POST":
                if files:
                    form_data = aiohttp.FormData()
                    for key, value in files.items():
                        form_data.add_field(key, value)
                    async with self.session.post(url, data=form_data, headers=headers) as resp:
                        return resp.status, await resp.json()
                elif is_json:
                    async with self.session.post(url, json=data, headers=headers) as resp:
                        return resp.status, await resp.json()
                else:
                    async with self.session.post(url, data=data, headers=headers) as resp:
                        return resp.status, await resp.json()
            elif method.upper() == "PUT":
                async with self.session.put(url, json=data, headers=headers) as resp:
                    return resp.status, await resp.json()
            elif method.upper() == "DELETE":
                async with self.session.delete(url, headers=headers) as resp:
                    return resp.status, await resp.json()
        except Exception as e:
            return -1, {"error": str(e)}
        return -1, {"error": "Unknown error"}

    async def request_v2(
        self, method: str, endpoint: str, data: dict = None, use_auth: bool = True,
        is_json: bool = True, files: dict = None
    ) -> tuple:
        url = f"{API_V2}{endpoint}"
        headers = await self.auth_header() if use_auth else {}
        if self.session is None:
            await self.init_session()

        try:
            if method.upper() == "GET":
                async with self.session.get(url, headers=headers) as resp:
                    return resp.status, await resp.json()
            elif method.upper() == "POST":
                if files:
                    form_data = aiohttp.FormData()
                    for key, value in files.items():
                        form_data.add_field(key, value)
                    async with self.session.post(url, data=form_data, headers=headers) as resp:
                        return resp.status, await resp.json()
                elif is_json:
                    async with self.session.post(url, json=data, headers=headers) as resp:
                        return resp.status, await resp.json()
                else:
                    async with self.session.post(url, data=data, headers=headers) as resp:
                        return resp.status, await resp.json()
            elif method.upper() == "PUT":
                async with self.session.put(url, json=data, headers=headers) as resp:
                    return resp.status, await resp.json()
            elif method.upper() == "DELETE":
                async with self.session.delete(url, headers=headers) as resp:
                    return resp.status, await resp.json()
        except Exception as e:
            return -1, {"error": str(e)}
        return -1, {"error": "Unknown error"}

    async def request_stream(
        self, method: str, endpoint: str, data: dict = None, use_auth: bool = True,
        timeout: int = 30
    ) -> tuple:
        """处理流式响应 (SSE)"""
        url = f"{API_V1}{endpoint}"
        headers = await self.auth_header() if use_auth else {}
        if self.session is None:
            await self.init_session()

        try:
            async with self.session.post(url, json=data, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status != 200:
                    return resp.status, {"error": f"HTTP {resp.status}"}
                
                chunk_count = 0
                async for line in resp.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        chunk_count += 1
                        if line == 'data: [DONE]':
                            break
                    if chunk_count >= 5:
                        break
                return 200, {"status": "streaming_ok", "chunks_received": chunk_count}
        except asyncio.TimeoutError:
            return -1, {"error": "Request timeout"}
        except Exception as e:
            return -1, {"error": str(e)}

    async def test_health_check(self):
        print("\n" + "=" * 60)
        print("1. 健康检查测试")
        print("=" * 60)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{BASE_URL}/health") as resp:
                    status = resp.status
                    data = await resp.json()
                    self.log("GET /health", status == 200, f"Status: {status}")
        except Exception as e:
            self.log("GET /health", False, str(e))

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{BASE_URL}/docs") as resp:
                    status = resp.status
                    self.log("GET /docs (Swagger UI)", status == 200, f"Status: {status}")
        except Exception as e:
            self.log("GET /docs", False, str(e))

    async def test_auth_apis(self):
        print("\n" + "=" * 60)
        print("2. 认证相关 API 测试")
        print("=" * 60)

        test_username = f"testuser_{datetime.now().strftime('%H%M%S')}"
        test_password = "testpassword123"

        status, data = await self.request(
            "POST", "/auth/register", {"username": test_username, "password": test_password}, use_auth=False
        )
        self.log(
            "POST /auth/register",
            status == 200,
            f"Status: {status}"
        )

        status, data = await self.request(
            "POST", "/auth/login", {"username": test_username, "password": test_password}, use_auth=False
        )
        if status == 200 and data.get("data", {}).get("access_token"):
            self.token = data["data"]["access_token"]
            self.log("POST /auth/login", True, "获取到令牌")
        else:
            self.log("POST /auth/login", False, f"Status: {status}")

        if self.token:
            status, data = await self.request("GET", "/auth/me", use_auth=True)
            if status == 200:
                self.user_id = data.get("id")
                self.log("GET /auth/me (获取当前用户)", True, f"用户: {data.get('username')}")
            else:
                self.log("GET /auth/me", False, f"Status: {status}, Data: {str(data)[:100]}")

    async def test_team_apis(self):
        print("\n" + "=" * 60)
        print("3. 团队管理 API 测试")
        print("=" * 60)

        status, data = await self.request("GET", "/teams", use_auth=True)
        self.log("GET /teams (列出团队)", status == 200, f"Status: {status}")
        if status == 200 and data.get("data"):
            print(f"   现有团队数量: {len(data['data'])}")

        status, data = await self.request(
            "POST", "/teams", {"name": "测试团队", "description": "API测试创建的团队"}, use_auth=True
        )
        if status == 200 and data.get("code") == 0 and data.get("data"):
            self.team_id = data["data"]["id"]
            self.log("POST /teams (创建团队)", True, f"团队ID: {self.team_id}")
        else:
            self.log("POST /teams", False, f"Status: {status}")
            if self.team_id is None and data.get("data"):
                teams = data.get("data", [])
                if teams:
                    self.team_id = teams[0].get("id")
                    print(f"   使用现有团队ID: {self.team_id}")

        if self.team_id:
            status, data = await self.request("GET", f"/teams/{self.team_id}", use_auth=True)
            self.log(f"GET /teams/{{team_id}} (获取团队详情)", status == 200, f"Status: {status}")

            status, data = await self.request(
                "PUT", f"/teams/{self.team_id}", {"name": "测试团队-更新"}, use_auth=True
            )
            self.log(f"PUT /teams/{{team_id}} (更新团队)", status == 200, f"Status: {status}")

            status, data = await self.request(
                "POST", f"/teams/invitations/create",
                {"team_id": self.team_id, "role": "member"}, use_auth=True
            )
            if status == 200 and data.get("code") == 0 and data.get("data"):
                self.invitation_code = data.get("data", {}).get("code")
                self.log("POST /teams/invitations/create (生成邀请码)", True, f"邀请码: {str(self.invitation_code)[:20]}...")
            else:
                self.log("POST /teams/invitations/create", False, f"Status: {status}, Data: {str(data)[:100]}")

            status, data = await self.request(
                "POST", f"/teams/{self.team_id}/invitations",
                {"email": "test@example.com", "role": "member"}, use_auth=True
            )
            self.log(f"POST /teams/{{team_id}}/invitations (邮件邀请)", status in [200, 201], f"Status: {status}")

            status, data = await self.request(
                "GET", f"/teams/{self.team_id}/invitations", use_auth=True
            )
            self.log(f"GET /teams/{{team_id}}/invitations (列出邀请)", status == 200, f"Status: {status}")

        status, data = await self.request("GET", "/teams", use_auth=True)
        if status == 200 and data.get("data"):
            teams = data.get("data", [])
            if teams:
                first_team = teams[0]
                self.team_id = first_team.get("id")
                members = first_team.get("members", [])
                if members:
                    self.member_id = members[0].get("id")

    async def test_join_team_api(self):
        print("\n" + "=" * 60)
        print("4. 加入团队 API 测试")
        print("=" * 60)

        if self.invitation_code:
            status, data = await self.request(
                "POST", "/teams/join", {"invitation_code": self.invitation_code}, use_auth=True
            )
            self.log("POST /teams/join (使用邀请码加入)", status == 200, f"Status: {status}")
            if status == 200 and data.get("code") == 0:
                joined_team_id = data.get("data", {}).get("id")
                if joined_team_id and self.member_id:
                    status, data = await self.request(
                        "DELETE", f"/teams/{joined_team_id}/members/{self.member_id}", use_auth=True
                    )
                    self.log(f"DELETE /teams/{{team_id}}/members/{{member_id}}", status == 200, f"Status: {status}")

    async def test_chat_apis(self):
        print("\n" + "=" * 60)
        print("5. 聊天相关 API 测试")
        print("=" * 60)

        status, data = await self.request("GET", "/chat/history/sessions", use_auth=True)
        self.log("GET /chat/history/sessions (获取会话列表)", status == 200, f"Status: {status}")
        if status == 200:
            sessions = data if isinstance(data, list) else data.get("data", data)
            print(f"   会话数量: {len(sessions)}")

    async def test_other_apis(self):
        print("\n" + "=" * 60)
        print("6. 其他 API 测试")
        print("=" * 60)

        files = {'file': ('test.txt', 'Test resume content', 'text/plain')}
        status, data = await self.request("POST", "/resume/upload", files=files, use_auth=True)
        self.log("POST /resume/upload (简历上传)", status == 200, f"Status: {status}")

        status, data = await self.request_stream("POST", "/jd/generate-guide", {"jd_text": "Python高级开发工程师\n\n岗位职责：\n1. 负责核心业务系统的设计与开发\n2. 优化系统性能，提升用户体验\n3. 指导初级工程师的技术成长\n\n任职要求：\n1. 5年以上Python开发经验\n2. 熟悉Django或FastFrame框架\n3. 熟练使用MySQL和Redis\n4. 具备良好的代码规范和文档能力"}, use_auth=True)
        self.log("POST /jd/generate-guide (JD生成指南)", status == 200, f"Status: {status}, {data}")

        status, data = await self.request("POST", "/jd/crawl-jobs", {"keywords": "Python开发工程师", "max_results": 5}, use_auth=True)
        self.log("POST /jd/crawl-jobs (爬取职位)", status == 200, f"Status: {status}")

        status, data = await self.request("GET", "/logs/list", use_auth=True)
        self.log("GET /logs/list (日志列表)", status == 200, f"Status: {status}")

        status, data = await self.request_stream("POST", "/qa/qa", {"question": "test question"}, use_auth=True)
        self.log("POST /qa/qa (RAG问答)", status == 200, f"Status: {status}")

        status, data = await self.request("GET", "/webrtc/token", use_auth=True)
        self.log("GET /webrtc/token (WebRTC令牌)", status == 200, f"Status: {status}")

        # 使用更简单的测试数据测试面试指南
        status, data = await self.request_stream("POST", "/interview/guide", {
            "jd_text": "Python开发工程师\n\n职责：\n1. 负责Python后端开发\n2. 使用Django或FastFrame框架\n3. 编写高质量代码"
        }, use_auth=True)
        self.log("POST /interview/guide (面试指南)", status == 200, f"Status: {status}")

        status, data = await self.request("POST", "/audio/transcribe", files={'file': ('test.wav', b'test audio content', 'audio/wav')}, use_auth=True)
        self.log("POST /audio/transcribe (音频转写)", status == 200, f"Status: {status}")

        status, data = await self.request("POST", "/audio/tts", {"text": "你好，世界！"}, use_auth=True)
        self.log("POST /audio/tts (文字转语音)", status == 200, f"Status: {status}")

        status, data = await self.request("POST", "/confluence/query", {"query": "test"}, use_auth=True)
        self.log("POST /confluence/query (Confluence查询)", status == 200, f"Status: {status}")

        status, data = await self.request("GET", "/confluence/status", use_auth=True)
        self.log("GET /confluence/status (Confluence状态)", status == 200, f"Status: {status}")

        status, data = await self.request("POST", "/blog/chat", {"question": "技术面试通常会问哪些问题？"}, use_auth=True)
        self.log("POST /blog/chat (博客查询)", status == 200, f"Status: {status}")

        status, data = await self.request("GET", "/interview-style/styles/presets", use_auth=True)
        self.log("GET /interview-style/styles/presets (面试风格预设)", status == 200, f"Status: {status}")

        status, data = await self.request("GET", "/report-export/sessions", use_auth=True)
        self.log("GET /report-export/sessions (报告导出会话)", status == 200, f"Status: {status}")

        status, data = await self.request("GET", "/knowledge-graph/graph/stats", use_auth=True)
        self.log("GET /knowledge-graph/graph/stats (知识图谱统计)", status == 200, f"Status: {status}")

    async def test_api_v2(self):
        print("\n" + "=" * 60)
        print("8. API v2 测试")
        print("=" * 60)

        status, data = await self.request_v2("POST", "/auth/register", {"username": "test_v2", "password": "test123"}, use_auth=False)
        self.log("POST /v2/auth/register", status == 200, f"Status: {status}")

        status, data = await self.request_v2("GET", "/chat/history/sessions", use_auth=True)
        self.log("GET /v2/chat/history/sessions", status == 200, f"Status: {status}")

        status, data = await self.request_v2("GET", "/webrtc/token", use_auth=True)
        self.log("GET /v2/webrtc/token", status == 200, f"Status: {status}")

    async def cleanup(self):
        print("\n" + "=" * 60)
        print("7. 清理测试数据")
        print("=" * 60)

        if self.team_id:
            status, data = await self.request(
                "DELETE", f"/teams/{self.team_id}", use_auth=True
            )
            self.log(f"DELETE /teams/{{team_id}} (删除测试团队)", status == 200, f"Status: {status}")

    async def print_summary(self):
        print("\n" + "=" * 60)
        print("测试结果汇总")
        print("=" * 60)

        passed = sum(1 for r in self.test_results if r["status"] == "PASS")
        failed = sum(1 for r in self.test_results if r["status"] == "FAIL")

        print(f"总计: {len(self.test_results)} 个测试")
        print(f"✅ 通过: {passed}")
        print(f"❌ 失败: {failed}")
        print(f"通过率: {passed/len(self.test_results)*100:.1f}%")

        if failed > 0:
            print("\n失败详情:")
            for r in self.test_results:
                if r["status"] == "FAIL":
                    msg = r["message"][:100] if len(r["message"]) > 100 else r["message"]
                    print(f"  - {r['test']}: {msg}")

    async def run_all_tests(self):
        await self.init_session()
        await self.test_health_check()
        await self.test_auth_apis()
        await self.test_team_apis()
        await self.test_join_team_api()
        await self.test_chat_apis()
        await self.test_other_apis()
        await self.test_api_v2()
        await self.cleanup()
        await self.print_summary()
        await self.close_session()


async def main():
    tester = APITester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
