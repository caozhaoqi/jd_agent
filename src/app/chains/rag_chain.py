import os

# 设置 HuggingFace 国内镜像
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from langchain.retrievers import ContextualCompressionRetriever
from langchain_community.document_compressors import FlashrankRerank
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser
from loguru import logger

from app.core.config import settings
from app.core.llm_factory import get_llm
from app.interview_experience.interview_rag import InterviewExperienceRAG

# 1. 初始化向量数据库连接
DB_DIR = "/Users/caozhaoqi/PycharmProjects/JD_agent/src/app/blog/chroma_db"

# 延迟初始化组件
_embedding_model = None
_vectorstore = None
_retriever = None
_compression_retriever = None


def init_retriever():
    """延迟初始化检索器组件"""
    global _embedding_model, _vectorstore, _retriever, _compression_retriever
    
    if _retriever is not None:
        return
    
    try:
        # 只在需要时才初始化模型
        _embedding_model = HuggingFaceEmbeddings(model="shibing624/text2vec-base-chinese")
        
        # 检查数据库是否存在
        if os.path.exists(DB_DIR):
            _vectorstore = Chroma(persist_directory=DB_DIR, embedding_function=_embedding_model)
            # 定义基础检索器
            _retriever = _vectorstore.as_retriever(
                search_type="similarity_score_threshold",  # 启用阈值模式
                search_kwargs={
                    "k": 3,  # 捞 3 个相关文档
                    "score_threshold": 0.4,  # 设定门槛
                },
            )
            # 暂时不使用重排序器，避免网络下载问题
            _compression_retriever = _retriever
            logger.info("✅ 检索器组件初始化成功")
        else:
            _retriever = None
            logger.warning("⚠️ 向量数据库不存在，检索器未初始化")
    except Exception as e:
        logger.error(f"❌ 检索器组件初始化失败: {e}")
        _retriever = None


# 获取检索器
def get_retriever():
    """获取检索器实例，自动初始化"""
    init_retriever()
    return _retriever


def get_compression_retriever():
    """获取压缩检索器实例，自动初始化"""
    init_retriever()
    return _compression_retriever

