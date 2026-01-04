#!/usr/bin/env python3
"""
Confluence内容同步脚本
用于将Confluence页面同步到知识库向量库
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
from core.rag_engine import rag_engine
from core.config import settings


def sync_space(space_key: str):
    """
    同步指定空间的Confluence页面到知识库

    Args:
        space_key: Confluence空间的key
    """
    logger.info(f"🚀 [Sync] 开始同步空间: {space_key}")

    # 获取空间所有页面
    pages = confluence_service.get_space_pages(
        space_key=space_key, expand=["body.storage", "version", "history"]
    )

    if not pages:
        logger.warning(f"⚠️ [Sync] 空间 {space_key} 没有可同步的页面")
        return

    # 处理每个页面
    synced_count = 0
    failed_count = 0

    for page in pages:
        try:
            # 处理页面内容
            processed_page = content_processor.process_confluence_page(page)

            if not processed_page or not processed_page["cleaned_text"]:
                logger.warning(
                    f"⚠️ [Sync] 页面 '{page.get('title', '未知')}' 内容为空，跳过"
                )
                failed_count += 1
                continue

            # 生成来源信息
            source_name = f"Confluence_{space_key}_{page.get('id', 'unknown')}.md"
            source_url = (
                f"{settings.CONFLUENCE_URL}{page.get('_links', {}).get('webui', '')}"
            )

            # 准备要存入向量库的内容
            content_to_store = f"""# {processed_page['title']}

来源: {source_url}
空间: {space_key}
最后更新: {processed_page['updated_at']}
更新者: {processed_page['author']}

{processed_page['markdown_content']}
"""

            # 存入向量库
            rag_engine.ingest_knowledge(
                text_content=content_to_store, source_name=source_name
            )

            logger.success(f"✅ [Sync] 成功同步页面: '{processed_page['title']}'")
            synced_count += 1

        except Exception as e:
            logger.error(
                f"❌ [Sync] 同步页面 '{page.get('title', '未知')}' 失败: {str(e)}"
            )
            failed_count += 1

    logger.info(
        f"📊 [Sync] 空间 {space_key} 同步完成: 成功 {synced_count} 个, 失败 {failed_count} 个"
    )


def sync_all_spaces():
    """
    同步配置文件中指定的所有Confluence空间
    """
    spaces = settings.CONFLUENCE_SPACE_KEYS

    if not spaces:
        logger.warning("⚠️ [Sync] 配置文件中没有指定要同步的空间")
        return

    logger.info(f"🚀 [Sync] 开始同步所有配置的空间: {', '.join(spaces)}")

    for space in spaces:
        sync_space(space)
        logger.info("-" * 50)

    logger.info("🎉 [Sync] 所有空间同步完成！")


def sync_pages_by_label(label: str, space_key: str = None):
    """
    同步指定标签的Confluence页面

    Args:
        label: 标签名称
        space_key: 可选，指定空间
    """
    logger.info(f"🚀 [Sync] 开始同步标签: '{label}' 的页面")

    # 获取带标签的页面
    pages = confluence_service.get_pages_by_label(
        label=label, space_key=space_key, expand=["body.storage", "version", "history"]
    )

    if not pages:
        logger.warning(f"⚠️ [Sync] 没有找到带标签 '{label}' 的页面")
        return

    # 处理每个页面
    synced_count = 0
    failed_count = 0

    for page in pages:
        try:
            # 处理页面内容
            processed_page = content_processor.process_confluence_page(page)

            if not processed_page or not processed_page["cleaned_text"]:
                logger.warning(
                    f"⚠️ [Sync] 页面 '{page.get('title', '未知')}' 内容为空，跳过"
                )
                failed_count += 1
                continue

            # 生成来源信息
            space = page.get("space", {}).get("key", "unknown")
            source_name = f"Confluence_{space}_{page.get('id', 'unknown')}.md"
            source_url = (
                f"{settings.CONFLUENCE_URL}{page.get('_links', {}).get('webui', '')}"
            )

            # 准备要存入向量库的内容
            content_to_store = f"""# {processed_page['title']}

来源: {source_url}
空间: {space}
标签: {label}
最后更新: {processed_page['updated_at']}
更新者: {processed_page['author']}

{processed_page['markdown_content']}
"""

            # 存入向量库
            rag_engine.ingest_knowledge(
                text_content=content_to_store, source_name=source_name
            )

            logger.success(f"✅ [Sync] 成功同步页面: '{processed_page['title']}'")
            synced_count += 1

        except Exception as e:
            logger.error(
                f"❌ [Sync] 同步页面 '{page.get('title', '未知')}' 失败: {str(e)}"
            )
            failed_count += 1

    logger.info(
        f"📊 [Sync] 标签 '{label}' 同步完成: 成功 {synced_count} 个, 失败 {failed_count} 个"
    )


if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
    )

    logger.info("📚 [Sync] Confluence内容同步工具启动")

    try:
        # 检查参数
        if len(sys.argv) < 2:
            logger.error("❌ 参数错误: 请指定要执行的操作")
            logger.error("用法:")
            logger.error(
                "  python sync_confluence_to_kb.py space <space_key>    # 同步指定空间"
            )
            logger.error(
                "  python sync_confluence_to_kb.py all               # 同步所有配置的空间"
            )
            logger.error(
                "  python sync_confluence_to_kb.py label <label>      # 同步指定标签的页面"
            )
            logger.error(
                "  python sync_confluence_to_kb.py label <label> <space_key>  # 同步指定空间和标签的页面"
            )
            sys.exit(1)

        command = sys.argv[1]

        if command == "space":
            if len(sys.argv) < 3:
                logger.error("❌ 参数错误: 请指定空间key")
                sys.exit(1)
            sync_space(sys.argv[2])

        elif command == "all":
            sync_all_spaces()

        elif command == "label":
            if len(sys.argv) < 3:
                logger.error("❌ 参数错误: 请指定标签名称")
                sys.exit(1)

            label = sys.argv[2]
            space_key = sys.argv[3] if len(sys.argv) > 3 else None
            sync_pages_by_label(label, space_key)

        else:
            logger.error(f"❌ 未知命令: {command}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"❌ [Sync] 同步过程中发生错误: {str(e)}")
        logger.exception(e)
        sys.exit(1)

    logger.info("👋 [Sync] Confluence内容同步工具结束")
