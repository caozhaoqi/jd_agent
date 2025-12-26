#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试增强的RAG系统，验证博客和面经数据的联合检索功能
"""

import asyncio
import os
import sys

# 将项目根目录添加到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'src'))

from loguru import logger
from app.chains.rag_chain import ask_knowledge_base

# 配置日志
logger.remove()
logger.add(sys.stdout, level="DEBUG")

async def test_enhanced_rag():
    """测试增强的RAG系统"""
    logger.info("开始测试增强的RAG系统...")
    
    # 测试问题1：偏向技术知识的问题
    question1 = "Python中列表推导式的用法"
    logger.info(f"\n测试问题1: {question1}")
    result1 = await ask_knowledge_base(question1)
    logger.info(f"回答: {result1['answer']}")
    logger.info(f"来源: {result1['sources']}")
    
    # 测试问题2：偏向面试经验的问题
    question2 = "Python面试中常见的算法问题"
    logger.info(f"\n测试问题2: {question2}")
    result2 = await ask_knowledge_base(question2)
    logger.info(f"回答: {result2['answer']}")
    logger.info(f"来源: {result2['sources']}")
    
    # 测试问题3：混合问题
    question3 = "如何准备Python后端开发面试"
    logger.info(f"\n测试问题3: {question3}")
    result3 = await ask_knowledge_base(question3)
    logger.info(f"回答: {result3['answer']}")
    logger.info(f"来源: {result3['sources']}")
    
    logger.info("\n增强RAG系统测试完成！")

if __name__ == "__main__":
    asyncio.run(test_enhanced_rag())
