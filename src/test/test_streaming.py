import asyncio
import aiohttp
import json
import time


async def test_streaming():
    url = "http://localhost:8000/api/v1/interview/guide/stream"

    # Test JD text
    jd_text = """
    职位名称：高级Python开发工程师
    职位描述：
    1. 负责公司核心业务系统的开发和维护
    2. 参与技术架构设计和优化
    3. 指导初级开发工程师
    4. 解决复杂的技术问题

    任职要求：
    1. 5年以上Python开发经验
    2. 精通Django、Flask等Web框架
    3. 熟悉分布式系统设计
    4. 良好的团队协作能力

    公司名称：科技有限公司
    """

    # Mock token for authentication
    token = "test_token"

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}

    data = {"jd_text": jd_text}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status != 200:
                print(f"Error: {response.status} - {await response.text()}")
                return

            print("\n=== Streaming Response Test ===")
            print(f"Status: {response.status}")
            print("\n--- Received Events ---")

            start_time = time.time()
            async for line in response.content:
                line = line.decode("utf-8").strip()
                if line and line.startswith("data: "):
                    data_part = line.replace("data: ", "")
                    if data_part == "[DONE]":
                        print("\n--- Stream Completed ---")
                        break

                    try:
                        event = json.loads(data_part)
                        current_time = time.time() - start_time
                        print(
                            f"[{current_time:.2f}s] Type: {event['type']}, Content: {event['content']}"
                        )
                    except json.JSONDecodeError:
                        print(f"[{current_time:.2f}s] Invalid JSON: {data_part}")

            print(f"\nTotal time: {time.time() - start_time:.2f}s")


if __name__ == "__main__":
    asyncio.run(test_streaming())
