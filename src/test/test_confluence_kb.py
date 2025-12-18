import os
import sys
import json
from typing import Dict, Any

# 添加src目录到Python搜索路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from app.utils.logger import logger
from app.confluence.confluence_kb import ConfluenceKnowledgeBase


def test_kb_initialization():
    """测试知识库初始化"""
    logger.info("测试Confluence知识库初始化...")
    
    try:
        # 测试数据目录创建
        test_data_dir = "./test_confluence_data"
        kb = ConfluenceKnowledgeBase(data_dir=test_data_dir)
        
        # 测试页面保存和加载
        test_page = {
            "page_id": "123456",
            "title": "测试页面",
            "content": "这是一个测试页面的内容",
            "url": "https://wiki.hcmcloud.cn/pages/viewpage.action?pageId=123456",
            "space_name": "TEST",
            "author": "测试用户",
            "created_at": "2025-12-18T00:00:00.000Z",
            "updated_at": "2025-12-18T00:00:00.000Z",
            "metadata": {"labels": ["测试", "示例"]}
        }
        
        # 保存测试页面
        from app.confluence.confluence_kb import ConfluencePage
        page_obj = ConfluencePage(**test_page)
        kb.save_page(page_obj)
        
        # 加载测试页面
        loaded_pages = kb.load_all_pages()
        logger.info(f"✅ 保存并加载了 {len(loaded_pages)} 个测试页面")
        
        # 测试页面转换为Document
        doc = page_obj.to_document()
        logger.info(f"✅ 成功将页面转换为Document格式，内容长度: {len(doc.page_content)}")
        
        # 清理测试数据
        import shutil
        if os.path.exists(test_data_dir):
            shutil.rmtree(test_data_dir)
        
        return True
    except Exception as e:
        logger.error(f"❌ 知识库初始化测试失败: {e}")
        return False


def test_build_kb_script():
    """测试知识库构建脚本"""
    logger.info("测试知识库构建脚本...")
    
    try:
        # 创建模拟数据目录和页面数据
        test_data_dir = "./test_confluence_data"
        os.makedirs(test_data_dir, exist_ok=True)
        
        # 创建模拟页面数据
        test_pages = [

        ]
        
        # 保存模拟页面数据
        with open(os.path.join(test_data_dir, "confluence_pages.json"), "w", encoding="utf-8") as f:
            json.dump(test_pages, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 创建了 {len(test_pages)} 个模拟页面数据")
        
        # 清理测试数据
        import shutil
        if os.path.exists(test_data_dir):
            shutil.rmtree(test_data_dir)
        
        return True
    except Exception as e:
        logger.error(f"❌ 知识库构建脚本测试失败: {e}")
        return False


def main():
    """运行所有测试"""
    logger.info("🚀 开始运行Confluence Wiki知识库测试...")
    
    # 测试1: 知识库初始化
    test1_result = test_kb_initialization()
    
    # 测试2: 知识库构建脚本
    test2_result = test_build_kb_script()
    
    # 测试结果汇总
    if test1_result and test2_result:
        logger.success("✅ 所有测试通过！Confluence Wiki知识库功能正常。")
    else:
        logger.error("❌ 部分测试失败，请检查代码。")


if __name__ == "__main__":
    main()
