#!/usr/bin/env python3
"""
简化向量存储测试
测试向量数据库基础功能，避免外部API调用
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.append('/')

from loguru import logger
from app.core.vector_store import vector_store

# 配置日志
logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")

def test_vector_store_basics():
    """测试向量存储基础功能"""
    logger.info("🧪 开始测试向量存储基础功能...")
    
    try:
        # 测试健康检查
        health = vector_store.health_check()
        logger.info(f"🔍 健康检查: {health}")
        
        # 测试统计信息
        stats = vector_store.get_stats()
        logger.info(f"📊 统计信息: {stats}")
        
        # 测试集合名称
        collection_name = vector_store.collection_name
        logger.info(f"📂 集合名称: {collection_name}")
        
        # 测试嵌入模型
        model_name = vector_store.embeddings.model_name
        logger.info(f"🤖 嵌入模型: {model_name}")
        
        logger.success("✅ 向量存储基础功能测试成功")
        return True
        
    except Exception as e:
        logger.error(f"❌ 向量存储基础功能测试失败: {e}")
        return False

def test_cache_functionality():
    """测试缓存功能"""
    logger.info("🧪 开始测试缓存功能...")
    
    try:
        from app.core.cache import search_cache
        
        # 测试基本缓存操作
        test_key = "test_key_simple"
        test_value = "test_value"
        
        # 设置缓存
        search_cache.set(test_key, test_value)
        logger.info(f"💾 设置缓存: {test_key}")
        
        # 获取缓存
        cached_value = search_cache.get(test_key)
        
        if cached_value == test_value:
            logger.success("✅ 缓存读写测试成功")
        else:
            logger.error(f"❌ 缓存测试失败: 期望 '{test_value}', 得到 '{cached_value}'")
            return False
        
        # 测试复杂数据类型
        complex_data = {
            "name": "测试",
            "values": [1, 2, 3],
            "nested": {"key": "value"}
        }
        
        search_cache.set("complex_test", complex_data)
        cached_complex = search_cache.get("complex_test")
        
        if cached_complex == complex_data:
            logger.success("✅ 复杂数据缓存测试成功")
        else:
            logger.error("❌ 复杂数据缓存测试失败")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 缓存功能测试失败: {e}")
        return False

def test_settings_config():
    """测试配置系统"""
    logger.info("🧪 开始测试配置系统...")
    
    try:
        from app.core.config import settings
        
        # 测试基本配置
        logger.info(f"📋 项目名称: {settings.PROJECT_NAME}")
        logger.info(f"📋 版本: {settings.VERSION}")
        logger.info(f"📋 向量数据库路径: {settings.VECTOR_DB_PATH}")
        logger.info(f"📋 嵌入模型: {settings.EMBEDDING_MODEL_NAME}")
        logger.info(f"📋 爬虫延迟: {settings.CRAWLER_DELAY_MIN}-{settings.CRAWLER_DELAY_MAX}秒")
        
        # 测试目录创建
        if Path(settings.VECTOR_DB_PATH).exists():
            logger.success("✅ 向量数据库目录已创建")
        else:
            logger.warning("⚠️  向量数据库目录不存在")
        
        logger.success("✅ 配置系统测试成功")
        return True
        
    except Exception as e:
        logger.error(f"❌ 配置系统测试失败: {e}")
        return False

def test_exception_handling():
    """测试异常处理系统"""
    logger.info("🧪 开始测试异常处理系统...")
    
    try:
        from app.core.exceptions import JDAgentError, VectorStoreError, CrawlerError, RAGError
        
        # 测试基础异常
        try:
            raise JDAgentError("测试基础异常", error_code="TEST_001")
        except JDAgentError as e:
            logger.info(f"✅ 基础异常测试: {e.message} (代码: {e.error_code})")
        
        # 测试向量存储异常
        try:
            raise VectorStoreError("测试向量存储异常", error_code="VECTOR_001")
        except VectorStoreError as e:
            logger.info(f"✅ 向量存储异常测试: {e.message} (代码: {e.error_code})")
        
        # 测试RAG异常
        try:
            raise RAGError("测试RAG异常", error_code="RAG_001")
        except RAGError as e:
            logger.info(f"✅ RAG异常测试: {e.message} (代码: {e.error_code})")
        
        logger.success("✅ 异常处理系统测试成功")
        return True
        
    except Exception as e:
        logger.error(f"❌ 异常处理系统测试失败: {e}")
        return False

def main():
    """主测试函数"""
    logger.info("🚀 开始简化向量存储和架构测试")
    logger.info("=" * 50)
    
    test_results = []
    
    # 执行所有测试
    tests = [
        ("向量存储基础", test_vector_store_basics),
        ("缓存功能", test_cache_functionality),
        ("配置系统", test_settings_config),
        ("异常处理", test_exception_handling),
    ]
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 运行测试: {test_name}")
        logger.info("-" * 30)
        
        try:
            result = test_func()
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
        logger.success("🎉 所有简化测试都通过了！架构优化成功")
    else:
        logger.warning(f"⚠️  有 {total - passed} 个测试失败")
    
    return passed == total

if __name__ == "__main__":
    main()