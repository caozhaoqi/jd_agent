from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# 1. 配置要测试的模型 (必须和 build_kb.py 一样)
model_name = "shibing624/text2vec-base-chinese"  # 或者你之前用的 "shibing624/text2vec-base-chinese"

print(f"正在加载模型: {model_name} ...")
embedding_model = HuggingFaceEmbeddings(
    model_name=model_name,
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)

# 2. 加载数据库
DB_DIR = "/Users/caozhaoqi/PycharmProjects/JD_agent/src/app/blog/chroma_db"
vectorstore = Chroma(persist_directory=DB_DIR, embedding_function=embedding_model)

# 3. 测试查询
query = "socket"  # 你要测试的问题
print(f"\n🔍 正在查询: {query}")

# k=5 找前5个
docs = vectorstore.similarity_search(query, k=5)

print(f"✅ 找到 {len(docs)} 个结果:\n")
for i, doc in enumerate(docs):
    print(f"--- 结果 {i+1} (来源: {doc.metadata.get('source')}) ---")
    # 打印前 100 个字
    print(doc.page_content[:150].replace("\n", " "))
    print("------------------\n")
