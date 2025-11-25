from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.output_parsers import StrOutputParser
from app.utils.prompt_loader import load_prompt
from app.core.llm_factory import get_llm


async def research_company(company_name: str) -> str:
    """
    异步联网搜索公司背景
    """
    if not company_name or "公司" not in company_name:
        return "未识别到具体的公司名称，跳过背景调查。"

    # 1. 初始化搜索工具 (Tavily)
    search = TavilySearchResults(max_results=3)

    # 2. 执行搜索 (异步调用工具)
    # 注意：LangChain 的 Tool 并不总是原生支持 async，但在 Service 层我们用线程池或 await 即可
    try:
        # 这里 Tavily 的异步支持可能因版本而异，这里用同步封装演示逻辑
        search_results = search.invoke(f"{company_name} 最近的新闻 财报 业务动态")
    except Exception as e:
        return f"搜索失败: {str(e)}"

    # 3. 让 LLM 总结搜索结果
    llm = get_llm(temperature=0.5)
    prompt = load_prompt("company_research.yaml")  # 你的总结 Prompt

    chain = prompt | llm | StrOutputParser()

    # 4. 生成总结报告
    summary = await chain.ainvoke({
        "company_name": company_name,
        "search_results": str(search_results)
    })

    return summary