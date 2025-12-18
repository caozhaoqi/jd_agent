from bs4 import BeautifulSoup, Comment
from typing import Optional, Dict, Any
import re
from loguru import logger


class ConfluenceContentProcessor:
    """
    Confluence内容处理器，用于清洗和转换HTML内容
    """

    def __init__(self):
        """
        初始化内容处理器
        """
        # 定义要保留的HTML标签
        self.allowed_tags = {
            "p",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "ul",
            "ol",
            "li",
            "strong",
            "b",
            "em",
            "i",
            "code",
            "pre",
            "a",
            "br",
        }

        # 定义要转换的标签映射
        self.tag_mappings = {
            "h1": "# ",
            "h2": "## ",
            "h3": "### ",
            "h4": "#### ",
            "h5": "##### ",
            "h6": "###### ",
            "strong": "**",
            "b": "**",
            "em": "*",
            "i": "*",
            "code": "`",
            "pre": "```\n",
            "ul li": "- ",
            "ol li": "1. ",
        }

    def clean_html(self, html_content: str) -> str:
        """
        清洗HTML内容，去除不必要的标签和属性

        Args:
            html_content: 原始HTML内容

        Returns:
            清洗后的HTML内容
        """
        if not html_content:
            return ""

        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # 移除注释
            for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
                comment.extract()

            # 移除脚本和样式
            for script in soup.find_all(["script", "style"]):
                script.extract()

            # 移除所有属性（除了a标签的href）
            for tag in soup.find_all(True):
                if tag.name == "a" and "href" in tag.attrs:
                    tag.attrs = {"href": tag.attrs["href"]}
                else:
                    tag.attrs = {}

            # 移除不允许的标签
            for tag in soup.find_all(True):
                if tag.name not in self.allowed_tags:
                    tag.unwrap()

            cleaned_html = str(soup)
            # 移除多余的空白
            cleaned_html = re.sub(r"\s+", " ", cleaned_html)
            cleaned_html = re.sub(r">\s+<", "><", cleaned_html)

            return cleaned_html.strip()

        except Exception as e:
            logger.error(f"❌ [ContentProcessor] 清洗HTML失败: {str(e)}")
            return html_content

    def html_to_text(self, html_content: str) -> str:
        """
        将HTML内容转换为纯文本

        Args:
            html_content: 原始HTML内容

        Returns:
            纯文本内容
        """
        if not html_content:
            return ""

        try:
            soup = BeautifulSoup(html_content, "html.parser")
            return soup.get_text(separator="\n", strip=True)
        except Exception as e:
            logger.error(f"❌ [ContentProcessor] HTML转文本失败: {str(e)}")
            return html_content

    def html_to_markdown(self, html_content: str) -> str:
        """
        将HTML内容转换为Markdown格式

        Args:
            html_content: 原始HTML内容

        Returns:
            Markdown格式的内容
        """
        if not html_content:
            return ""

        try:
            cleaned_html = self.clean_html(html_content)
            soup = BeautifulSoup(cleaned_html, "html.parser")

            # 处理标题
            for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
                prefix = self.tag_mappings.get(tag.name, "")
                tag.string = f"{prefix}{tag.get_text()}\n"
                tag.unwrap()

            # 处理列表
            for ul in soup.find_all("ul"):
                for li in ul.find_all("li"):
                    li.string = f"- {li.get_text()}\n"
                ul.unwrap()

            for ol in soup.find_all("ol"):
                items = ol.find_all("li")
                for i, li in enumerate(items, 1):
                    li.string = f"{i}. {li.get_text()}\n"
                ol.unwrap()

            # 处理强调
            for tag in soup.find_all(["strong", "b", "em", "i"]):
                wrap_char = self.tag_mappings.get(tag.name, "")
                tag.string = f"{wrap_char}{tag.get_text()}{wrap_char}"
                tag.unwrap()

            # 处理代码
            for pre in soup.find_all("pre"):
                code = pre.find("code")
                if code:
                    pre.string = f"```\n{code.get_text()}\n```\n"
                else:
                    pre.string = f"```\n{pre.get_text()}\n```\n"
                pre.unwrap()

            for code in soup.find_all("code"):
                if not code.parent.name == "pre":
                    code.string = f"`{code.get_text()}`"
                    code.unwrap()

            # 处理链接
            for a in soup.find_all("a"):
                href = a.get("href", "")
                text = a.get_text()
                a.string = f"[{text}]({href})"
                a.unwrap()

            # 处理段落
            for p in soup.find_all("p"):
                p.string = f"{p.get_text()}\n"
                p.unwrap()

            # 处理换行
            for br in soup.find_all("br"):
                br.string = "\n"
                br.unwrap()

            markdown = soup.get_text()
            # 清理多余的空行
            markdown = re.sub(r"\n\s*\n", "\n\n", markdown)
            markdown = re.sub(r"^\s+|\s+$", "", markdown, flags=re.MULTILINE)

            return markdown

        except Exception as e:
            logger.error(f"❌ [ContentProcessor] HTML转Markdown失败: {str(e)}")
            # 转换失败时返回纯文本
            return self.html_to_text(html_content)

    def process_confluence_page(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理完整的Confluence页面，提取和转换内容

        Args:
            page: Confluence页面对象

        Returns:
            处理后的页面信息，包含原始内容、纯文本和Markdown
        """
        if not page:
            return {}

        try:
            # 提取基本信息
            page_info = {
                "id": page.get("id", ""),
                "title": page.get("title", ""),
                "space_key": page.get("space", {}).get("key", ""),
                "url": page.get("_links", {}).get("webui", ""),
                "version": page.get("version", {}).get("number", 1),
                "created_at": page.get("history", {}).get("createdDate", ""),
                "updated_at": page.get("version", {}).get("when", ""),
                "author": page.get("version", {}).get("by", {}).get("displayName", ""),
            }

            # 提取原始内容
            original_html = ""
            if "body" in page and "storage" in page["body"]:
                original_html = page["body"]["storage"]["value"]
            elif "body" in page and "view" in page["body"]:
                original_html = page["body"]["view"]["value"]

            # 转换内容
            page_info["original_html"] = original_html
            page_info["cleaned_text"] = self.html_to_text(original_html)
            page_info["markdown_content"] = self.html_to_markdown(original_html)

            logger.debug(
                f"📝 [ContentProcessor] 处理页面 '{page_info['title']}'，原始长度: {len(original_html)}，转换后长度: {len(page_info['cleaned_text'])}"
            )

            return page_info

        except Exception as e:
            logger.error(f"❌ [ContentProcessor] 处理页面失败: {str(e)}")
            return {}


# 单例实例
content_processor = ConfluenceContentProcessor()
