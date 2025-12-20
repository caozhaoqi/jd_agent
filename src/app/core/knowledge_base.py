import os
import torch
from typing import List, Dict, Any, Union, Coroutine
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from app.utils.logger import logger

# 1. 确定向量库路径
# 逻辑：当前文件 -> 上级(core) -> 上级(app) -> 上级(src) -> 项目根目录 -> blog_faiss_index
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR)))
DB_PATH = os.path.join(PROJECT_ROOT, "blog_faiss_index")


class BlogKnowledgeBase:
    _instance = None

    def __new__(cls):
        """单例模式：确保全局只有一个知识库实例，避免重复加载模型占用内存"""
        if cls._instance is None:
            cls._instance = super(BlogKnowledgeBase, cls).__new__(cls)
            # 延迟初始化：不在创建实例时立即初始化模型
            cls._instance._initialized = False
            cls._instance.vector_store = None
            cls._instance.embeddings = None
        return cls._instance

    def _initialize(self):
        """初始化加载模型和向量库"""
        if self._initialized:
            return
            
        logger.info("📚 [KB] Initializing Blog Knowledge Base...")
        try:
            # 2. 自动检测最佳硬件设备 (MPS > CUDA > CPU)
            if torch.backends.mps.is_available():
                # 适配 macOS M系列芯片 (M1/M2/M3/M4)
                device = "mps"
                logger.info("🚀 [KB] Using Apple Metal (MPS) acceleration!")
            elif torch.cuda.is_available():
                # 适配 NVIDIA 显卡
                device = "cuda"
                logger.info("🚀 [KB] Using CUDA acceleration!")
            else:
                # 兜底 CPU
                device = "cpu"
                logger.info("🐢 [KB] No GPU detected. Using CPU.")

            # 3. 初始化 Embedding 模型
            # 设置 HF 镜像，防止国内网络下载模型超时
            os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

            self.embeddings = HuggingFaceEmbeddings(
                model_name="BAAI/bge-small-zh-v1.5",
                # 关键修改：将 device 设置为检测到的硬件，而不是写死 'cpu'
                model_kwargs={"device": device},
                encode_kwargs={"normalize_embeddings": True},
            )

            # 4. 加载 FAISS 向量库
            if os.path.exists(DB_PATH):
                self.vector_store = FAISS.load_local(
                    DB_PATH, self.embeddings, allow_dangerous_deserialization=True
                )
                logger.success(
                    f"✅ [KB] Vector Store loaded successfully from: {DB_PATH}"
                )
            else:
                logger.warning(
                    f"⚠️ [KB] Index not found at {DB_PATH}. RAG functionality disabled."
                )
                self.vector_store = None

            self._initialized = True
        except Exception as e:
            logger.error(f"❌ [KB] Init failed: {e}")
            self.vector_store = None
            self._initialized = True  # 即使失败也标记为已初始化，避免重复尝试

    async def search(
        self, query: str, top_k: int = 3
    ) -> dict[str, Union[str, list[Any]]]:
        """
        检索相关文档
        返回格式: {"context": "拼接好的文档内容...", "sources": ["文章A.md", "文章B.md"]}
        """
        # 在首次使用时初始化模型
        self._initialize()
        
        if not self.vector_store:
            return {"context": "", "sources": []}

        try:
            # 异步执行搜索
            # 注意：FAISS 索引搜索是在 CPU 上进行的，但在 Web 服务中非常快
            # Embedding 的生成（将 query 转为向量）会使用上面配置的 device (MPS/GPU)
            docs = self.vector_store.similarity_search(query, k=top_k)

            if not docs:
                return {"context": "", "sources": []}

            # 拼接内容
            context_parts = []
            sources = set()

            for doc in docs:
                # 获取元数据中的来源文件名，默认为"未知来源"
                source = doc.metadata.get("source", "未知来源")
                sources.add(source)
                # 格式化文档内容
                context_parts.append(f"---[引用自: {source}]---\n{doc.page_content}")

            return {"context": "\n\n".join(context_parts), "sources": list(sources)}
        except Exception as e:
            logger.error(f"❌ [KB] Search failed: {e}")
            return {"context": "", "sources": []}


# 导出单例实例
kb_engine = BlogKnowledgeBase()
