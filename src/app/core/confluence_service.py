import time
from typing import List, Dict, Any, Optional
from atlassian import Confluence
from loguru import logger
from retry import retry

from core.config import settings


class ConfluenceService:
    """
    Confluence服务类，提供Confluence页面的读取和提取功能
    """

    def __init__(self):
        """
        初始化Confluence连接
        """
        self.confluence = None
        self._connect()

    def _connect(self):
        """
        建立与Confluence服务器的连接
        """
        if (
            not settings.CONFLUENCE_URL
            or not settings.CONFLUENCE_USERNAME
            or not settings.CONFLUENCE_PASSWORD
        ):
            logger.warning("⚠️ [Confluence] 配置不完整，跳过连接")
            return

        try:
            self.confluence = Confluence(
                url=settings.CONFLUENCE_URL,
                username=settings.CONFLUENCE_USERNAME,
                password=settings.CONFLUENCE_PASSWORD,
                verify_ssl=True,  # 生产环境建议启用SSL验证
            )

            # 测试连接
            self.confluence.get_server_info()
            logger.info(f"✅ [Confluence] 成功连接到 {settings.CONFLUENCE_URL}")
        except Exception as e:
            logger.error(f"❌ [Confluence] 连接失败: {str(e)}")
            self.confluence = None

    @retry(tries=settings.CONFLUENCE_MAX_RETRIES, delay=1, backoff=2, logger=logger)
    def get_space_pages(
        self, space_key: str, expand: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取指定空间的所有页面

        Args:
            space_key: Confluence空间的key
            expand: 要扩展的字段列表，如['body.view', 'version', 'ancestors']

        Returns:
            页面列表，每个页面包含基本信息和指定的扩展字段
        """
        if not self.confluence:
            logger.error("❌ [Confluence] 未连接到服务器")
            return []

        try:
            pages = []
            start = 0
            limit = settings.CONFLUENCE_PAGE_SIZE

            while True:
                logger.debug(
                    f"🔍 [Confluence] 获取空间 {space_key} 的页面，起始位置: {start}"
                )
                response = self.confluence.get_all_pages_from_space(
                    space=space_key, start=start, limit=limit, expand=expand
                )

                if not response:
                    break

                pages.extend(response)

                if len(response) < limit:
                    break

                start += limit
                time.sleep(0.5)  # 避免请求过快

            logger.info(
                f"📄 [Confluence] 从空间 {space_key} 获取到 {len(pages)} 个页面"
            )
            return pages

        except Exception as e:
            logger.error(f"❌ [Confluence] 获取空间 {space_key} 的页面失败: {str(e)}")
            return []

    @retry(tries=settings.CONFLUENCE_MAX_RETRIES, delay=1, backoff=2, logger=logger)
    def get_page_content(
        self, page_id: str, expand: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取指定页面的详细内容

        Args:
            page_id: 页面的ID
            expand: 要扩展的字段列表，如['body.view', 'body.storage', 'version', 'ancestors']

        Returns:
            页面详细信息，如果失败返回None
        """
        if not self.confluence:
            logger.error("❌ [Confluence] 未连接到服务器")
            return None

        try:
            page = self.confluence.get_page_by_id(
                page_id=page_id, expand=expand or ["body.view"]
            )
            return page
        except Exception as e:
            logger.error(f"❌ [Confluence] 获取页面 {page_id} 的内容失败: {str(e)}")
            return None

    @retry(tries=settings.CONFLUENCE_MAX_RETRIES, delay=1, backoff=2, logger=logger)
    def get_page_by_title(
        self, space_key: str, title: str, expand: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        根据标题获取页面

        Args:
            space_key: 空间key
            title: 页面标题
            expand: 要扩展的字段列表

        Returns:
            页面详细信息，如果失败返回None
        """
        if not self.confluence:
            logger.error("❌ [Confluence] 未连接到服务器")
            return None

        try:
            page = self.confluence.get_page_by_title(
                space=space_key, title=title, expand=expand or ["body.view"]
            )
            return page
        except Exception as e:
            logger.error(f"❌ [Confluence] 获取页面 '{title}' 失败: {str(e)}")
            return None

    def get_pages_by_label(
        self, label: str, space_key: str = None, expand: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        根据标签获取页面

        Args:
            label: 标签名称
            space_key: 可选，指定空间
            expand: 要扩展的字段列表

        Returns:
            页面列表
        """
        if not self.confluence:
            logger.error("❌ [Confluence] 未连接到服务器")
            return []

        try:
            pages = self.confluence.get_all_pages_by_label(
                label=label, space=space_key, expand=expand or ["body.view"]
            )
            logger.info(
                f"📄 [Confluence] 获取到 {len(pages)} 个带有标签 '{label}' 的页面"
            )
            return pages
        except Exception as e:
            logger.error(f"❌ [Confluence] 获取带标签 '{label}' 的页面失败: {str(e)}")
            return []

    def extract_page_text(self, page: Dict[str, Any]) -> str:
        """
        从页面对象中提取纯文本内容

        Args:
            page: 包含页面内容的字典

        Returns:
            提取的纯文本
        """
        try:
            # 优先使用存储格式（更结构化）
            if "body" in page and "storage" in page["body"]:
                return page["body"]["storage"]["value"]

            # 否则使用视图格式
            if "body" in page and "view" in page["body"]:
                return page["body"]["view"]["value"]

            logger.warning("⚠️ [Confluence] 页面内容格式不支持")
            return ""
        except Exception as e:
            logger.error(f"❌ [Confluence] 提取页面文本失败: {str(e)}")
            return ""


# 实例化Confluence服务
def get_confluence_service() -> ConfluenceService:
    """
    获取Confluence服务实例

    Returns:
        ConfluenceService实例
    """
    return ConfluenceService()


confluence_service = get_confluence_service()
