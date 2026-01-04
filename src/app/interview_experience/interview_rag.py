import os
import json
import time

# 设置 HuggingFace 国内镜像
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
from typing import List, Dict, Any, Optional
from langchain.docstore.document import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS, Chroma
from utils.logger import logger
from interview_experience.nowcoder_crawler import NowCoderCrawler
from interview_experience.maimai_crawler import MaimaiCrawler


class InterviewExperienceRAG:
    """面试经验RAG系统"""

    def __init__(self, vector_store_path: str = None):
        """
        初始化面试经验RAG系统
        vector_store_path: 向量数据库存储路径
        """
        if vector_store_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            self.vector_store_path = os.path.join(project_root, "src/app/interview_experience/faiss_index")
        else:
            self.vector_store_path = vector_store_path
        
        # 初始化爬虫
        self.nowcoder_crawler = NowCoderCrawler()
        self.maimai_crawler = MaimaiCrawler()
        
        # 初始化嵌入模型 - 使用与blog模块相同的本地模型，避免网络问题
        self.embeddings = HuggingFaceEmbeddings(
            model_name="shibing624/text2vec-base-chinese",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        
        # 加载向量数据库
        self.vector_store = None
        self._load_vector_store()

    def _load_vector_store(self):
        """加载向量数据库"""
        try:
            if os.path.exists(self.vector_store_path):
                self.vector_store = FAISS.load_local(
                    self.vector_store_path,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                logger.success(f"✅ 成功加载面试经验向量数据库: {self.vector_store_path}")
            else:
                logger.warning(f"⚠️ 面试经验向量数据库不存在: {self.vector_store_path}")
        except Exception as e:
            logger.error(f"❌ 加载面试经验向量数据库失败: {e}")

    def crawl_nowcoder(self, start_page: int = 1, end_page: int = 10, order_type: int = 3) -> List[Dict[str, Any]]:
        """爬取牛客面经"""
        return self.nowcoder_crawler.crawl(start_page, end_page, order_type)

    def crawl_maimai(self, keyword: str = "面试经验", start_page: int = 1, end_page: int = 10) -> List[Dict[str, Any]]:
        """爬取脉脉面经"""
        return self.maimai_crawler.crawl(keyword, start_page, end_page)

    def crawl_all(self, start_page: int = 1, end_page: int = 10) -> List[Dict[str, Any]]:
        """爬取所有平台面经"""
        logger.info("开始爬取所有平台面经...")
        
        # 爬取牛客面经
        nowcoder_interviews = self.crawl_nowcoder(start_page, end_page)
        
        # 爬取脉脉面经
        maimai_interviews = self.crawl_maimai(start_page=start_page, end_page=end_page)
        
        # 合并结果
        all_interviews = nowcoder_interviews + maimai_interviews
        logger.success(f"所有平台面经爬取完成，共获取 {len(all_interviews)} 条面经")
        
        return all_interviews

    def save_raw_data(self, interviews: List[Dict[str, Any]], filename: str = None) -> str:
        """保存原始面经数据"""
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"interview_data_{timestamp}.json"
        
        data_dir = os.path.join(os.path.dirname(self.vector_store_path), "raw_data")
        os.makedirs(data_dir, exist_ok=True)
        
        file_path = os.path.join(data_dir, filename)
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(interviews, f, ensure_ascii=False, indent=2)
            logger.success(f"✅ 原始面经数据保存成功: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"❌ 保存原始面经数据失败: {e}")
            return ""

    def load_raw_data(self, file_path: str) -> List[Dict[str, Any]]:
        """加载原始面经数据"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                interviews = json.load(f)
            logger.success(f"✅ 原始面经数据加载成功: {file_path}")
            return interviews
        except Exception as e:
            logger.error(f"❌ 加载原始面经数据失败: {e}")
            return []

    def interviews_to_documents(self, interviews: List[Dict[str, Any]]) -> List[Document]:
        """将面经数据转换为LangChain Document对象"""
        documents = []
        
        for interview in interviews:
            try:
                # 构建文档内容
                content = []
                if interview.get("title"):
                    content.append(f"# {interview['title']}")
                if interview.get("company"):
                    content.append(f"**公司**: {interview['company']}")
                if interview.get("position"):
                    content.append(f"**职位**: {interview['position']}")
                if interview.get("content"):
                    content.append(f"\n**面经内容**:\n{interview['content']}")
                else:
                    continue  # 没有内容的面经跳过
                
                # 构建元数据
                metadata = {
                    "source": interview.get("url", "未知来源"),
                    "platform": "牛客网" if "nowcoder" in interview.get("url", "").lower() else "脉脉",
                    "company": interview.get("company", ""),
                    "position": interview.get("position", ""),
                    "author": interview.get("author", ""),
                    "publish_time": interview.get("publish_time", ""),
                    "likes": interview.get("likes", 0),
                    "replies": interview.get("replies", 0),
                    "tags": interview.get("tags", [])
                }
                
                # 创建Document对象
                document = Document(
                    page_content="\n".join(content),
                    metadata=metadata
                )
                
                documents.append(document)
            except Exception as e:
                logger.error(f"❌ 转换面经为Document失败: {e}")
                continue
        
        logger.info(f"成功将 {len(documents)} 条面经转换为Document对象")
        return documents

    def update_vector_store(self, interviews: List[Dict[str, Any]]) -> bool:
        """更新向量数据库"""
        try:
            # 转换为Document对象
            documents = self.interviews_to_documents(interviews)
            if not documents:
                logger.warning("⚠️ 没有可更新的文档")
                return False
            
            # 构建或更新向量数据库
            if self.vector_store is None:
                # 首次构建
                self.vector_store = FAISS.from_documents(documents, self.embeddings)
                logger.success("✅ 首次构建面试经验向量数据库")
            else:
                # 更新现有数据库
                self.vector_store.add_documents(documents)
                logger.success(f"✅ 更新面试经验向量数据库，新增 {len(documents)} 个文档")
            
            # 保存向量数据库
            self.vector_store.save_local(self.vector_store_path)
            logger.success(f"✅ 面试经验向量数据库保存成功: {self.vector_store_path}")
            
            return True
        except Exception as e:
            logger.error(f"❌ 更新面试经验向量数据库失败: {e}")
            return False

    def search(self, query: str, top_k: int = 3) -> dict[str, Any]:
        """
        检索相关面经
        返回格式: {"context": "拼接好的面经内容...", "sources": ["https://...", "https://..."]}
        """
        try:
            if not self.vector_store:
                logger.warning("⚠️ 向量数据库未初始化，检索功能不可用")
                return {"context": "", "sources": []}
            
            # 执行检索
            docs = self.vector_store.similarity_search(query, k=top_k)
            
            if not docs:
                return {"context": "", "sources": []}
            
            # 拼接内容和提取来源
            context_parts = []
            sources = []
            
            for doc in docs:
                context_parts.append(doc.page_content)
                sources.append(doc.metadata.get("source", "未知来源"))
            
            return {
                "context": "\n\n---\n\n".join(context_parts),
                "sources": sources
            }
        except Exception as e:
            logger.error(f"❌ 检索面试经验失败: {e}")
            return {"context": "", "sources": []}

    def build_knowledge_base(self, start_page: int = 1, end_page: int = 10, save_raw: bool = True) -> bool:
        """构建面试经验知识库"""
        try:
            logger.info("开始构建面试经验知识库...")
            
            # 爬取面经
            interviews = self.crawl_all(start_page, end_page)
            if not interviews:
                logger.warning("⚠️ 未爬取到任何面经")
                return False
            
            # 保存原始数据
            if save_raw:
                self.save_raw_data(interviews)
            
            # 更新向量数据库
            return self.update_vector_store(interviews)
        except Exception as e:
            logger.error(f"❌ 构建面试经验知识库失败: {e}")
            return False


if __name__ == "__main__":
    """测试面试经验RAG系统"""
    # 初始化RAG系统
    interview_rag = InterviewExperienceRAG()
    
    # 测试爬取（小范围）
    logger.info("测试爬取牛客面经...")
    nowcoder_interviews = interview_rag.crawl_nowcoder(start_page=1, end_page=1, order_type=3)
    
    # 测试构建知识库
    logger.info("测试构建知识库...")
    interview_rag.build_knowledge_base(start_page=1, end_page=1, save_raw=True)
    
    # 测试检索
    logger.info("测试检索功能...")
    result = interview_rag.search("Python面试经验", top_k=3)
    logger.info(f"检索结果来源: {result['sources']}")
    if result['context']:
        logger.info(f"上下文内容: {result['context'][:300]}...")
    else:
        logger.info("没有找到相关面经")
