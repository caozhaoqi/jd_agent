import os
from typing import List, Dict
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from app.utils.logger import logger

# 你的向量库路径 (请确保 build_blog_kb.py 已经运行过并在根目录生成了此文件夹)
# DB_PATH = "blog_faiss_index"
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR)))
DB_PATH = os.path.join(PROJECT_ROOT, "blog_faiss_index")

class BlogKnowledgeBase:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BlogKnowledgeBase, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """初始化加载模型和向量库 (单例模式，只加载一次)"""
        logger.info("📚 [KB] Initializing Blog Knowledge Base...")
        try:
            # 1. 初始化 Embedding (使用国内镜像逻辑)
            os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
            self.embeddings = HuggingFaceEmbeddings(
                model_name="BAAI/bge-small-zh-v1.5",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )

            # 2. 加载 FAISS
            if os.path.exists(DB_PATH):
                self.vector_store = FAISS.load_local(
                    DB_PATH,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                logger.success("✅ [KB] Vector Store loaded successfully.")
            else:
                logger.warning(f"⚠️ [KB] Index not found at {DB_PATH}. RAG disabled.")
                self.vector_store = None
        except Exception as e:
            logger.error(f"❌ [KB] Init failed: {e}")
            self.vector_store = None

    async def search(self, query: str, top_k: int = 3) -> Dict[str, str]:
        """
        检索相关文档
        返回格式: {"context": "文档内容...", "sources": ["文章A.md", "文章B.md"]}
        """
        if not self.vector_store:
            return {"context": "", "sources": []}

        try:
            # 异步执行搜索 (FAISS 本身是 CPU 密集型，但在 Web 服务中很快)
            # 这里简单用同步调用，因为 FAISS 在内存中极快
            docs = self.vector_store.similarity_search(query, k=top_k)

            if not docs:
                return {"context": "", "sources": []}

            # 拼接内容
            context_parts = []
            sources = set()

            for doc in docs:
                source = doc.metadata.get("source", "未知来源")
                sources.add(source)
                context_parts.append(f"---[引用自: {source}]---\n{doc.page_content}")

            return {
                "context": "\n\n".join(context_parts),
                "sources": list(sources)
            }
        except Exception as e:
            logger.error(f"❌ [KB] Search failed: {e}")
            return {"context": "", "sources": []}


# 导出单例
kb_engine = BlogKnowledgeBase()
