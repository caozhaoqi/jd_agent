import requests
import asyncio
from bs4 import BeautifulSoup
import httpx

async def browse_website(url: str):
    """
    利用 Jina Reader 将网页转为 Markdown
    """
    jina_url = f"https://r.jina.ai/{url}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(jina_url, timeout=10)
            return resp.text[:5000]
        except Exception as e:
            return f"无法访问网页: {e}"

# 测试牛客网面经页面
async def test_nowcoder():
    # 尝试不同的URL结构
    url = 'https://www.nowcoder.com/discuss?order=3&type=2&page=1'
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.nowcoder.com/discuss/interview?orderType=3&companyId=0&tagId=0"
    }
    
    try:
        # 使用Jina Reader获取内容
        content = await browse_website(url)
        print(f"Content length: {len(content)}")
        
        # 保存到文件以便查看
        with open('html/nowcoder_jina_response.md', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("Content preview:")
        print(content[:1000] + "...")
        
    except Exception as e:
        print(f"Error: {e}")

# 测试脉脉面经页面
async def test_maimai():
    url = 'https://maimai.cn/web/gossip/search?query=%E9%9D%A2%E8%AF%95%E7%BB%8F%E9%AA%8C&page=1'
    
    try:
        # 使用Jina Reader获取内容
        content = await browse_website(url)
        print(f"\n\nContent length: {len(content)}")
        
        # 保存到文件以便查看
        with open('html/maimai_jina_response.md', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("Content preview:")
        print(content[:1000] + "...")
        
    except Exception as e:
        print(f"Error: {e}")

async def main():
    print("Testing Nowcoder...")
    await test_nowcoder()
    print("\n" + "="*50 + "\n")
    print("Testing Maimai...")
    await test_maimai()

if __name__ == "__main__":
    asyncio.run(main())