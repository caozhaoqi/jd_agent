#!/usr/bin/env python3
"""
测试进度流功能 - 用户发送JD后能看到后台进度状态
"""

import asyncio
import json
import httpx
import time
import sys

# API配置
API_URL = "http://localhost:8000/api/v1"
TOKEN = "your_test_token_here"  # 替换为实际的测试token

# 测试JD文本
TEST_JD = """
岗位职责：
1. 负责公司产品的前端开发工作
2. 熟练使用React、TypeScript、Next.js等技术栈
3. 有良好的代码规范和团队协作能力

任职要求：
1. 本科及以上学历，计算机相关专业
2. 3-5年前端开发经验
3. 熟悉现代前端框架和工具链
4. 具备良好的沟通能力和学习能力

公司信息：
- 公司名称：科技有限公司
- 行业：互联网
- 规模：500-1000人
"""


async def test_progress_stream():
    """测试进度流功能"""
    print("🚀 开始测试进度流功能...")
    print(f"\n📝 测试JD文本长度: {len(TEST_JD)} 字符")

    async with httpx.AsyncClient() as client:
        try:
            # 发送POST请求到流式接口
            response = await client.post(
                f"{API_URL}/interview/guide/stream",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {TOKEN}",
                },
                json={"jd_text": TEST_JD},
                timeout=None,  # 流式响应需要禁用超时
            )

            print(f"\n📡 连接状态: {response.status_code} {response.reason_phrase}")
            print(f"📡 内容类型: {response.headers.get('content-type')}")

            if response.status_code != 200:
                print(f"❌ 请求失败: {response.status_code} {response.reason_phrase}")
                return

            # 处理流式响应
            print("\n\n🔄 开始接收进度更新...\n")

            start_time = time.time()
            progress_count = 0
            thought_count = 0
            data_count = 0
            result_count = 0

            # 逐行处理SSE事件
            async for line in response.aiter_lines():
                line = line.strip()
                if not line:
                    continue

                if line.startswith("data: "):
                    data = line[6:].strip()

                    if data == "[DONE]":
                        print("\n✅ 流结束信号 [DONE]")
                        break

                    try:
                        payload = json.loads(data)
                        progress_count += 1

                        # 根据消息类型处理
                        if payload.get("type") == "thought":
                            thought_count += 1
                            print(
                                f"💡 [{thought_count}] 思考过程: {payload.get('content', '')}"
                            )
                            if payload.get("detail"):
                                print(f"   📝 详情: {payload.get('detail')}")

                        elif payload.get("type") == "data":
                            data_count += 1
                            key = payload.get("key")
                            value = payload.get("value")
                            print(f"📊 [{data_count}] 数据更新: {key}")
                            if isinstance(value, list):
                                print(f"   📋 内容: {value[:5]}... ({len(value)}项)")
                            elif isinstance(value, dict):
                                print(f"   📋 内容: {list(value.keys())}")
                            else:
                                print(f"   📋 内容: {value}")

                        elif payload.get("type") == "token":
                            # 过滤掉token内容，避免输出过多
                            pass

                        elif payload.get("type") == "result":
                            result_count += 1
                            print(f"\n📄 [{result_count}] 结果生成完成")

                        elif payload.get("type") == "error":
                            print(f"❌ 错误: {payload.get('content', '')}")

                        else:
                            print(f"📌 未知类型: {payload.get('type')}")

                    except json.JSONDecodeError as e:
                        print(f"⚠️ 解析JSON失败: {e}")
                        print(f"   原始数据: {data}")
                    except Exception as e:
                        print(f"⚠️ 处理消息失败: {e}")

            end_time = time.time()
            total_time = end_time - start_time

            print("\n\n📊 测试统计:")
            print(f"⏱️  总耗时: {total_time:.2f} 秒")
            print(f"📥 总消息数: {progress_count} 条")
            print(f"💡 思考过程: {thought_count} 条")
            print(f"📊 数据更新: {data_count} 条")
            print(f"📄 结果消息: {result_count} 条")
            print("\n✅ 测试完成")

        except httpx.RequestError as e:
            print(f"❌ 请求错误: {e}")
        except Exception as e:
            print(f"❌ 测试失败: {e}")


if __name__ == "__main__":
    if not TOKEN:
        print("❌ 请先设置测试用的TOKEN")
        sys.exit(1)

    asyncio.run(test_progress_stream())
