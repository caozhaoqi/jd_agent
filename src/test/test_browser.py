import asyncio
import sys
import os

# 添加src目录到Python搜索路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from app.utils.browser import browse_website

async def test_browser():
    print("Testing browser tool...")
    result = await browse_website('')
    print("Result:", result[:1000] + "..." if len(result) > 1000 else result)

if __name__ == "__main__":
    asyncio.run(test_browser())
