"""
优化的RAG链 - 使用统一架构
解决当前项目中向量数据库分散和硬编码问题
"""

import os
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

# 设置 HuggingFace 国内镜像
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from loguru import logger

from core.config import settings
from core.vector_store import vector_store, UnifiedVectorStore
from core.cache import search_cache
from core.exceptions import RAGError, RAGRetrievalError, handle_exceptions, ErrorContext
from core.query_cache import QueryCache

# 延迟初始化组件
_rag_chain = None
_rewrite_chain = None
_blog_retriever = None
_interview_retriever = None
_initialization_lock = False
_query_cache = None  # 添加智能查询缓存实例


def init_rag_components():
    """延迟初始化所有RAG相关的组件，避免启动时加载模型"""
    global _rag_chain, _rewrite_chain, _blog_retriever, _interview_retriever, _initialization_lock
    
    # 使用锁防止并发初始化
    if _initialization_lock:
        logger.info("🔄 RAG组件正在初始化中，跳过重复初始化")
        # 等待初始化完成
        while _initialization_lock:
            time.sleep(0.1)
        return
    
    # 快速检查组件是否已初始化
    if _blog_retriever is not None and _interview_retriever is not None and _rewrite_chain is not None:
        return
    
    _initialization_lock = True
    try:
        logger.info("正在初始化优化RAG组件...")
        
        # 直接使用已有的向量数据库实例，避免重复初始化
        vs = vector_store
        
        # 预创建博客知识库检索器，简化参数
        def blog_retriever(query: str):
            try:
                # 直接调用向量数据库搜索，减少额外检查
                return vs.search_by_type(
                    query=query,
                    doc_type="blog",
                    k=3,
                    # score_threshold参数在某些版本中不支持，直接移除
                )
            except Exception as e:
                logger.warning(f"博客知识库检索失败: {e}")
                return []
        
        # 预创建面试经验检索器，简化参数
        def interview_retriever(query: str):
            try:
                # 直接调用向量数据库搜索，减少额外检查
                return vs.search_by_type(
                    query=query,
                    doc_type="interview",
                    k=3,
                    # score_threshold参数在某些版本中不支持，直接移除
                )
            except Exception as e:
                logger.warning(f"面试经验知识库检索失败: {e}")
                return []
        
        # 只在第一次调用时创建检索器
        _blog_retriever = blog_retriever
        _interview_retriever = interview_retriever
        
        # 初始化查询改写链 - 预编译模板以减少运行时开销
        if _rewrite_chain is None:
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
            
            rewrite_llm = ChatOpenAI(
                model_name=settings.MODEL_NAME,
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_API_BASE,
                temperature=0.1,
            )
            _rewrite_chain = rewrite_prompt | rewrite_llm | StrOutputParser()
        
        logger.success("✅ 优化RAG组件初始化成功")
        
    except Exception as e:
        logger.error(f"❌ 优化RAG组件初始化失败: {e}")
        # 失败时重置状态，允许重试
        _blog_retriever = None
        _interview_retriever = None
        _rewrite_chain = None
        raise
    finally:
        _initialization_lock = False


def get_blog_retriever():
    """获取博客知识库检索器"""
    return _blog_retriever


def get_interview_retriever():
    """获取面试经验检索器"""
    return _interview_retriever


def get_query_cache():
    """获取智能查询缓存实例"""
    global _query_cache
    if _query_cache is None:
        _query_cache = QueryCache()
    return _query_cache

def get_rewrite_chain():
    """获取查询改写链实例"""
    global _rewrite_chain
    if _rewrite_chain is None:
        init_rag_components()
    return _rewrite_chain


def format_docs_with_source(docs):
    """格式化文档内容并提取来源"""
    if not docs:
        return ""
    
    formatted_parts = []
    for i, doc in enumerate(docs, 1):
        # 添加文档编号
        formatted_parts.append(f"【文档 {i}】")
        formatted_parts.append(doc.page_content)
        formatted_parts.append("")  # 空行分隔
    
    return "\n".join(formatted_parts)


def extract_sources(docs):
    """提取文档来源"""
    if not docs:
        return []
    
    sources = set()
    for doc in docs:
        source = doc.metadata.get("source", "未知来源")
        # 提取文件名
        if "/" in source:
            filename = source.split("/")[-1]
        else:
            filename = source
        sources.add(filename)
    
    return list(sources)


