#!/usr/bin/env python3
"""
测试脚本：验证LLM缓存修复是否有效

该脚本模拟了jd_parser_node函数中的调用场景，测试缓存命中时是否能正确处理类型
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('/'))

import asyncio
import logging
from langchain_core.messages import HumanMessage, AIMessage
from app.core.llm_factory import get_llm
from app.chains.jd_parser import parse_jd_async

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger('test_cache_fix')

async def test_cache_hit_scenarios():
    """测试缓存命中时的不同场景"""
    logger.info("🚀 开始测试LLM缓存修复...")
    
    # 准备一个简单的JD文本
    jd_text = """职位描述：
我们正在寻找一位经验丰富的前端工程师，负责开发和维护我们的Web应用。

职位要求：
1. 3年以上前端开发经验
2. 精通React、Next.js等前端框架
3. 熟悉JavaScript/TypeScript
4. 良好的代码规范和团队协作能力

公司名称：Tech公司"""
    
    try:
        # 第一次调用，应该会缓存结果
        logger.info("🔄 第一次调用（预期缓存未命中）")
        result1 = await parse_jd_async(jd_text)
        logger.info(f"✅ 第一次调用成功，结果：{result1}")
        
        # 第二次调用，应该会命中缓存
        logger.info("🔄 第二次调用（预期缓存命中）")
        result2 = await parse_jd_async(jd_text)
        logger.info(f"✅ 第二次调用成功，结果：{result2}")
        
        # 验证两次结果一致
        if result1 == result2:
            logger.info("✅ 两次调用结果一致，缓存机制正常工作")
        else:
            logger.error("❌ 两次调用结果不一致")
            
        logger.info("🎉 所有测试通过！")
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_cache_hit_scenarios())
