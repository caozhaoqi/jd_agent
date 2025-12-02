import asyncio
import httpx
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from app.core.llm_factory import get_llm

# 1. 初始化工具
# max_results=3 表示每个关键词搜3条，一共搜 3x3=9条
search_tool = TavilySearchResults(max_results=3)


async def fetch_website_content(url: str) -> str:
    """
    利用 Jina Reader 将网页转为 Markdown (免费、无Key)
    """
    jina_url = f"https://r.jina.ai/{url}"
    headers = {"User-Agent": "Mozilla/5.0"}

    async with httpx.AsyncClient(verify=False) as client:
        try:
            # 设置 10秒 超时，防止卡死
            resp = await client.get(jina_url, timeout=10, headers=headers)
            if resp.status_code == 200:
                # 截取前 3000 字符，防止 Token 爆炸
                return resp.text[:3000]
            return ""
        except Exception as e:
            print(f"⚠️ Jina Reader failed for {url}: {e}")
            return ""


async def research_company(company_name: str) -> str:
    """
    L5 级背调：搜索 + 筛选 + 深度阅读 + 总结
    """
    # --- 0. 兜底逻辑 ---
    if not company_name or len(company_name) < 2 or "某" in company_name:
        return "未提供具体公司名称，跳过深度背调，基于行业通用标准分析。"

    print(f"🕵️ [Research] 开始全网搜索: {company_name}")

    # --- 1. 关键词扩展 (广撒网) ---
    queries = [
        f"{company_name} 官网 关于我们",  # 找官网
        f"{company_name} 核心产品 业务模式",  # 找业务
        f"{company_name} 融资 评价 面试"  # 找舆情
    ]

    # --- 2. 并行搜索 ---
    # Tavily 可能是同步工具，我们需要用 run_in_executor 或者是它自带的 ainvoke
    # 这里假设 search_tool.invoke 是同步的，我们简单包装一下或者直接调
    try:
        search_results = []
        for q in queries:
            # 也可以用 asyncio.to_thread 包装以防阻塞
            res = await search_tool.ainvoke(q)
            if isinstance(res, list):
                search_results.extend(res)
    except Exception as e:
        return f"搜索服务异常: {e}"

    # --- 3. 结果去重与筛选官网 ---
    seen_urls = set()
    unique_results = []
    best_url = None

    for item in search_results:
        url = item.get("url", "")
        content = item.get("content", "")

        if url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(f"- 来源: {url}\n  摘要: {content}")

            # 简单的官网探测策略：
            # 如果是第一次循环(搜官网Query)，且URL不包含 baidu/zhihu/job 等第三方平台
            # 就暂定为最佳 URL 用于深度抓取
            if not best_url and "官网" in queries[0] and not any(x in url for x in ["zhihu", "baike", "job", "boss"]):
                best_url = url

    # --- 4. 深度阅读 (钓大鱼) ---
    deep_content = ""
    if best_url:
        print(f"📖 [Research] 正在深度阅读官网: {best_url}")
        deep_content = await fetch_website_content(best_url)
        if deep_content:
            deep_content = f"\n\n=== 官网深度抓取 ({best_url}) ===\n{deep_content}\n"

    # --- 5. LLM 总结 (深加工) ---
    llm = get_llm(temperature=0.4)  # 稍微有点创造力，但也保持严谨

    # 构造最终上下文
    context_text = "\n".join(unique_results[:8])  # 只取前8个摘要防止过长
    full_context = f"{context_text}{deep_content}"

    prompt = ChatPromptTemplate.from_template(
        """
        你是一名专业的商业情报分析师。请根据以下搜集到的碎片信息，为求职者生成一份公司背景报告。

        目标公司：{company_name}

        === 搜集到的情报 ===
        {context}
        ==================

        请总结以下 3 点（如果信息缺失，请明确指出）：
        1. **核心业务**：他们到底是做什么的？主要产品是什么？
        2. **发展状况**：是初创、独角兽还是上市公司？最近有什么大新闻（融资/裁员/新产品）？
        3. **技术/文化氛围**：如果有相关信息，分析一下技术栈偏好或加班情况。

        要求：
        - 语气客观、专业。
        - 字数控制在 300 字以内。
        - 使用 Markdown 格式。
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
        print(f"❌ Summary Gen Error: {e}")
        return "背调总结生成失败。"