@handle_exceptions("combined_retrieval")
def combined_retrieval(question: str) -> List:
    """
    合并检索函数 - 优化版本，减少网络调用和重复操作
    
    Args:
        question: 查询问题
        
    Returns:
        合并后的文档列表
    """
    # 快速检查RAG组件状态，如果未初始化则进行初始化
    if _rag_chain is None or _rewrite_chain is None or _blog_retriever is None or _interview_retriever is None:
        init_rag_components()
    
    # 检查缓存
    cache_key = f"combined_{hash(question)}"
    cached_result = search_cache.get(cache_key)
    if cached_result:
        logger.debug(f"🔍 使用缓存结果: {question}")
        return cached_result
    
    # 直接使用全局变量，避免额外的函数调用
    blog_retriever = _blog_retriever
    interview_retriever = _interview_retriever
    
    # 简化检索流程 - 先检查博客知识库
    blog_docs = blog_retriever(question)
    logger.info(f"🔍 从博客知识库检索到 {len(blog_docs)} 个文档")
    
    # 如果博客检索有结果，则减少面试经验检索的文档数量
    interview_docs = []
    if len(blog_docs) < 3:
        interview_docs = interview_retriever(question)
        logger.info(f"🔍 从面试经验知识库检索到 {len(interview_docs)} 个文档")
    else:
        logger.debug(f"🔍 博客知识库已有 {len(blog_docs)} 个结果，跳过面试经验检索")
    
    # 合并结果
    combined_docs = blog_docs + interview_docs
    
    # 优化去重逻辑，简化排序操作
    seen_sources = set()
    unique_docs = []
    for doc in combined_docs:
        source = doc.metadata.get("source", "")
        if source not in seen_sources:
            seen_sources.add(source)
            unique_docs.append(doc)
    
    # 简化排序逻辑，在空知识库时不进行排序操作
    if unique_docs:
        # 仅在有足够结果时进行排序，否则直接返回
        if len(unique_docs) > 3:
            # 根据元数据中的score排序（如果存在）
            unique_docs.sort(key=lambda x: x.metadata.get('score', 0), reverse=True)
    
    logger.info(f"🔍 合并并去重后共 {len(unique_docs)} 个文档")
    
    # 缓存结果，移除不兼容的参数
    search_cache.set(cache_key, unique_docs)
    
    return unique_docs


@handle_exceptions("enhanced_retrieval")
def enhanced_retrieval(question: str) -> List:
    """
    增强检索函数 - 使用智能查询缓存系统
    
    Args:
        question: 原始查询问题
        
    Returns:
        增强后的文档列表
    """
    # 获取智能查询缓存实例
    cache = get_query_cache()
    
    # 尝试从智能查询缓存中获取结果
    cached_result = cache.get(question)
    if cached_result:
        logger.info(f"🔄 智能缓存命中: '{question[:50]}...'")
        return cached_result.get("docs", [])
    
    # 快速检查RAG组件状态，如果未初始化则进行初始化
    if _rag_chain is None or _rewrite_chain is None or _blog_retriever is None or _interview_retriever is None:
        init_rag_components()
    
    # 直接使用全局变量，避免额外的函数调用
    rewrite_chain = _rewrite_chain
    
    # 简化查询改写 - 减少LLM调用
    try:
        # 使用缓存的改写结果加速查询
        cache_key = f"rewrite_{hash(question)}"
        rewritten_question = search_cache.get(cache_key)
        
        if not rewritten_question:
            # 只有当没有缓存时才进行改写
            rewritten_question = rewrite_chain.invoke({"x": question})
            # 缓存改写结果
            search_cache.set(cache_key, rewritten_question)
            
            logger.info(f"🔄 查询改写: '{question}' -> '{rewritten_question}'")
        else:
            logger.debug(f"🔄 使用缓存改写: '{question}' -> '{rewritten_question}'")
        
        # 如果改写结果不理想，使用原始查询
        if not rewritten_question or len(rewritten_question.strip()) < 2:
            rewritten_question = question
    except Exception as e:
        logger.warning(f"查询改写失败: {e}, 使用原始查询")
        rewritten_question = question
    
    # 使用改写后的查询进行检索
    enhanced_docs = combined_retrieval(rewritten_question)
    
    # 将检索结果存储到智能查询缓存中
    cache_result = {
        "docs": enhanced_docs,
        "timestamp": time.time()
    }
    cache.set(question, cache_result)
    
    # 简化扩展检索逻辑，在空知识库时直接返回结果
    if len(enhanced_docs) < 3:
        logger.info(f"🔍 检索结果较少: {len(enhanced_docs)} 个文档，直接返回结果")
        return enhanced_docs
    
    return enhanced_docs


