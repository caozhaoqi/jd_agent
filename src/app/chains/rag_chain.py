import os

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser
from app.core.config import settings

# 1. 初始化向量数据库连接
DB_DIR = "/Users/caozhaoqi/PycharmProjects/JD_agent/src/app/blog/chroma_db"
embedding_model = HuggingFaceEmbeddings(model="shibing624/text2vec-base-chinese")

# 检查数据库是否存在
if os.path.exists(DB_DIR):
    vectorstore = Chroma(persist_directory=DB_DIR, embedding_function=embedding_model)
    # search_kwargs={"k": 3} 表示每次只找最相关的 3 个片段
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
else:
    retriever = None

# 2. 定义 Prompt：严格限制只用上下文回答
template = """
你是一个严谨的知识库助手。请仅根据以下提供的【上下文内容】回答用户的【问题】。

规则：
1. 如果【上下文内容】中没有答案，请直接回答 "知识库中未找到相关内容"，不要编造。
2. 回答必须准确、客观。
3. 不需要你在回答中列出来源，来源会在最后自动附加。

【上下文内容】：
{context}

【问题】：
{question}
"""
prompt = ChatPromptTemplate.from_template(template)


# 3. 辅助函数：格式化检索到的文档，并提取源文件名称
def format_docs_with_source(docs):
    # 拼接内容给 LLM 看
    formatted_content = "\n\n".join(doc.page_content for doc in docs)
    return formatted_content


def extract_sources(docs):
    # 提取元数据中的 source (文件名) 并去重
    sources = set()
    for doc in docs:
        # source 通常是文件的绝对路径，我们只取文件名
        file_path = doc.metadata.get("source", "未知来源")
        file_name = os.path.basename(file_path)
        sources.add(file_name)
    return list(sources)


# 4. 构建 RAG 链
def get_rag_chain():
    if not retriever:
        raise ValueError("知识库未构建！请先运行 scripts/build_kb.py")

    llm = ChatOpenAI(
        model_name=settings.MODEL_NAME,
        openai_api_key=settings.OPENAI_API_KEY,
        openai_api_base=settings.OPENAI_API_BASE,
        temperature=0.1  # RAG 任务温度要低，防幻觉
    )

    # 使用 RunnableParallel 并行获取检索结果
    rag_chain_from_docs = (
            RunnableParallel(
                {
                    "context": lambda x: format_docs_with_source(x["docs"]),
                    "question": lambda x: x["question"]
                }
            )
            | prompt
            | llm
            | StrOutputParser()
    )

    # 最终链：先检索，再把 docs 传给 rag_chain_from_docs，同时保留 docs 用于提取来源
    chain = (
        RunnableParallel(
            {"docs": retriever, "question": RunnablePassthrough()}
        )
        .assign(answer=rag_chain_from_docs)
        .pick(["answer", "docs"])
    )

    return chain


# 5. 封装一个简单的调用函数
async def ask_knowledge_base(question: str):
    chain = get_rag_chain()
    # 调用链
    result = await chain.ainvoke(question)

    answer = result["answer"]
    source_docs = result["docs"]

    # 提取来源列表
    sources = extract_sources(source_docs)

    return {
        "answer": answer,
        "sources": sources
    }