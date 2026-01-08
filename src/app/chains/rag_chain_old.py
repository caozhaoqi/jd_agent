import os
from langchain.retrievers import ContextualCompressionRetriever
from langchain_community.document_compressors import FlashrankRerank
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser
from loguru import logger

from core.config import settings
from core.llm_factory import get_llm
from interview_experience.interview_rag import InterviewExperienceRAG

# 1. 初始化路径和组件
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "blog", "chroma_db")

_embedding_model = None
_vectorstore = None
_retriever = None
_compression_retriever = None
_rewrite_chain = None


def init_rag_components():
    """延迟初始化所有RAG相关的组件，避免启动时加载模型。"""
    global _embedding_model, _vectorstore, _retriever, _compression_retriever, _rewrite_chain
    
    if _compression_retriever is not None:
        return

    try:
        logger.info("正在初始化RAG组件...")
        # 初始化 Embedding 模型
        _embedding_model = HuggingFaceEmbeddings(model_name="shibing624/text2vec-base-chinese")
        
        if os.path.exists(DB_DIR):
            _vectorstore = Chroma(persist_directory=DB_DIR, embedding_function=_embedding_model)
            
            # 基础检索器：获取更多候选文档
            base_retriever = _vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 10},  # 扩大召回数量到10
            )
            
            # 重排序器
            reranker = FlashrankRerank(model="ms-marco-MiniLM-L-12-v2", top_n=3) # top_n=3 表示最终返回3个最相关的
            
            # 压缩检索器：结合基础检索器和重排序器
            _compression_retriever = ContextualCompressionRetriever(
                base_compressor=reranker, base_retriever=base_retriever
            )
            
            logger.success("✅ RAG组件（包括重排序器）初始化成功")
        else:
            logger.warning(f"⚠️ 向量数据库不存在于 {DB_DIR}，RAG功能受限")

        # 初始化查询改写链
        rewrite_prompt = ChatPromptTemplate.from_template(
            """你是一个专业的搜索引擎优化助手。请将用户的输入转换为一个更精准、语义更丰富的查询语句，以便在技术知识库中进行向量检索。
            要求：
            1. 补全相关的技术上下文（例如 "unity" -> "Unity3D 游戏引擎开发"）。
            2. 如果是具体问题，保持原意但使其更书面化。
            3. 仅输出改写后的查询语句，不要包含任何解释。
            4. 所有生成内容必须使用中文。
            用户输入: {x}
            改写后的查询:"""
        )
        from core.llm_factory import get_llm
        rewrite_llm = get_llm(temperature=0.1, model=settings.MODEL_NAME)
        _rewrite_chain = rewrite_prompt | rewrite_llm | StrOutputParser()

    except Exception as e:
        logger.error(f"❌ RAG组件初始化失败: {e}")


def get_retriever():
    init_rag_components()
    return _retriever

def get_compression_retriever():
    init_rag_components()
    return _compression_retriever

def get_rewrite_chain():
    init_rag_components()
    return _rewrite_chain

def get_interview_rag():
    try:
        return InterviewExperienceRAG()
    except Exception as e:
        logger.error(f"❌ 初始化面试经验RAG失败: {e}")
        return None

def format_docs_with_source(docs):
    return "\n\n".join(doc.page_content for doc in docs)

def extract_sources(docs):
    sources = {os.path.basename(doc.metadata.get("source", "未知来源")) for doc in docs}
    return list(sources)


async def ask_knowledge_base(question: str):
    """使用查询改写和重排序的RAG流程"""
    init_rag_components()
    
    if not _compression_retriever or not _rewrite_chain:
        raise ValueError("RAG组件未成功初始化，无法执行查询。")

    # 1. 查询改写
    rewritten_question = await _rewrite_chain.ainvoke({"x": question})
    logger.debug(f"查询改写: '{question}' -> '{rewritten_question}'")

    # 2. 组合检索
    blog_docs = _compression_retriever.invoke(rewritten_question)
    logger.info(f"从博客知识库检索到 {len(blog_docs)} 个文档")
    
    interview_rag = get_interview_rag()
    interview_docs = []
    if interview_rag and interview_rag.vector_store:
        # 面经使用简单检索，因为内容通常较短
        interview_docs = interview_rag.vector_store.similarity_search(rewritten_question, k=2)
        logger.info(f"从面试经验知识库检索到 {len(interview_docs)} 个文档")

    # 合并并去重
    combined_docs = blog_docs + interview_docs
    seen_sources = set()
    unique_docs = []
    for doc in combined_docs:
        source = doc.metadata.get("source", "")
        if source not in seen_sources:
            seen_sources.add(source)
            unique_docs.append(doc)
    
    logger.info(f"合并并去重后共 {len(unique_docs)} 个文档")

    if not unique_docs:
        return {"answer": "抱歉，知识库中未找到相关内容。", "sources": []}

    # 3. 构建Prompt并生成答案
    context_str = format_docs_with_source(unique_docs)
    
    template = """
    你是一个严谨的知识库助手。请仅根据以下提供的【上下文内容】回答用户的【问题】。
    规则：
    1. 如果【上下文内容】中没有答案，请直接回答 "知识库中未找到相关内容"，不要编造。
    2. 回答必须准确、客观。
    3. 不需要你在回答中列出来源，来源会在最后自动附加。
    4. 所有生成内容必须使用中文。
    【上下文内容】：
    {context}
    【问题】：
    {question}
    """
    prompt = ChatPromptTemplate.from_template(template)
    
    from core.llm_factory import get_llm
    llm = get_llm(temperature=0.1, model=settings.MODEL_NAME)
    chain = prompt | llm | StrOutputParser()
    
    answer = await chain.ainvoke({"context": context_str, "question": question})
    
    sources = extract_sources(unique_docs)

    return {
        "answer": answer,
        "sources": sources,
        "original_query": question,
        "rewritten_query": rewritten_question,
    }
