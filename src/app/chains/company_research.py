import asyncio
import httpx
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger

from app.core.llm_factory import get_llm

# 1. 初始化工具
search_tool = TavilySearchResults(max_results=3)


async def fetch_website_content(url: str) -> str:
    """Jina Reader 抓取逻辑 (保持不变)"""
    jina_url = f"https://r.jina.ai/{url}"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with httpx.AsyncClient(verify=False) as client:
        try:
            resp = await client.get(jina_url, timeout=8, headers=headers)
            if resp.status_code == 200:
                return resp.text[:2000]  # 进一步缩减字符数，只看头部核心信息
            return ""
        except Exception:
            return ""


async def research_company(company_name: str) -> str:
    # --- 0. 兜底逻辑 ---
    if not company_name or len(company_name) < 2 or "某" in company_name:
        return "⚠️ **提示**：JD 未提供具体公司名称，无法进行精确背调。"

    logger.debug(f"🕵️ [Research] 开始全网搜索: {company_name}")

    # --- 1. 关键词扩展 ---
    queries = [
        f"{company_name} 官网 核心业务",
        f"{company_name} 融资情况 发展",
        f"{company_name} 技术团队 评价"
    ]

    # --- 2. 并行搜索 ---
    try:
        search_results = []
        for q in queries:
            # 使用 ainvoke (如果 langchain 版本支持) 或同步 invoke
            try:
                res = await search_tool.ainvoke(q)
            except:
                res = search_tool.invoke(q)  # 降级同步

            if isinstance(res, list):
                search_results.extend(res)
    except Exception as e:
        return f"搜索服务异常: {e}"

    # --- 3. 结果清洗与官网抓取 ---
    seen_urls = set()
    unique_results = []
    best_url = None

    for item in search_results:
        url = item.get("url", "")
        content = item.get("content", "")

        if url not in seen_urls:
            seen_urls.add(url)
            # 仅保留较短的摘要，减少噪音
            unique_results.append(f"- {content[:150]}")

            if not best_url and "官网" in queries[0] and not any(
                    x in url for x in ["zhihu", "baike", "job", "boss", "36kr"]):
                best_url = url

    # --- 4. 深度阅读 ---
    deep_content = ""
    if best_url:
        logger.debug(f"📖 [Research] 正在深度阅读官网: {best_url}")
        deep_content = await fetch_website_content(best_url)

    # --- 5. LLM 总结 (✨ 核心优化点) ---
    llm = get_llm(temperature=0.2)  # 调低温度，让输出更稳定干练

    context_text = "\n".join(unique_results[:6])  # 减少输入量，防止干扰
    full_context = f"【搜索摘要】:\n{context_text}\n\n【官网首页】:\n{deep_content}"

    # ✅ 优化后的 Prompt：强制 Markdown 格式 + 列表化
    prompt = ChatPromptTemplate.from_template(
        """
        你是一个极其精炼的商业情报分析师。请根据搜集到的信息，生成一份**极简**的公司背景报告。

        目标公司：{company_name}
        搜集情报：
        {context}

        ---

        ### 输出格式要求 (必须严格遵守)：
        请直接输出 Markdown，不要有任何开场白（如“根据搜索结果...”）。

        格式如下：
        **🏢 一句话简介**：[用一句话定义公司性质，如：A轮融资的AI医疗初创公司]

        **📦 核心业务**：
        - [关键点1，简练]
        - [关键点2，简练]

        **📈 发展状况**：
        - [融资/上市/规模信息，如果没有则写“暂无公开信息”]
        - [最近大新闻，如无则不写]

        **💡 补充情报**：
        - [是否有加班文化/技术栈特点/远程办公等，如无则不写]

        ---
        **约束**：
        1. 总字数控制在 **200字以内**。
        2. 能用列表就绝对不要用长段落。
        3. 信息必须来自提供的上下文，严禁编造。
        """
    )

    chain = prompt | llm | StrOutputParser()

    try:
        summary = await chain.ainvoke({
            "company_name": company_name,
            "context": full_context
        })
        return summary
    except Exception as e:
        logger.error(f"❌ Summary Gen Error: {e}")
        return "背调总结生成失败。"