import os
import sys

# 设置HuggingFace国内镜像
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import json
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger

# 配置路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(CURRENT_DIR, "confluence_data")
INDEX_DIR = os.path.join(CURRENT_DIR, "confluence_faiss_index")


def load_vector_db():
    """加载向量数据库"""
    logger.info("📚 正在加载Confluence向量数据库...")
    
    # 初始化Embedding模型（与构建索引时使用相同的模型）
    embedding_model = HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-zh-v1.5",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    
    try:
        # 加载FAISS向量数据库
        vector_db = FAISS.load_local(
            INDEX_DIR,
            embedding_model,
            allow_dangerous_deserialization=True
        )
        logger.success("✅ 向量数据库加载成功！")
        return vector_db
    except Exception as e:
        logger.error(f"❌ 向量数据库加载失败: {e}")
        return None


def test_query(vector_db, query, top_k=3):
    """测试向量数据库查询"""
    logger.info(f"🔍 查询向量数据库: '{query}'")
    
    try:
        # 执行相似性搜索
        results = vector_db.similarity_search_with_score(
            query=query,
            k=top_k
        )
        
        logger.success(f"✅ 查询完成，找到 {len(results)} 个相关文档")
        
        # 打印查询结果
        print("\n" + "="*80)
        print(f"查询: {query}")
        print("="*80)
        
        for i, (doc, score) in enumerate(results, 1):
            print(f"\n🎯 结果 {i} (相似度: {1-score:.4f})")
            print(f"📄 标题: {doc.metadata.get('title', '未知')}")
            print(f"🔗 链接: {doc.metadata.get('source', '未知')}")
            print(f"📌 空间: {doc.metadata.get('space_name', '未知')}")
            print(f"📅 更新时间: {doc.metadata.get('updated_at', '未知')}")
            print(f"💬 内容预览: {doc.page_content[:200]}...")
        
        print("\n" + "="*80)
        
        return results
    except Exception as e:
        logger.error(f"❌ 查询失败: {e}")
        return None


def main():
    """主函数"""
    # 加载向量数据库
    vector_db = load_vector_db()
    if not vector_db:
        logger.error("❌ 无法加载向量数据库，请先运行构建脚本")
        return
    
    logger.info("\n💡 向量数据库测试系统已启动！")
    logger.info("💡 输入您的查询，或输入 'exit' 退出")
    
    while True:
        query = input("\n请输入查询: ")
        
        if query.lower() == "exit":
            logger.info("👋 退出测试系统")
            break
        
        if not query.strip():
            logger.warning("⚠️  请输入有效的查询")
            continue
        
        # 执行查询
        test_query(vector_db, query.strip(), top_k=3)


if __name__ == "__main__":
    main()
