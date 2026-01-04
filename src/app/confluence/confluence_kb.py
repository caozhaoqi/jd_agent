import os
import json
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from utils.logger import logger


class ConfluencePage:
    """Confluence页面数据模型"""

    def __init__(
        self,
        page_id: str,
        title: str,
        content: str,
        url: str,
        space_name: str,
        author: str,
        created_at: str,
        updated_at: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.page_id = page_id
        self.title = title
        self.content = content
        self.url = url
        self.space_name = space_name
        self.author = author
        self.created_at = created_at
        self.updated_at = updated_at
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "page_id": self.page_id,
            "title": self.title,
            "content": self.content,
            "url": self.url,
            "space_name": self.space_name,
            "author": self.author,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    def to_document(self) -> Document:
        """转换为LangChain Document格式，用于向量存储"""
        text_content = f"页面标题: {self.title}\n空间名称: {self.space_name}\n内容:\n{self.content}"
        metadata = {
            "source": self.url,
            "title": self.title,
            "page_id": self.page_id,
            "space_name": self.space_name,
            "author": self.author,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            **self.metadata,
        }
        return Document(page_content=text_content, metadata=metadata)


class ConfluenceKnowledgeBase:
    """Confluence知识库管理类"""

    def __init__(self, data_dir: str = "./confluence_data"):
        self.data_dir = data_dir
        self.pages_file = os.path.join(data_dir, "confluence_pages.json")
        self._ensure_dir()

    def _ensure_dir(self):
        """确保数据目录存在"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def save_page(self, page: ConfluencePage) -> None:
        """保存单个页面"""
        pages = self.load_all_pages()
        pages.append(page.to_dict())
        self._save_to_file(pages)

    def save_pages(self, pages: List[ConfluencePage]) -> None:
        """保存多个页面"""
        existing_pages = self.load_all_pages()
        new_pages = [page.to_dict() for page in pages]
        existing_pages.extend(new_pages)
        self._save_to_file(existing_pages)

    def load_all_pages(self) -> List[Dict[str, Any]]:
        """加载所有保存的页面"""
        if not os.path.exists(self.pages_file):
            return []

        try:
            with open(self.pages_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载Confluence页面数据失败: {e}")
            return []

    def _save_to_file(self, pages: List[Dict[str, Any]]) -> None:
        """保存页面数据到文件"""
        try:
            with open(self.pages_file, "w", encoding="utf-8") as f:
                json.dump(pages, f, ensure_ascii=False, indent=2)
            logger.info(f"已保存 {len(pages)} 个Confluence页面到 {self.pages_file}")
        except Exception as e:
            logger.error(f"保存Confluence页面数据失败: {e}")

    def get_pages_by_space(self, space_name: str) -> List[Dict[str, Any]]:
        """根据空间名称获取页面"""
        all_pages = self.load_all_pages()
        return [page for page in all_pages if page["space_name"] == space_name]

    def get_page_by_id(self, page_id: str) -> Optional[Dict[str, Any]]:
        """根据页面ID获取页面"""
        all_pages = self.load_all_pages()
        for page in all_pages:
            if page["page_id"] == page_id:
                return page
        return None

    def search_pages(self, keywords: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """根据关键词或自然语言查询搜索页面"""
        all_pages = self.load_all_pages()
        results = []

        # 预处理查询文本
        import re

        # 移除标点符号
        query = re.sub(r"[\s\W]+", " ", keywords.lower())
        # 拆分为关键词列表
        keyword_list = [k.strip() for k in query.split() if k.strip()]

        # 如果没有关键词，返回空结果
        if not keyword_list:
            return []

        for page in all_pages:
            # 计算页面与关键词的匹配度
            title = page.get("title", "").lower()
            content = page.get("content", "").lower()

            # 移除HTML标签
            clean_content = re.sub(r"<[^>]*>", " ", content)

            # 统计匹配的关键词数量
            title_matches = sum(1 for k in keyword_list if k in title)
            content_matches = sum(1 for k in keyword_list if k in clean_content)

            # 计算总匹配度（标题匹配权重更高）
            score = title_matches * 2 + content_matches

            if score > 0:
                page_with_score = page.copy()
                page_with_score["_score"] = score
                results.append(page_with_score)

        # 按匹配度排序并返回前top_k个结果
        results.sort(key=lambda x: x["_score"], reverse=True)
        return results[:top_k]

    def get_answer(self, question: str, top_k: int = 3) -> str:
        """根据问题从知识库中获取答案"""
        # 搜索相关页面
        relevant_pages = self.search_pages(question, top_k)

        if not relevant_pages:
            return "抱歉，知识库中没有找到与您的问题相关的信息。"

        # 构建答案
        answer = f"根据知识库查询结果，找到以下与 '{question}' 相关的信息：\n\n"

        for i, page in enumerate(relevant_pages, 1):
            answer += f"{i}. [{page['title']}]({page['url']})\n"

            # 从内容中提取关键信息
            content = page["content"]
            # 移除HTML标签和多余空格
            import re

            clean_content = re.sub(r"<[^>]*>", " ", content)
            clean_content = re.sub(r"\s+", " ", clean_content).strip()

            # 截取前200个字符作为摘要
            if len(clean_content) > 200:
                clean_content = clean_content[:200] + "..."

            answer += f"   摘要：{clean_content}\n\n"

        answer += "如果需要更详细的信息，请访问相关页面。"
        return answer
