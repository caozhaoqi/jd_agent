import asyncio
import time
import httpx
import json

# 测试配置
API_URL = "http://localhost:8000/api/v1"
TEST_JD = """职位名称：Python 开发工程师
职位描述：
1. 负责公司后端服务的开发和维护
2. 使用 Python, FastAPI 等技术栈
3. 参与数据库设计和优化
4. 与前端团队协作完成功能开发

任职要求：
1. 本科及以上学历，计算机相关专业
2. 3年以上 Python 开发经验
3. 熟悉 FastAPI 框架
4. 熟悉 MySQL 或 PostgreSQL
5. 有良好的代码风格和团队协作能力

公司信息：
公司名称：字节跳动
公司规模：10000人以上
"""
TEST_QUESTION = "什么是 Python 的装饰器？"


async def test_interview_guide():
    """测试面试指南生成接口"""
    print("\n=== 测试面试指南生成接口 ===")
    start_time = time.time()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/interview/guide",
            json={"jd_text": TEST_JD},
            headers={"Authorization": "Bearer test_token"},  # 假设的测试令牌
        )

    end_time = time.time()
    elapsed_time = end_time - start_time

    print(f"响应时间：{elapsed_time:.2f} 秒")
    print(f"状态码：{response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"公司名称：{result.get('meta', {}).get('company_name', '未知')}")
        print(f"技术问题数量：{len(result.get('tech_questions', []))}")
        print(f"HR问题数量：{len(result.get('hr_questions', []))}")

    return elapsed_time


async def test_rag_query():
    """测试RAG查询接口"""
    print("\n=== 测试RAG查询接口 ===")
    start_time = time.time()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/qa/qa", json={"question": TEST_QUESTION}
        )

    end_time = time.time()
    elapsed_time = end_time - start_time

    print(f"响应时间：{elapsed_time:.2f} 秒")
    print(f"状态码：{response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"回答：{result.get('answer', '')[:100]}...")
        print(f"来源：{result.get('sources', [])}")

    return elapsed_time


async def test_stream_rag_query():
    """测试流式RAG查询接口"""
    print("\n=== 测试流式RAG查询接口 ===")
    start_time = time.time()

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST", f"{API_URL}/qa/qa/stream", json={"question": TEST_QUESTION}
        ) as response:
            print(f"状态码：{response.status_code}")

            if response.status_code == 200:
                full_content = ""
                first_chunk_time = None

                async for chunk in response.aiter_text():
                    if chunk.strip():
                        for line in chunk.splitlines():
                            if line.startswith("data:"):
                                data = line[5:].strip()
                                if data != "[DONE]":
                                    try:
                                        parsed = json.loads(data)
                                        if parsed["type"] == "chunk":
                                            if first_chunk_time is None:
                                                first_chunk_time = time.time()
                                                first_token_time = (
                                                    first_chunk_time - start_time
                                                )
                                                print(
                                                    f"首令牌时间：{first_token_time:.2f} 秒"
                                                )
                                            full_content += parsed["content"]
                                    except json.JSONDecodeError:
                                        pass

                end_time = time.time()
                total_time = end_time - start_time
                print(f"总响应时间：{total_time:.2f} 秒")
                print(f"完整回答：{full_content[:100]}...")

                return total_time

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"响应时间：{elapsed_time:.2f} 秒")

    return elapsed_time


async def main():
    """主测试函数"""
    print("开始测试优化后的系统响应时间...")

    # 运行多次测试取平均值
    iterations = 3

    # 测试面试指南生成
    interview_times = []
    for i in range(iterations):
        print(f"\n第 {i+1}/{iterations} 次测试面试指南生成")
        try:
            time_taken = await test_interview_guide()
            interview_times.append(time_taken)
        except Exception as e:
            print(f"测试失败：{e}")
            import traceback

            traceback.print_exc()

    if interview_times:
        avg_interview_time = sum(interview_times) / len(interview_times)
        print(f"\n面试指南生成平均响应时间：{avg_interview_time:.2f} 秒")

    # 测试RAG查询
    rag_times = []
    for i in range(iterations):
        print(f"\n第 {i+1}/{iterations} 次测试RAG查询")
        try:
            time_taken = await test_rag_query()
            rag_times.append(time_taken)
        except Exception as e:
            print(f"测试失败：{e}")
            import traceback

            traceback.print_exc()

    if rag_times:
        avg_rag_time = sum(rag_times) / len(rag_times)
        print(f"\nRAG查询平均响应时间：{avg_rag_time:.2f} 秒")

    # 测试流式RAG查询
    stream_rag_times = []
    for i in range(iterations):
        print(f"\n第 {i+1}/{iterations} 次测试流式RAG查询")
        try:
            time_taken = await test_stream_rag_query()
            stream_rag_times.append(time_taken)
        except Exception as e:
            print(f"测试失败：{e}")
            import traceback

            traceback.print_exc()

    if stream_rag_times:
        avg_stream_rag_time = sum(stream_rag_times) / len(stream_rag_times)
        print(f"\n流式RAG查询平均响应时间：{avg_stream_rag_time:.2f} 秒")

    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
