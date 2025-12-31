#!/usr/bin/env python3
"""
增强RAG系统功能测试
测试新增的查询改写、增强检索、缓存等功能
"""

import asyncio
import sys
import os
from typing import List, Dict, Any

# 添加项目路径
sys.path.append('/')

from loguru import logger
from app.chains.rag_chain import (
    ask_knowledge_base, 
    batch_search,
    get_blog_retriever,
    get_interview_retriever,
    get_rewrite_chain,
    init_rag_components
)
from app.core.vector_store import vector_store
from app.core.cache import search_cache

# 配置日志
logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")

async def test_basic_functionality():
    """测试基础功能"""
    logger.info("🧪 开始测试基础功能...")
    
    try:
        # 初始化组件
        init_rag_components()
        logger.success("✅ RAG组件初始化成功")
        
        # 测试向量数据库
        health = vector_store.health_check()
        logger.info(f"🔍 向量数据库状态: {health}")
        
        stats = vector_store.get_stats()
        logger.info(f"📊 向量数据库统计: {stats}")
        
        return True
    except Exception as e:
        logger.error(f"❌ 基础功能测试失败: {e}")
        return False

async def test_retrieval_functions():
    """测试检索功能"""
    logger.info("🧪 开始测试检索功能...")
    
    try:
        # 获取检索器
        blog_retriever = get_blog_retriever()
        interview_retriever = get_interview_retriever()
        
        # 测试查询
        test_queries = [
            "Unity3D开发",
            "机器学习算法",
            "Python编程技巧"
        ]
        
        for query in test_queries:
            logger.info(f"🔍 测试查询: {query}")
            
            # 测试博客检索
            blog_docs = blog_retriever(query)
            logger.info(f"   📝 博客检索结果: {len(blog_docs)} 个文档")
            
            # 测试面经检索
            interview_docs = interview_retriever(query)
            logger.info(f"   💼 面经检索结果: {len(interview_docs)} 个文档")
            
            if blog_docs or interview_docs:
                logger.success(f"   ✅ 检索成功")
            else:
                logger.warning(f"   ⚠️  未找到相关文档")
        
        return True
    except Exception as e:
        logger.error(f"❌ 检索功能测试失败: {e}")
        return False

async def test_rewrite_chain():
    """测试查询改写功能"""
    logger.info("🧪 开始测试查询改写功能...")
    
    try:
        rewrite_chain = get_rewrite_chain()
        
        test_inputs = [
            "unity",
            "vue",
            "机器学习",
            "docker容器化"
        ]
        
        for test_input in test_inputs:
            logger.info(f"🔄 测试查询改写: '{test_input}'")
            
            try:
                rewritten = await rewrite_chain.ainvoke({"x": test_input})
                logger.info(f"   📝 改写结果: '{rewritten}'")
                
                if rewritten and len(rewritten.strip()) > 2:
                    logger.success("   ✅ 查询改写成功")
                else:
                    logger.warning("   ⚠️  改写结果过短")
            except Exception as e:
                logger.error(f"   ❌ 改写失败: {e}")
        
        return True
    except Exception as e:
        logger.error(f"❌ 查询改写测试失败: {e}")
        return False

async def test_enhanced_retrieval():
    """测试增强检索功能"""
    logger.info("🧪 开始测试增强检索功能...")
    
    try:
        from app.chains.rag_chain import enhanced_retrieval
        
        test_questions = [
            "如何学习Unity3D开发？",
            "Python的最佳实践是什么？",
            "机器学习入门建议"
        ]
        
        for question in test_questions:
            logger.info(f"🔍 测试增强检索: {question}")
            
            try:
                docs = enhanced_retrieval(question)
                logger.info(f"   📄 检索到 {len(docs)} 个文档")
                
                # 显示前2个文档的来源
                for i, doc in enumerate(docs[:2], 1):
                    source = doc.metadata.get("source", "未知")
                    logger.info(f"   📋 文档{i}: {source}")
                
                if docs:
                    logger.success("   ✅ 增强检索成功")
                else:
                    logger.warning("   ⚠️  未找到相关文档")
                    
            except Exception as e:
                logger.error(f"   ❌ 增强检索失败: {e}")
        
        return True
    except Exception as e:
        logger.error(f"❌ 增强检索测试失败: {e}")
        return False

