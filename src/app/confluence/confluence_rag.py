import os
import torch
from typing import List, Dict, Any, Union
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from app.utils.logger import logger

# 设置HuggingFace国内镜像
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# 确定向量库路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR)))
DB_PATH = os.path.join(PROJECT_ROOT, "confluence_faiss_index")


class ConfluenceKnowledgeBase:
    """Confluence Wiki知识库类，使用单例模式"""
    _instance = None

    def __new__(cls):
        """单例模式：确保全局只有一个知识库实例"""
        if cls._instance is None:
            cls._instance = super(ConfluenceKnowledgeBase, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """初始化加载模型和向量库"""
        logger.info("📚 [Confluence KB] Initializing Knowledge Base...")
        try:
            # 1. 自动检测最佳硬件设备 (MPS > CUDA > CPU)
            if torch.backends.mps.is_available():
                # 适配 macOS M系列芯片
                device = "mps"
                logger.info("🚀 [Confluence KB] Using Apple Metal (MPS) acceleration!")
            elif torch.cuda.is_available():
                # 适配 NVIDIA 显卡
                device = "cuda"
                logger.info("🚀 [Confluence KB] Using CUDA acceleration!")
            else:
                # 兜底 CPU
                device = "cpu"
                logger.info("🐢 [Confluence KB] No GPU detected. Using CPU.")

            # 2. 初始化 Embedding 模型
            self.embeddings = HuggingFaceEmbeddings(
                model_name="BAAI/bge-small-zh-v1.5",
                model_kwargs={'device': device},
                encode_kwargs={'normalize_embeddings': True}
            )

            # 3. 加载 FAISS 向量库
            if os.path.exists(DB_PATH):
                self.vector_store = FAISS.load_local(
                    DB_PATH,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                logger.success(f"✅ [Confluence KB] Vector Store loaded successfully from: {DB_PATH}")
            else:
                logger.warning(f"⚠️ [Confluence KB] Index not found at {DB_PATH}. Knowledge base functionality disabled.")
                self.vector_store = None

        except Exception as e:
            logger.error(f"❌ [Confluence KB] Initialization failed: {e}")
            self.vector_store = None

    def search(self, query: str, top_k: int = 3) -> Dict[str, Union[str, List[Dict[str, Any]]]]:
        """
        检索相关文档
        
        Args:
            query: 查询字符串
            top_k: 返回结果数量
            
        Returns:
            包含上下文和来源链接的字典
        """
        if not self.vector_store:
            return {"context": "", "sources": []}

        try:
            # 搜索相关文档
            logger.debug(f"🔍 [Confluence KB] Searching for: {query}")
            docs = self.vector_store.similarity_search(query, k=top_k)

            if not docs:
                return {"context": "", "sources": []}

            # 拼接内容
            context_parts = []
            sources = []

            for doc in docs:
                # 获取元数据
                source = doc.metadata.get("source", "未知来源")
                title = doc.metadata.get("title", "未知标题")
                page_id = doc.metadata.get("page_id", "未知ID")
                space_name = doc.metadata.get("space_name", "未知空间")
                
                # 记录来源
                sources.append({
                    "title": title,
                    "url": source,
                    "page_id": page_id,
                    "space_name": space_name
                })
                
                # 格式化文档内容
                context_parts.append(f"---[页面: {title} (来自: {space_name})]---\n{doc.page_content}")

            return {
                "context": "\n\n".join(context_parts),
                "sources": sources
            }
        except Exception as e:
            logger.error(f"❌ [Confluence KB] Search failed: {e}")
            return {"context": "", "sources": []}


# 导出单例实例
confluence_kb_engine = ConfluenceKnowledgeBase()
