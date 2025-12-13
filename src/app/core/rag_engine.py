import os
from typing import List
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.vectorstores import FAISS
from loguru import logger

# 1. 定义向量模型 (JD要求: BGE)
# 第一次运行会自动从 HuggingFace 下载模型，约 100MB
embedding_model = HuggingFaceBgeEmbeddings(
    model_name="BAAI/bge-small-zh-v1.5",
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)

VECTOR_DB_PATH = "faiss_index"


class RAGEngine:
    def __init__(self):
        self.vector_store = None
        self._load_existing_index()

    def _load_existing_index(self):
        """尝试加载本地已保存的向量库"""
        if os.path.exists(VECTOR_DB_PATH):
            self.vector_store = FAISS.load_local(
                VECTOR_DB_PATH,
                embedding_model,
                allow_dangerous_deserialization=True
            )

    def ingest_knowledge(self, text_content: str, source_name: str):
        """
        数据入库流程 (JD要求: 清洗、分词、向量化)
        """
        # 1. 文本清洗 (简单的去除空行)
        clean_text = "\n".join([line for line in text_content.split('\n') if line.strip()])

        # 2. 分词/切片 (Chunking)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,  # 每块 500 字
            chunk_overlap=50  # 重叠 50 字，保持上下文
        )
        docs = splitter.create_documents([clean_text], metadatas=[{"source": source_name}])

        # 3. 向量化并存入 FAISS
        if self.vector_store:
            self.vector_store.add_documents(docs)
        else:
            self.vector_store = FAISS.from_documents(docs, embedding_model)

        # 4. 持久化保存
        self.vector_store.save_local(VECTOR_DB_PATH)
        logger.debug(f"✅ 已将 {len(docs)} 个片段存入向量库")

    def search(self, query: str, top_k: int = 3) -> List[str]:
        # 🟢 修改这里：返回值不仅包含文本，还包含来源 metadata
        """
        检索并返回内容和元数据
        """
        if not self.vector_store:
            return []

        # 相似度搜索
        docs_and_scores = self.vector_store.similarity_search_with_score(query, k=top_k)

        results = []
        for doc, score in docs_and_scores:
            results.append({
                "content": doc.page_content,
                "source": doc.metadata.get("source", "未知来源"),  # 获取文件名
                "score": score
            })

        return results


# 单例
rag_engine = RAGEngine()
