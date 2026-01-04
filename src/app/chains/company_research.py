import asyncio
import httpx
import os
import hashlib
import json
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger

from core.config import settings
from core.llm_factory import get_llm
from core.redis_client import redis_client


# ❌ 移除全局初始化，防止启动时因缺少 Key 崩溃
# search_tool = TavilySearchResults(max_results=3)


async def fetch_website_content(url: str) -> str:
    """
    利用 Jina Reader 将网页转为 Markdown (免费、无Key)
    """
    jina_url = f"https://r.jina.ai/{url}"
    headers = {"User-Agent": "Mozilla/5.0"}

    async with httpx.AsyncClient(verify=False) as client:
        try:
            # 设置 8秒 超时，防止卡死
            resp = await client.get(jina_url, timeout=8, headers=headers)
            if resp.status_code == 200:
                # 截取前 2500 字符，防止 Token 爆炸
                return resp.text[:2500]
            return ""
        except Exception as e:
            logger.debug(f"⚠️ Jina Reader failed for {url}: {e}")
            return ""


def generate_cache_key(company_name: str) -> str:
    """
    生成公司研究结果的缓存键
    """
    cache_data = {"company_name": company_name, "version": "1.0"}
    cache_str = json.dumps(cache_data, sort_keys=True)
    cache_key = hashlib.md5(cache_str.encode()).hexdigest()
    return f"company_research:{cache_key}"


async def research_company(company_name: str) -> str:
    """
    L5 级背调：搜索 + 筛选 + 深度阅读 + 总结
    """
    # --- 0. 检查缓存 ---
    cache_key = generate_cache_key(company_name)
    cached_result = redis_client.get(cache_key)
    if cached_result:
        logger.info(f"💾 [Research Cache] 命中缓存: {company_name}")
        return cached_result

    # --- 1. 兜底逻辑 ---
    if not company_name or len(company_name) < 2 or "某" in company_name:
        return "⚠️ **提示**：JD 未提供具体公司名称，无法进行精确背调。"

    # --- 1. 安全检查与工具初始化 (懒加载) ---
    # 只有在真正调用函数时，才检查环境变量
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if not tavily_key:
        logger.debug("⚠️ 未检测到 TAVILY_API_KEY，跳过联网搜索。")
        return "⚠️ 系统未配置搜索服务(Tavily)，无法获取公司背景。"

    try:
        # ✅ 修复核心：在函数内部初始化，避免启动崩溃
        search_tool = TavilySearchResults(max_results=3, timeout=10)
    except Exception as e:
        logger.debug(f"❌ Tavily Init Error: {e}")
        return "搜索工具初始化失败。"

    logger.debug(f"🕵️ [Research] 开始全网搜索: {company_name}")

    # --- 2. 关键词扩展 ---
    # 减少搜索查询数量，提高效率
    queries = [f"{company_name} 官网 核心业务 融资情况"]

    # --- 3. 并行搜索 ---
    search_results = []
    try:
        # 使用更高效的搜索策略：只执行一次搜索
        try:
            # 尝试异步调用
            res = await search_tool.ainvoke(queries[0])
        except:
            # 降级为同步调用
            res = search_tool.invoke(queries[0])

        if isinstance(res, list):
            search_results.extend(res)
    except Exception as e:
        return f"搜索服务异常: {e}"

    # --- 4. 结果清洗与官网探测 ---
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

            # 简单的官网探测策略：优先排除第三方平台
            if (
                not best_url
                and "官网" in queries[0]
                and not any(
                    x in url
                    for x in ["zhihu", "baike", "job", "boss", "36kr", "linkedin"]
                )
            ):
                best_url = url

    # --- 5. 深度阅读 (钓大鱼) ---
    # 优化：减少深度阅读频率，只在搜索结果不足时进行
    deep_content = ""
    if best_url and len(unique_results) < 3:
        logger.debug(f"📖 [Research] 正在深度阅读官网: {best_url}")
        try:
            # 缩短超时时间，避免等待太久
            deep_content = await fetch_website_content(best_url)
            if deep_content:
                deep_content = f"\n\n=== 官网深度抓取 ({best_url}) ===\n{deep_content[:1500]}\n"  # 进一步限制内容长度
        except Exception as e:
            logger.debug(f"⚠️ 深度阅读失败，跳过: {e}")
            deep_content = ""

    # --- 6. LLM 总结 (Prompt 优化版) ---
    llm = get_llm(temperature=0.2)  # 调低温度，让输出更稳定干练

    context_text = "\n".join(unique_results[:6])  # 减少输入量
    full_context = f"【搜索摘要】:\n{context_text}\n\n{deep_content}"

    # 强制 Markdown 格式 + 列表化
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

        ---        **约束**：        1. 总字数控制在 **200字以内**。        2. 能用列表就绝对不要用长段落。        3. 信息必须来自提供的上下文，严禁编造。        4. 所有生成内容必须使用中文。
        """
    )

    chain = prompt | llm | StrOutputParser()

    try:
        summary = await chain.ainvoke(
            {"company_name": company_name, "context": full_context}
        )

        # 缓存结果，有效期7天
        redis_client.set(
            generate_cache_key(company_name),
            summary,
            expire_seconds=settings.CACHE_EXPIRATION_COMPANY_RESEARCH,
        )
        logger.info(f"💾 [Research Cache] 缓存结果: {company_name}")

        return summary
    except Exception as e:
        logger.error(f"❌ Summary Gen Error: {e}")
        return "背调总结生成失败。"
