import os
import sys

# 🚀 【核心修复】设置 HuggingFace 国内镜像 (必须放在最前面)
# 这会让下载速度飞起，解决卡住的问题
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

import json
import shutil
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv
from loguru import logger

# 配置日志输出到控制台 (防止日志被缓存看不到)
logger.remove()
logger.add(sys.stderr, level="DEBUG")

load_dotenv()

DATA_DIR = "data"
DB_DIR = "chroma_db"

def build_knowledge_base():
    if os.path.exists(DB_DIR):
        shutil.rmtree(DB_DIR)

    JSON_PATH = "/Users/caozhaoqi/PycharmProjects/JD_agent/src/app/blog/blog_data.json"

    logger.debug("正在加载博客数据...")
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        blog_posts = json.load(f)

    docs = []
    for post in blog_posts:
        text_content = f"文章标题: {post['title']}\n标签: {post['tags']}\n内容:\n{post['content']}"
        metadata = {
            "source": post['source'],
            "title": post['title'],
            "date": post['date']
        }
        docs.append(Document(page_content=text_content, metadata=metadata))

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )
    splits = text_splitter.split_documents(docs)
    logger.debug(f"切分为 {len(splits)} 个片段。")

    # 4. 向量化
    logger.debug("⏳ 正在初始化 Embedding 模型 (首次运行会自动下载)...")

    # 强制指定 device='cpu' (Mac 上有时自动检测 mps 会卡住，先用 cpu 跑通最稳)
    embedding_model = HuggingFaceEmbeddings(
        model_name="shibing624/text2vec-base-chinese",
        model_kwargs={'device': 'cpu'}
    )

    logger.debug("🚀 正在写入向量数据库 (Chroma)...")
    Chroma.from_documents(
        documents=splits,
        embedding=embedding_model,
        persist_directory=DB_DIR
    )
    logger.success("✅ 知识库构建完成！")

if __name__ == "__main__":
    build_knowledge_base()