def build_rag_chain():
    """构建优化的RAG链"""
    
    # 定义Prompt模板
    template = """
    你是一个严谨的知识库助手。请仅根据以下提供的【上下文内容】回答用户的【问题】。

    规则：
    1. 如果【上下文内容】中没有答案，请直接回答 "知识库中未找到相关内容"，不要编造。
    2. 回答必须准确、客观，基于提供的上下文内容。
    3. 不需要你在回答中列出来源，来源会在最后自动附加。
    4. 所有生成内容必须使用中文。

    【上下文内容】：
    {context}

    【问题】：
    {question}
    """
    
    prompt = ChatPromptTemplate.from_template(template)
    
    # 获取LLM
    llm = ChatOpenAI(
        model_name=settings.MODEL_NAME,
        openai_api_key=settings.OPENAI_API_KEY,
        openai_api_base=settings.OPENAI_API_BASE,
        temperature=0.1,  # RAG任务温度要低，防幻觉
    )
    
    # 构建RAG链
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
    
    # 最终链：使用增强检索
    enhanced_chain = (
        RunnableParallel(
            {
                "docs": enhanced_retrieval,
                "question": RunnablePassthrough(),
            }
        )
        .assign(answer=rag_chain_from_docs)
        .pick(["answer", "docs"])
    )
    
    # 缓存RAG链实例
    global _rag_chain
    _rag_chain = enhanced_chain
    
    return enhanced_chain


def build_enhanced_rag_chain():
    """构建增强的RAG链（支持异步和查询改写）"""
    
    # 定义改进的Prompt模板
    enhanced_template = """
    你是一个专业的技术知识库助手，专门为开发者提供准确、实用的技术信息。

    任务：根据提供的【上下文内容】回答用户的【问题】，确保回答准确、实用。

    回答原则：
    1. 仅基于提供的上下文内容回答，不要编造信息
    2. 如果上下文没有相关信息，诚实回答"知识库中未找到相关内容"
    3. 优先提供实用的技术细节和具体解决方案
    4. 保持回答简洁明了，重点突出
    5. 使用中文回答

    【上下文内容】：
    {context}

    【问题】：{question}
    """
    
    enhanced_prompt = ChatPromptTemplate.from_template(enhanced_template)
    
    # 获取LLM
    llm = ChatOpenAI(
        model_name=settings.MODEL_NAME,
        openai_api_key=settings.OPENAI_API_KEY,
        openai_api_base=settings.OPENAI_API_BASE,
        temperature=0.2,  # 稍高的温度以获得更好的创意性
    )
    
    # 构建增强RAG链
    enhanced_rag_chain = (
        RunnableParallel(
            {
                "docs": enhanced_retrieval,
                "question": RunnablePassthrough(),
            }
        )
        | enhanced_prompt
        | llm
        | StrOutputParser()
    )
    
    return enhanced_rag_chain


