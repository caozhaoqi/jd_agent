from langchain_core.tools import tool
from app.core.knowledge_base import kb_engine
from app.chains.company_research import research_company

# 1. 定义查博客工具
@tool
def search_blog_tool(query: str) -> str:
    """
    当用户询问具体技术问题，或者需要查找相关技术资料时，使用此工具查询个人博客知识库。
    输入应该是一个具体的技术关键词，如 'Docker 原理' 或 'FastAPI 依赖注入'。
    """
    # 这里调用我们之前写好的 RAG 引擎
    # 注意：这里是同步调用，生产环境可用 async 工具
    import asyncio
    # 临时封装一下异步调用
    result = asyncio.run(kb_engine.search(query))
    return result["context"]

# 2. 定义查公司工具
@tool
def search_company_tool(company_name: str) -> str:
    """
    当需要了解某家公司的背景、新闻、财报时使用此工具。
    输入应该是公司名称。
    """
    import asyncio
    return asyncio.run(research_company(company_name))