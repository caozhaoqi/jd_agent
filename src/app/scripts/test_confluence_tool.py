#!/usr/bin/env python3
"""
Confluence工具测试脚本
用于验证Confluence读取工具的功能
"""

import os
import sys
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from core.confluence_service import confluence_service
from core.content_processor import content_processor
from core.config import settings


def test_confluence_connection():
    """
    测试Confluence连接
    """
    logger.info("🔌 [Test] 测试Confluence连接...")

    if confluence_service.confluence:
        try:
            server_info = confluence_service.confluence.get_server_info()
            logger.success(
                f"✅ [Test] 连接成功！服务器版本: {server_info.get('version', '未知')}"
            )
            return True
        except Exception as e:
            logger.error(f"❌ [Test] 连接测试失败: {str(e)}")
            return False
    else:
        logger.error("❌ [Test] 未建立Confluence连接")
        return False


def test_get_spaces():
    """
    测试获取空间列表
    """
    logger.info("📋 [Test] 测试获取空间列表...")

    if not confluence_service.confluence:
        logger.error("❌ [Test] 未建立Confluence连接")
        return False

    try:
        spaces = confluence_service.confluence.get_all_spaces(start=0, limit=5)

        if spaces and "results" in spaces:
            logger.success(f"✅ [Test] 成功获取 {len(spaces['results'])} 个空间")
            logger.info("📄 空间列表:")
            for space in spaces["results"][:3]:  # 只显示前3个
                logger.info(f"   - {space.get('name')} (key: {space.get('key')})")
            if len(spaces["results"]) > 3:
                logger.info(f"   ... 等 {len(spaces['results'])} 个空间")
            return True
        else:
            logger.error("❌ [Test] 获取空间列表失败")
            return False

    except Exception as e:
        logger.error(f"❌ [Test] 获取空间列表失败: {str(e)}")
        return False


def test_get_space_pages(space_key: str):
    """
    测试获取指定空间的页面

    Args:
        space_key: Confluence空间的key
    """
    logger.info(f"📄 [Test] 测试获取空间 {space_key} 的页面...")

    try:
        pages = confluence_service.get_space_pages(space_key, expand=["body.view"])

        if pages:
            logger.success(f"✅ [Test] 成功获取 {len(pages)} 个页面")
            logger.info("📄 页面列表:")
            for page in pages[:3]:  # 只显示前3个
                logger.info(f"   - {page.get('title')}")
            if len(pages) > 3:
                logger.info(f"   ... 等 {len(pages)} 个页面")
            return pages[:1]  # 返回第一个页面用于后续测试
        else:
            logger.error(f"❌ [Test] 空间 {space_key} 没有页面")
            return None

    except Exception as e:
        logger.error(f"❌ [Test] 获取空间 {space_key} 的页面失败: {str(e)}")
        return None


def test_content_processing(page):
    """
    测试内容处理功能

    Args:
        page: Confluence页面对象
    """
    logger.info(f"🔧 [Test] 测试内容处理，页面: '{page.get('title', '未知')}'")

    try:
        processed_page = content_processor.process_confluence_page(page)

        if processed_page:
            logger.success("✅ [Test] 内容处理成功")

            logger.info("📝 处理结果:")
            logger.info(f"   标题: {processed_page.get('title')}")
            logger.info(f"   ID: {processed_page.get('id')}")
            logger.info(f"   空间: {processed_page.get('space_key')}")
            logger.info(f"   更新时间: {processed_page.get('updated_at')}")
            logger.info(f"   原文长度: {len(processed_page.get('original_html', ''))}")
            logger.info(f"   纯文本长度: {len(processed_page.get('cleaned_text', ''))}")

            # 显示部分Markdown内容
            markdown = processed_page.get("markdown_content", "")
            if markdown:
                preview = markdown[:200] + "..." if len(markdown) > 200 else markdown
                logger.info(f"   Markdown预览: {preview}")

            return True
        else:
            logger.error("❌ [Test] 内容处理失败")
            return False

    except Exception as e:
        logger.error(f"❌ [Test] 内容处理失败: {str(e)}")
        return False


def test_get_page_by_title(space_key: str, title: str):
    """
    测试根据标题获取页面

    Args:
        space_key: Confluence空间的key
        title: 页面标题
    """
    logger.info(f"🔍 [Test] 测试根据标题获取页面: '{title}'")

    try:
        page = confluence_service.get_page_by_title(
            space_key, title, expand=["body.view"]
        )

        if page:
            logger.success(f"✅ [Test] 成功获取页面: '{page.get('title')}'")
            return True
        else:
            logger.error(f"❌ [Test] 未找到页面: '{title}'")
            return False

    except Exception as e:
        logger.error(f"❌ [Test] 获取页面失败: {str(e)}")
        return False


def test_get_pages_by_label(label: str):
    """
    测试根据标签获取页面

    Args:
        label: 标签名称
    """
    logger.info(f"🏷️ [Test] 测试根据标签获取页面: '{label}'")

    try:
        pages = confluence_service.get_pages_by_label(label, expand=["body.view"])

        if pages:
            logger.success(f"✅ [Test] 成功获取 {len(pages)} 个带标签 '{label}' 的页面")
            for page in pages[:3]:
                logger.info(f"   - {page.get('title')}")
            return True
        else:
            logger.warning(f"⚠️ [Test] 没有找到带标签 '{label}' 的页面")
            return True

    except Exception as e:
        logger.error(f"❌ [Test] 获取带标签页面失败: {str(e)}")
        return False


if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
    )

    logger.info("🧪 [Test] Confluence工具测试开始")

    # 检查配置
    if not all(
        [
            settings.CONFLUENCE_URL,
            settings.CONFLUENCE_USERNAME,
            settings.CONFLUENCE_PASSWORD,
        ]
    ):
        logger.error("❌ [Test] Confluence配置不完整")
        logger.error("请在 .env 文件中配置以下参数:")
        logger.error("  CONFLUENCE_URL=your_confluence_url")
        logger.error("  CONFLUENCE_USERNAME=your_username")
        logger.error("  CONFLUENCE_PASSWORD=your_password")
        sys.exit(1)

    logger.info(f"📋 [Test] 当前配置:")
    logger.info(f"   服务器: {settings.CONFLUENCE_URL}")
    logger.info(f"   用户名: {settings.CONFLUENCE_USERNAME}")
    logger.info(f"   同步空间: {settings.CONFLUENCE_SPACE_KEYS}")

    logger.info("-" * 50)

    # 运行测试
    tests = [
        ("连接测试", test_confluence_connection, []),
        ("空间列表测试", test_get_spaces, []),
    ]

    # 如果指定了空间key参数，运行更多测试
    if len(sys.argv) > 1:
        space_key = sys.argv[1]
        logger.info(f"🔧 [Test] 使用空间key: {space_key}")

        # 测试获取指定空间的页面
        pages = test_get_space_pages(space_key)

        if pages and len(pages) > 0:
            # 测试内容处理
            test_content_processing(pages[0])

            # 测试根据标题获取页面
            test_get_page_by_title(space_key, pages[0].get("title", ""))

        # 如果指定了标签参数，测试根据标签获取页面
        if len(sys.argv) > 2:
            label = sys.argv[2]
            test_get_pages_by_label(label)

    logger.info("-" * 50)
    logger.info("🧪 [Test] Confluence工具测试结束")
