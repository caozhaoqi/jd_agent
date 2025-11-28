from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.core.llm_factory import get_llm  # 复用你之前的 LLM 工厂

# 路径配置
DB_LOAD_PATH = "blog_faiss_index"


def query_blog_knowledge(question: str):
    # 1. 加载模型和向量库
    embedding_model = HuggingFaceBgeEmbeddings(
        model_name="BAAI/bge-small-zh-v1.5",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )

    try:
        vector_store = FAISS.load_local(
            DB_LOAD_PATH,
            embedding_model,
            allow_dangerous_deserialization=True
        )
    except Exception:
        return "❌ 找不到知识库，请先运行 build_blog_kb.py"

    # 2. 检索 (Retrieve)
    # k=3 表示找最相关的3个片段
    docs = vector_store.similarity_search(question, k=3)

    if not docs:
        return "博客里好像没有相关内容。"

    # 拼接上下文
    context = "\n\n".join([f"---片段来源: {d.metadata['source']}---\n{d.page_content}" for d in docs])

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

    print(f"🔎 检索到的相关文章: {[d.metadata['source'] for d in docs]}")

    # 流式输出或直接输出
    response = chain.invoke({"context": context, "question": question})
    return response


if __name__ == "__main__":
    q = input("请输入你想查询博客的问题: ")
    answer = query_blog_knowledge(q)
    print("\n🤖 AI 回答:\n", answer)