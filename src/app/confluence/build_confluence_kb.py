import os
import sys

# 设置HuggingFace国内镜像
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import json
from typing import List
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from app.utils.logger import logger
from app.confluence.confluence_kb import ConfluenceKnowledgeBase

# 配置路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR)))

# 数据目录和索引目录
DATA_DIR = os.path.join(PROJECT_ROOT, "confluence_data")
INDEX_DIR = os.path.join(PROJECT_ROOT, "confluence_faiss_index")


def build_confluence_knowledge_base():
    """构建Confluence Wiki知识库向量索引"""
    logger.info("🚀 开始构建Confluence Wiki知识库...")

    # 1. 加载保存的页面数据
    logger.info("📄 正在加载Confluence页面数据...")
    kb = ConfluenceKnowledgeBase(data_dir=DATA_DIR)
    pages = kb.load_all_pages()

    if not pages:
        logger.error("❌ 没有找到Confluence页面数据，请先运行爬虫采集数据")
        return

    logger.info(f"✅ 成功加载 {len(pages)} 个页面数据")

    # 2. 转换为LangChain Document格式
    logger.info("🔄 正在转换页面数据为文档格式...")
    documents = []
    for page in pages:
        text_content = f"页面标题: {page['title']}\n空间名称: {page['space_name']}\n内容:\n{page['content']}"
        metadata = {
            "source": page["url"],
            "title": page["title"],
            "page_id": page["page_id"],
            "space_name": page["space_name"],
            "author": page["author"],
            "created_at": page["created_at"],
            "updated_at": page["updated_at"],
            **page["metadata"],
        }
        documents.append(Document(page_content=text_content, metadata=metadata))

    # 3. 文本分割
    logger.info("✂️  正在分割文档内容...")
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )
    splits = text_splitter.split_documents(documents)

    logger.info(f"✅ 将 {len(documents)} 个文档分割为 {len(splits)} 个片段")

    # 4. 初始化Embedding模型
    logger.info("🧠 正在初始化Embedding模型...")

    # 使用BGE-small-zh-v1.5模型
    embedding_model = HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-zh-v1.5",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    # 5. 创建向量索引
    logger.info("📊 正在创建向量索引...")

    # 创建FAISS向量存储
    vector_store = FAISS.from_documents(documents=splits, embedding=embedding_model)

    # 保存索引
    vector_store.save_local(INDEX_DIR)

    logger.success(f"✅ Confluence Wiki知识库构建完成！")
    logger.info(f"📁 索引文件保存在: {INDEX_DIR}")
    logger.info(f"📚 共包含 {len(splits)} 个文档片段")


if __name__ == "__main__":
    build_confluence_knowledge_base()
