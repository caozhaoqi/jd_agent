import os
import sys
import time
from typing import List, Dict, Any, Optional
from atlassian import Confluence
from app.utils.logger import logger
from app.confluence.config import confluence_config
from app.confluence.confluence_kb import ConfluencePage, ConfluenceKnowledgeBase


class ConfluenceCrawler:
    """Confluence页面爬虫类"""

    def __init__(self):
        self.confluence = self._connect()
        self.kb = ConfluenceKnowledgeBase()

    def _connect(self) -> Confluence:
        """连接到Confluence服务器"""
        logger.info(f"正在连接到Confluence服务器: {confluence_config.url}")

        try:
            confluence = Confluence(
                url=confluence_config.url,
                username=confluence_config.username,
                password=confluence_config.password,
                proxies=confluence_config.proxies,
                cloud=False,  # 企业内部服务器设置为False
            )

            # 测试连接
            confluence.get_all_spaces(start=0, limit=1)
            logger.success("✅ Confluence服务器连接成功")
            return confluence
        except Exception as e:
            logger.error(f"❌ Confluence服务器连接失败: {e}")
            raise

    def get_all_spaces(self) -> List[Dict[str, Any]]:
        """获取所有空间"""
        try:
            spaces = self.confluence.get_all_spaces(start=0, limit=50)
            return spaces.get("results", [])
        except Exception as e:
            logger.error(f"获取空间列表失败: {e}")
            return []

    def get_pages_in_space(
        self, space_key: str, depth: int = 2
    ) -> List[Dict[str, Any]]:
        """获取指定空间的所有页面"""
        try:
            # 直接获取空间所有页面
            pages = self.confluence.get_all_pages_from_space(
                space=space_key,
                start=0,
                limit=100,
                expand="body.storage,version,history.createdBy,history.lastUpdatedBy",
                status="current",
            )

            logger.info(f"空间 {space_key} 共有 {len(pages)} 个页面")
            return pages
        except Exception as e:
            logger.error(f"获取空间 {space_key} 的页面失败: {e}")
            return []

    def extract_page_info(self, page: Dict[str, Any]) -> Optional[ConfluencePage]:
        """提取页面信息并创建ConfluencePage对象"""
        try:
            # 获取基本信息
            page_id = str(page.get("id"))
            title = page.get("title", "")
            space_name = (
                page.get("space", {}).get("name", "")
                or page.get("_expandable", {}).get("space", "").split("/")[-1]
            )

            # 获取内容
            content = page.get("body", {}).get("storage", {}).get("value", "")
            if not content:
                content = page.get("body", {}).get("view", {}).get("value", "")

            # 获取URL
            url = f"{confluence_config.url}/pages/viewpage.action?pageId={page_id}"

            # 获取作者信息
            created_by = (
                page.get("history", {}).get("createdBy", {}).get("displayName", "未知")
            )
            updated_by = (
                page.get("history", {})
                .get("lastUpdatedBy", {})
                .get("displayName", "未知")
            )

            # 获取时间信息
            created_at = page.get("history", {}).get("createdDate", "")
            updated_at = page.get("version", {}).get("when", "")

            # 提取元数据
            metadata = {
                "created_by": created_by,
                "updated_by": updated_by,
                "version": page.get("version", {}).get("number", 1),
                "type": page.get("type", "page"),
                "labels": [
                    label.get("name")
                    for label in page.get("metadata", {})
                    .get("labels", {})
                    .get("results", [])
                ],
            }

            # 创建页面对象
            return ConfluencePage(
                page_id=page_id,
                title=title,
                content=content,
                url=url,
                space_name=space_name,
                author=created_by,
                created_at=created_at,
                updated_at=updated_at,
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"提取页面信息失败: {e}")
            return None

    def crawl_space(self, space_key: str) -> int:
        """爬取指定空间的所有页面"""
        logger.info(f"开始爬取空间: {space_key}")

        # 获取空间页面
        pages = self.get_pages_in_space(space_key)

        # 处理每个页面
        processed_count = 0
        for page in pages:
            confluence_page = self.extract_page_info(page)
            if confluence_page:
                # 保存页面
                self.kb.save_page(confluence_page)
                processed_count += 1
                logger.debug(
                    f"✅ 已保存页面: {confluence_page.title} (ID: {confluence_page.page_id})"
                )

            # 添加延迟避免请求过于频繁
            time.sleep(1)

        logger.success(f"空间 {space_key} 爬取完成，共保存 {processed_count} 个页面")
        return processed_count

    def crawl_all_spaces(self) -> int:
        """爬取所有配置的空间"""
        spaces_to_crawl = confluence_config.spaces

        # 如果没有配置空间，则爬取所有空间
        if not spaces_to_crawl:
            spaces = self.get_all_spaces()
            spaces_to_crawl = [space.get("key") for space in spaces]

        logger.info(f"开始爬取 {len(spaces_to_crawl)} 个空间")

        total_count = 0
        for space_key in spaces_to_crawl:
            total_count += self.crawl_space(space_key)

        logger.success(f"所有空间爬取完成，共保存 {total_count} 个页面")
        return total_count


if __name__ == "__main__":
    """主函数，用于直接运行爬虫"""
    try:
        crawler = ConfluenceCrawler()

        # 获取所有空间
        logger.info("获取所有空间列表...")
        spaces = crawler.get_all_spaces()
        if spaces:
            logger.info(f"发现 {len(spaces)} 个空间:")
            for space in spaces[:10]:  # 只显示前10个空间
                logger.info(f"  - {space.get('name')} (key: {space.get('key')})")
            if len(spaces) > 10:
                logger.info(f"  ... 还有 {len(spaces) - 10} 个空间")

        # 开始爬取
        logger.info("\n开始爬取Confluence页面...")
        total_pages = crawler.crawl_all_spaces()
        logger.success(f"\n✅ 爬虫任务完成！总共采集了 {total_pages} 个页面")

    except Exception as e:
        logger.error(f"\n❌ 爬虫执行失败: {e}")
        import sys

        sys.exit(1)
