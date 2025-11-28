import os
import glob
from typing import List
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.vectorstores import FAISS
from tqdm import tqdm

# === 配置区域 ===
BLOG_DIR = "/Users/caozhaoqi/Downloads/hexo-bamboo-blog/source/_posts"  # 你的博客 Markdown 文件夹路径
DB_SAVE_PATH = "blog_faiss_index"  # 向量库存放路径

# 1. 初始化 Embedding 模型 (JD要求: BGE)
print("⏳ 正在加载 BGE 模型...")
embedding_model = HuggingFaceBgeEmbeddings(
    model_name="BAAI/bge-small-zh-v1.5",
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)


def load_and_split_markdown(directory: str):
    """
    加载并切分 Markdown 文件
    策略：先按标题切分，再按字符长度递归切分
    """
    md_files = glob.glob(os.path.join(directory, "**/*.md"), recursive=True)
    print(f"📂 发现 {len(md_files)} 个 Markdown 文件")

    all_splits = []

    # 定义 Markdown 标题切分规则 (保留章节结构)
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

    # 定义字符长度切分规则 (防止切分后依然过长)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    for file_path in tqdm(md_files, desc="处理文件中"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()

            # 第一刀：按 Markdown 标题切
            md_header_splits = markdown_splitter.split_text(text)

            # 把文件名作为 source 存入 metadata，方便溯源
            for doc in md_header_splits:
                doc.metadata["source"] = os.path.basename(file_path)

            # 第二刀：按长度切
            splits = text_splitter.split_documents(md_header_splits)
            all_splits.extend(splits)

        except Exception as e:
            print(f"❌ 读取文件 {file_path} 失败: {e}")

    return all_splits


def build_index():
    # 1. 加载与切分
    docs = load_and_split_markdown(BLOG_DIR)
    print(f"✅ 共生成 {len(docs)} 个知识片段")

    # 2. 向量化并建库
    print("⏳ 正在向量化 (这可能需要几分钟)...")
    vector_store = FAISS.from_documents(docs, embedding_model)

    # 3. 保存
    vector_store.save_local(DB_SAVE_PATH)
    print(f"🎉 知识库已构建完成，保存在: {DB_SAVE_PATH}")


if __name__ == "__main__":
    build_index()