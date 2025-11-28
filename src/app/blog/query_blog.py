import os
import sys
from dotenv import load_dotenv

# ==========================================
# 🔴 核心修复：强制加载项目根目录的 .env 文件
# ==========================================
# 获取当前脚本的绝对路径
current_path = os.path.abspath(__file__)
# 向回退 4 层找到项目根目录 (根据你的目录结构: src/app/blog/query_blog.py)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
env_path = os.path.join(project_root, ".env")

# 1. 加载环境变量
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"✅ 已加载环境变量: {env_path}")
else:
    print(f"❌ 警告: 未找到 .env 文件，路径: {env_path}")

# 2. 将 src 目录加入 Python 搜索路径，防止 'ModuleNotFoundError: No module named app'
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.append(src_path)
# ==========================================

# 🔴 修复依赖导入
# 必须先安装新版库: pip install langchain-huggingface
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.core.llm_factory import get_llm

# 路径配置 (指向生成的向量库文件夹)
DB_LOAD_PATH = "../../../blog_faiss_index"


def query_blog_knowledge(question: str):
    # 1. 初始化 Embedding 模型 (使用新版)
    print("⏳ 正在加载 BGE 模型...")
    embedding_model = HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-zh-v1.5",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )

    try:
        # 加载向量库
        vector_store = FAISS.load_local(
            DB_LOAD_PATH,
            embedding_model,
            allow_dangerous_deserialization=True
        )
    except Exception as e:
        return f"❌ 找不到知识库目录 '{DB_LOAD_PATH}'。\n请先确保你运行了 build_blog_kb.py 并且生成了索引文件。\n错误详情: {e}"

    # 2. 检索 (Retrieve)
    print(f"🔍 正在检索问题: {question}")
    docs = vector_store.similarity_search(question, k=3)

    if not docs:
        return "博客里好像没有相关内容。"

    # 拼接上下文
    context = "\n\n".join([f"---片段来源: {d.metadata.get('source', '未知')}---\n{d.page_content}" for d in docs])

    # 3. 生成 (Generate)
    llm = get_llm(temperature=0.3)

    prompt = ChatPromptTemplate.from_template(
        """
        你是一个基于个人博客的 AI 助手。请根据下面的博客内容回答用户问题。
        如果博客内容里没有提到，请直接说“博客里没有涉及该话题”。

        【博客内容片段】：
        {context}

        【用户问题】：
        {question}
        """
    )

    chain = prompt | llm | StrOutputParser()

    print(f"📄 参考文章: {[d.metadata.get('source') for d in docs]}")

    response = chain.invoke({"context": context, "question": question})
    return response


if __name__ == "__main__":
    # 交互式查询
    while True:
        print("\n" + "=" * 30)
        q = input("请输入你想查询博客的问题 (输入 q 退出): ")
        if q.lower() in ['q', 'quit', 'exit']:
            break

        answer = query_blog_knowledge(q)
        print("\n🤖 AI 回答:\n", answer)