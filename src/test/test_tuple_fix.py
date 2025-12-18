#!/usr/bin/env python3
"""
测试脚本：验证元组消息处理修复

该脚本模拟了 jd_parser_node 函数中可能出现的元组消息情况，
用于验证 llm_factory.py 中的修复是否有效。
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath("/"))

import asyncio
import logging
from langchain_core.messages import HumanMessage, AIMessage
from app.core.llm_factory import get_llm
from app.chains.jd_parser import parse_jd_async

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("test_tuple_fix")


def test_tuple_message_serialization():
    """测试元组消息的序列化"""
    logger.info("🚀 开始测试元组消息序列化...")

    # 创建一个模拟的元组消息，类似于可能从 chain.ainvoke 返回的格式
    tuple_message = (
        {"type": "human", "content": "测试消息1"},
        {"type": "ai", "content": "测试消息2"},
    )

    logger.info(f"📝 测试元组消息: {tuple_message}")

    # 获取带缓存的 LLM
    llm = get_llm(use_cache=True)

    # 测试缓存键生成
    try:
        cache_key = llm._generate_cache_key(tuple_message)
        logger.info(f"✅ 成功生成缓存键: {cache_key}")
    except Exception as e:
        logger.error(f"❌ 生成缓存键失败: {e}")
        return False

    logger.info("✅ 元组消息序列化测试通过!")
    return True


async def test_parse_jd_async():
    """测试 parse_jd_async 函数"""
    logger.info("🚀 开始测试 parse_jd_async 函数...")

    # 准备一个简单的 JD 文本
    jd_text = """职位描述：
我们正在寻找一位经验丰富的前端工程师，负责开发和维护我们的Web应用。

职位要求：
1. 3年以上前端开发经验
2. 精通React、Next.js等前端框架
3. 熟悉JavaScript/TypeScript
4. 良好的代码规范和团队协作能力

公司名称：Tech公司"""

    try:
        result = await parse_jd_async(jd_text)
        logger.info(f"✅ parse_jd_async 执行成功，结果类型: {type(result).__name__}")
        logger.info(f"📝 解析结果: {result}")
        return True
    except Exception as e:
        logger.error(f"❌ parse_jd_async 执行失败: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    logger.info("🌟 开始所有测试...")

    # 测试元组消息序列化
    test1_passed = test_tuple_message_serialization()

    # 测试 parse_jd_async 函数
    test2_passed = await test_parse_jd_async()

    # 总结测试结果
    logger.info("\n" + "=" * 50)
    logger.info("📊 测试总结:")
    logger.info(f"✅ 元组消息序列化测试: {'通过' if test1_passed else '失败'}")
    logger.info(f"✅ parse_jd_async 函数测试: {'通过' if test2_passed else '失败'}")

    if test1_passed and test2_passed:
        logger.info("🎉 所有测试通过！修复有效！")
        return 0
    else:
        logger.error("❌ 部分测试失败，请检查修复！")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