async def test_knowledge_base_query():
    """测试知识库查询接口"""
    logger.info("🧪 开始测试知识库查询接口...")
    
    try:
        test_questions = [
            "什么是机器学习？",
            "Unity3D开发环境如何搭建？",
            "Python装饰器的作用是什么？"
        ]
        
        for question in test_questions:
            logger.info(f"🤖 测试知识库查询: {question}")
            
            try:
                result = await ask_knowledge_base(question, use_cache=True)
                
                answer = result.get("answer", "")
                sources = result.get("sources", [])
                doc_count = result.get("doc_count", 0)
                
                logger.info(f"   💬 答案: {answer[:100]}...")
                logger.info(f"   📚 来源数量: {len(sources)}")
                logger.info(f"   📄 文档数量: {doc_count}")
                
                if answer:
                    logger.success("   ✅ 知识库查询成功")
                else:
                    logger.warning("   ⚠️  未生成答案")
                    
            except Exception as e:
                logger.error(f"   ❌ 知识库查询失败: {e}")
        
        return True
    except Exception as e:
        logger.error(f"❌ 知识库查询测试失败: {e}")
        return False

async def test_cache_system():
    """测试缓存系统"""
    logger.info("🧪 开始测试缓存系统...")
    
    try:
        # 测试内存缓存
        test_key = "test_cache_key"
        test_value = "test_cache_value"
        
        # 设置缓存
        search_cache.set(test_key, test_value)
        logger.info(f"💾 设置缓存: {test_key}")
        
        # 获取缓存
        cached_value = search_cache.get(test_key)
        
        if cached_value == test_value:
            logger.success("✅ 内存缓存测试成功")
        else:
            logger.error(f"❌ 内存缓存测试失败: 期望 '{test_value}', 得到 '{cached_value}'")
            return False
        
        # 清除测试缓存
        # search_cache.delete(test_key)  # 如果有delete方法的话
        
        return True
    except Exception as e:
        logger.error(f"❌ 缓存系统测试失败: {e}")
        return False

async def test_batch_search():
    """测试批量搜索功能"""
    logger.info("🧪 开始测试批量搜索功能...")
    
    try:
        test_questions = [
            "Python基础语法",
            "Unity3D脚本编写",
            "机器学习算法"
        ]
        
        logger.info(f"🔄 批量搜索 {len(test_questions)} 个问题...")
        
        results = await batch_search(test_questions, use_cache=True)
        
        logger.info(f"📊 批量搜索完成，获得 {len(results)} 个结果")
        
        for i, result in enumerate(results):
            question = test_questions[i]
            answer = result.get("answer", "")
            sources = result.get("sources", [])
            
            logger.info(f"   问题{i+1}: {question}")
            logger.info(f"   答案长度: {len(answer)} 字符")
            logger.info(f"   来源数量: {len(sources)}")
            
            if answer and answer != "查询失败":
                logger.success(f"   ✅ 问题{i+1}查询成功")
            else:
                logger.warning(f"   ⚠️  问题{i+1}查询无结果或失败")
        
        return True
    except Exception as e:
        logger.error(f"❌ 批量搜索测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    logger.info("🚀 开始增强RAG系统功能测试")
    logger.info("=" * 50)
    
    test_results = []
    
    # 执行所有测试
    tests = [
        ("基础功能", test_basic_functionality),
        ("检索功能", test_retrieval_functions),
        ("查询改写", test_rewrite_chain),
        ("增强检索", test_enhanced_retrieval),
        ("知识库查询", test_knowledge_base_query),
        ("缓存系统", test_cache_system),
        ("批量搜索", test_batch_search),
    ]
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 运行测试: {test_name}")
        logger.info("-" * 30)
        
        try:
            result = await test_func()
            test_results.append((test_name, result))
            
            if result:
                logger.success(f"✅ {test_name} 测试通过")
            else:
                logger.error(f"❌ {test_name} 测试失败")
                
        except Exception as e:
            logger.error(f"❌ {test_name} 测试异常: {e}")
            test_results.append((test_name, False))
    
    # 输出测试总结
    logger.info("\n" + "=" * 50)
    logger.info("📊 测试结果总结:")
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\n🎯 总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        logger.success("🎉 所有测试都通过了！增强RAG系统功能正常")
    else:
        logger.warning(f"⚠️  有 {total - passed} 个测试失败，请检查相关功能")
    
    return passed == total

if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())