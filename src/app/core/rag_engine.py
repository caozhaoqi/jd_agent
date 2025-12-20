import os
from typing import List
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from loguru import logger

VECTOR_DB_PATH = "faiss_index"


class RAGEngine:
    def __init__(self):
        self.vector_store = None
        self.embedding_model = None
        self._initialized = False

    def _initialize(self):
        """初始化模型和向量库"""
        if self._initialized:
            return
            
        logger.info("📚 [RAG] Initializing RAG Engine...")
        try:
            # 设置 HF 镜像
            os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
            
            # 初始化 Embedding 模型
            self.embedding_model = HuggingFaceEmbeddings(
                model_name="BAAI/bge-small-zh-v1.5",
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
            
            # 加载向量库
            if os.path.exists(VECTOR_DB_PATH):
                self.vector_store = FAISS.load_local(
                    VECTOR_DB_PATH, self.embedding_model, allow_dangerous_deserialization=True
                )
                logger.success(f"✅ [RAG] Vector Store loaded successfully from: {VECTOR_DB_PATH}")
            
            self._initialized = True
        except Exception as e:
            logger.error(f"❌ [RAG] Init failed: {e}")
            self._initialized = True  # 即使失败也标记为已初始化，避免重复尝试

    def ingest_knowledge(self, text_content: str, source_name: str):
        """
        数据入库流程 (JD要求: 清洗、分词、向量化)
        """
        # 初始化模型
        self._initialize()
        
        # 1. 文本清洗 (简单的去除空行)
        clean_text = "\n".join(
            [line for line in text_content.split("\n") if line.strip()]
        )

        # 2. 分词/切片 (Chunking)
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500, chunk_overlap=50  # 每块 500 字  # 重叠 50 字，保持上下文
        )
        docs = splitter.create_documents(
            [clean_text], metadatas=[{"source": source_name}]
        )

        # 3. 向量化并存入 FAISS
        if self.vector_store:
            self.vector_store.add_documents(docs)
        else:
            self.vector_store = FAISS.from_documents(docs, self.embedding_model)

        # 4. 持久化保存
        self.vector_store.save_local(VECTOR_DB_PATH)
        logger.debug(f"✅ 已将 {len(docs)} 个片段存入向量库")

    def search(self, query: str, top_k: int = 3) -> List[str]:
        # 🟢 修改这里：返回值不仅包含文本，还包含来源 metadata
        """
        检索并返回内容和元数据
        """
        # 初始化模型
        self._initialize()
        
        if not self.vector_store:
            return []

        # 相似度搜索
        docs_and_scores = self.vector_store.similarity_search_with_score(query, k=top_k)

        results = []
        for doc, score in docs_and_scores:
            results.append(
                {
                    "content": doc.page_content,
                    "source": doc.metadata.get("source", "未知来源"),  # 获取文件名
                    "score": score,
                }
            )

        return results


# 单例
rag_engine = RAGEngine()
