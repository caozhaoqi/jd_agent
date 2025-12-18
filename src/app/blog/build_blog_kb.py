import os
import sys

# 🔴 核心修复 1：设置国内镜像加速 (必须放在最前面！)
# 这会让下载速度从 0kb/s 变成 10MB/s
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import glob
from loguru import logger  # 使用我们统一的日志库
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

# 🔴 核心修复 2：使用新版库，消除 DeprecationWarning
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from tqdm import tqdm

# === 配置区域 ===
# 请确认你的博客路径是否正确
BLOG_DIR = "/Users/caozhaoqi/Downloads/hexo-bamboo-blog/source/_posts"
DB_SAVE_PATH = "../../../blog_faiss_index"

# 配置日志格式
logger.remove()
logger.add(
    sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>"
)


def init_embedding_model():
    logger.info("⏳ 正在通过国内镜像加载 BGE 模型...")
    # 使用新版 HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-zh-v1.5",
        model_kwargs={"device": "cpu"},  # 如果你是 M芯片 Mac，也可以尝试 'mps'
        encode_kwargs={"normalize_embeddings": True},
    )


def load_and_split_markdown(directory: str):
    md_files = glob.glob(os.path.join(directory, "**/*.md"), recursive=True)
    logger.info(f"📂 发现 {len(md_files)} 个 Markdown 文件")

    all_splits = []

    # 1. 标题切分规则
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on
    )

    # 2. 字符长度切分规则
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

    for file_path in tqdm(md_files, desc="处理进度"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()

            # 第一刀：按 Markdown 标题切
            md_header_splits = markdown_splitter.split_text(text)

            # 注入元数据
            for doc in md_header_splits:
                doc.metadata["source"] = os.path.basename(file_path)

            # 第二刀：按长度切
            splits = text_splitter.split_documents(md_header_splits)
            all_splits.extend(splits)

        except Exception as e:
            logger.error(f"❌ 读取文件 {file_path} 失败: {e}")

    return all_splits


def build_index():
    # 1. 初始化模型
    embedding_model = init_embedding_model()

    # 2. 加载与切分
    logger.info("🔪 开始切分文档...")
    docs = load_and_split_markdown(BLOG_DIR)

    if not docs:
        logger.warning("⚠️ 没有找到任何文档，请检查 BLOG_DIR 路径是否正确！")
        return

    logger.success(f"✅ 共生成 {len(docs)} 个知识片段")

    # 3. 向量化并建库
    logger.info("🧠 正在向量化 (这可能需要几分钟)...")
    vector_store = FAISS.from_documents(docs, embedding_model)

    # 4. 保存
    vector_store.save_local(DB_SAVE_PATH)
    logger.success(f"🎉 知识库已构建完成，保存在: {DB_SAVE_PATH}")


if __name__ == "__main__":
    build_index()