# 2. 定义 Prompt：严格限制只用上下文回答
template = """
你是一个严谨的知识库助手。请仅根据以下提供的【上下文内容】回答用户的【问题】。

规则：
1. 如果【上下文内容】中没有答案，请直接回答 "知识库中未找到相关内容"，不要编造。
2. 回答必须准确、客观。
3. 不需要你在回答中列出来源，来源会在最后自动附加。
4. 所有生成内容必须使用中文，包括问题和答案。

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


# 初始化面试经验RAG
def get_interview_rag():
    """获取面试经验RAG实例"""
    try:
        return InterviewExperienceRAG()
    except Exception as e:
        logger.error(f"❌ 初始化面试经验RAG失败: {e}")
        return None

# 4. 构建 RAG 链
def get_rag_chain(streaming: bool = False):
    if not get_retriever():
        raise ValueError("知识库未构建！请先运行 scripts/build_kb.py")

    llm = ChatOpenAI(
        model_name=settings.MODEL_NAME,
        openai_api_key=settings.OPENAI_API_KEY,
        openai_api_base=settings.OPENAI_API_BASE,
        temperature=0.1,  # RAG 任务温度要低，防幻觉
        streaming=streaming,
    )

    # 使用 RunnableParallel 并行获取检索结果
    rag_chain_from_docs = (
        RunnableParallel(
            {
                "context": lambda x: format_docs_with_source(x["docs"]),
                "question": lambda x: x["question"],
            }
        )
        | prompt
        | llm
        | StrOutputParser()
    )

    # 最终链：先检索，再把 docs 传给 rag_chain_from_docs，同时保留 docs 用于提取来源
    chain = (
        RunnableParallel(
            {
                "docs": get_compression_retriever(),
                "question": RunnablePassthrough(),
            }  # 使用 compression_retriever
        )
        .assign(answer=rag_chain_from_docs)
        .pick(["answer", "docs"])
    )

    return chain

# 构建包含面试经验的增强RAG链
def get_enhanced_rag_chain(streaming: bool = False):
    """构建增强的RAG链，同时使用博客知识库和面试经验知识库"""
    if not get_retriever():
        raise ValueError("博客知识库未构建！请先运行 scripts/build_kb.py")

    llm = ChatOpenAI(
        model_name=settings.MODEL_NAME,
        openai_api_key=settings.OPENAI_API_KEY,
        openai_api_base=settings.OPENAI_API_BASE,
        temperature=0.1,  # RAG 任务温度要低，防幻觉
        streaming=streaming,
    )

    # 获取面试经验RAG
    interview_rag = get_interview_rag()

    # 定义组合检索函数
    def combined_retrieval(question):
        # 从博客知识库检索
        blog_docs = get_compression_retriever().invoke(question)
        logger.info(f"🔍 从博客知识库检索到 {len(blog_docs)} 个文档")
        
        # 从面试经验知识库检索
        interview_results = []
        if interview_rag and interview_rag.vector_store:
            interview_docs = interview_rag.vector_store.similarity_search(question, k=3)
            interview_results = interview_docs
            logger.info(f"🔍 从面试经验知识库检索到 {len(interview_results)} 个文档")
        else:
            logger.warning("⚠️ 面试经验知识库未初始化或为空")
        
        # 合并结果，优先保留博客文档，再添加面试经验文档
        combined_docs = blog_docs + interview_results
        
        # 去重（根据source字段）
        seen_sources = set()
        unique_docs = []
        for doc in combined_docs:
            source = doc.metadata.get("source", "")
            if source not in seen_sources:
                seen_sources.add(source)
                unique_docs.append(doc)
        
        logger.info(f"🔍 合并并去重后共 {len(unique_docs)} 个文档")
        return unique_docs

    # 使用 RunnableParallel 并行获取检索结果
    rag_chain_from_docs = (
        RunnableParallel(
            {
                "context": lambda x: format_docs_with_source(x["docs"]),
                "question": lambda x: x["question"],
            }
        )
        | prompt
        | llm
        | StrOutputParser()
    )

    # 最终链：先检索，再把 docs 传给 rag_chain_from_docs，同时保留 docs 用于提取来源
    chain = (
        RunnableParallel(
            {
                "docs": combined_retrieval,
                "question": RunnablePassthrough(),
            }
        )
        .assign(answer=rag_chain_from_docs)
        .pick(["answer", "docs"])
    )

    return chain


# 5. 查询改写链 (用于流式查询)
rewrite_prompt = ChatPromptTemplate.from_template(
    """你是一个专业的搜索引擎优化助手。
    请将用户的输入转换为一个更精准、语义更丰富的查询语句，以便在技术知识库中进行向量检索。

    要求：
    1. 补全相关的技术上下文（例如 "unity" -> "Unity3D 游戏引擎开发"）。
    2. 如果是具体问题，保持原意但使其更书面化。
    3. 仅输出改写后的查询语句，不要包含任何解释。
    4. 所有生成内容必须使用中文。

    用户输入: {x}
    改写后的查询:"""
)

# 延迟初始化 rewrite_llm 和 rewrite_chain，避免导入时就创建
rewrite_chain = None


def get_rewrite_chain():
    """
    获取查询改写链
    """
    global rewrite_chain
    if rewrite_chain is None:
        rewrite_llm = get_llm(temperature=0.5)  # 给一点创造力
        rewrite_chain = rewrite_prompt | rewrite_llm | StrOutputParser()
    return rewrite_chain


# app/chains/rag_chain.py
async def ask_knowledge_base(question: str):
    # 🚀 优化步骤 1: 查询改写 (Query Rewriting)
    # 目的：将用户的短词 (如 "unity") 扩写为语义更丰富的句子，提高检索准确率
    rewrite_chain = get_rewrite_chain()

    # 获取改写后的问题
    better_question = await rewrite_chain.ainvoke({"x": question})
    logger.debug(f"🔄 [优化] 查询改写: '{question}' -> '{better_question}'")

    # ---------------------------------------------------------

    # 使用增强的RAG链，同时检索博客和面经数据
    chain = get_enhanced_rag_chain()

    # 🚀 优化步骤 2: 使用改写后的问题进行检索和回答
    # 注意：这里我们用 better_question 去检索文档，但 Prompt 里还是可以让 AI 知道原始问题
    result = await chain.ainvoke(better_question)

    answer = result["answer"]
    source_docs = result["docs"]

    # --- 🛠️ 调试代码：打印检索到的内容 ---
    logger.debug(f"\n🔍 [调试] 最终检索关键词: {better_question}")
    logger.debug(f"📄 [调试] 检索到 {len(source_docs)} 个片段:")

    for i, doc in enumerate(source_docs):
        # 获取文件名
        source_name = doc.metadata.get("source", "未知来源")
        # 获取相关性分数 (如果有的话，Chroma 默认 retriever 不直接返回分数，除非用 similarity_search_with_score)

        logger.debug(f"--- 片段 {i + 1} (来源: {source_name}) ---")
        # 打印内容预览，去除换行符以便查看
        preview_content = doc.page_content[:150].replace("\n", " ")
        logger.debug(f"内容: {preview_content}...")

    logger.debug("--------------------------------------------------\n")
    # ------------------------------------

    sources = extract_sources(source_docs)

    return {
        "answer": answer,
        "sources": sources,
        "original_query": question,  # (可选) 返回原始问题
        "rewritten_query": better_question,  # (可选) 返回改写后的问题供前端展示
    }