@handle_exceptions("ask_knowledge_base")
async def ask_knowledge_base(question: str, use_cache: bool = True):
    """
    优化的知识库查询接口
    
    Args:
        question: 用户问题
        use_cache: 是否使用缓存
        
    Returns:
        包含答案和来源的字典
    """
    # 确保RAG组件已初始化
    global _rag_chain, _rewrite_chain, _blog_retriever, _interview_retriever
    if _rag_chain is None or _rewrite_chain is None or _blog_retriever is None or _interview_retriever is None:
        init_rag_components()
    
    # 检查缓存
    if use_cache:
        cache_key = f"answer_{hash(question)}"
        cached_answer = search_cache.get(cache_key)
        if cached_answer:
            logger.debug(f"🔍 使用答案缓存: {question}")
            return cached_answer
    
    # 获取RAG链
    if _rag_chain is None:
        _rag_chain = build_rag_chain()
    
    # 执行查询改写
    rewrite_chain = get_rewrite_chain()
    rewritten_question = await rewrite_chain.ainvoke({"x": question})
    logger.debug(f"🔄 查询改写: '{question}' -> '{rewritten_question}'")
    
    # 使用改写后的问题进行检索
    try:
        result = await _rag_chain.ainvoke(rewritten_question)
        
        answer = result["answer"]
        source_docs = result["docs"]
        
        # 提取来源
        sources = extract_sources(source_docs)
        
        # 构建响应
        response = {
            "answer": answer,
            "sources": sources,
            "original_query": question,
            "rewritten_query": rewritten_question,
            "doc_count": len(source_docs),
            "timestamp": datetime.now().isoformat()
        }
        
        # 缓存结果
        if use_cache:
            search_cache.set(cache_key, response)
        
        # 记录检索统计
        logger.info(f"📊 查询完成: 原始问题='{question}', 改写后='{rewritten_question}', 文档数量={len(source_docs)}")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ RAG查询失败: {e}")
        raise RAGRetrievalError(
            message=f"知识库查询失败: {str(e)}",
            details={"question": question, "rewritten_question": rewritten_question}
        )


@handle_exceptions("batch_search")
async def batch_search(questions: List[str], use_cache: bool = True) -> List[Dict[str, Any]]:
    """
    批量搜索
    
    Args:
        questions: 问题列表
        use_cache: 是否使用缓存
        
    Returns:
        答案列表
    """
    results = []
    
    for question in questions:
        try:
            result = await ask_knowledge_base(question, use_cache)
            results.append(result)
        except Exception as e:
            logger.error(f"批量搜索中处理问题 '{question}' 失败: {e}")
            results.append({
                "answer": f"查询失败: {str(e)}",
                "sources": [],
                "original_query": question,
                "error": str(e)
            })
    
    return results


def get_search_stats() -> Dict[str, Any]:
    """获取搜索统计信息"""
    try:
        cache_stats = search_cache.cache.get_stats()
        vs_stats = vector_store.get_stats()
        
        return {
            "cache": cache_stats,
            "vector_store": vs_stats,
            "components_initialized": _rag_chain is not None,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取搜索统计失败: {e}")
        return {"error": str(e)}


def clear_search_cache():
    """清空搜索缓存"""
    try:
        search_cache.cache.clear()
        logger.info("🔄 搜索缓存已清空")
    except Exception as e:
        logger.error(f"清空搜索缓存失败: {e}")


def health_check() -> Dict[str, Any]:
    """RAG系统健康检查"""
    try:
        # 检查向量数据库
        vs_health = vector_store.health_check()
        
        # 检查组件初始化
        components_status = {
            "rag_chain": _rag_chain is not None,
            "rewrite_chain": _rewrite_chain is not None,
            "blog_retriever": _blog_retriever is not None,
            "interview_retriever": _interview_retriever is not None
        }
        
        # 检查缓存
        cache_stats = search_cache.cache.get_stats()
        
        overall_status = "healthy"
        if vs_health["status"] != "healthy":
            overall_status = "unhealthy"
        elif not all(components_status.values()):
            overall_status = "degraded"
        
        return {
            "status": overall_status,
            "vector_store": vs_health,
            "components": components_status,
            "cache": cache_stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"RAG健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


if __name__ == "__main__":
    """测试优化RAG系统"""
    
    # 健康检查
    health = health_check()
    print(f"系统健康状态: {health}")
    
    # 获取统计信息
    stats = get_search_stats()
    print(f"系统统计: {stats}")
    
    # 测试查询
    async def test_queries():
        test_questions = [
            "Python是什么？",
            "面试经验分享",
            "机器学习算法"
        ]
        
        for question in test_questions:
            print(f"\n🔍 测试问题: {question}")
            try:
                result = await ask_knowledge_base(question)
                print(f"答案: {result['answer'][:100]}...")
                print(f"来源: {result['sources']}")
                print(f"文档数量: {result['doc_count']}")
            except Exception as e:
                print(f"查询失败: {e}")
    
    import asyncio
    asyncio.run(test_queries())
    
    print("\n✅ 优化RAG系统测试完成")