import httpx

async def browse_website(url: str):
    """
    利用 Jina Reader 将网页转为 Markdown
    """
    jina_url = f"https://r.jina.ai/{url}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(jina_url, timeout=10)
            return resp.text[:5000] # 截取前5000字防止 Token 爆炸
        except Exception as e:
            return f"无法访问网页: {e}"

# 在 research_company 中使用：
# 1. 先搜出官网 URL
# 2. content = await browse_website(company_url)
# 3. 喂给 LLM