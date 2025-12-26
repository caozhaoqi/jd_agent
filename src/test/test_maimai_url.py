import requests
from bs4 import BeautifulSoup
import time

# 测试脉脉搜索URL并获取完整内容
url = "https://maimai.cn/feed/search?query=面试经验&page=1"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

try:
    print(f"测试URL: {url}")
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    print(f"状态码: {response.status_code}")
    
    # 保存完整响应
    with open("html/maimai_full_response.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    
    # 检查页面内容
    soup = BeautifulSoup(response.text, "html.parser")
    print(f"页面标题: {soup.title.string if soup.title else '无标题'}")
    print(f"页面长度: {len(response.text)} 字符")
    
    # 查找页面中的主要内容区域
    content = soup.find("div", class_="feed-content")
    if content:
        print(f"找到内容区域: {content.prettify()[:500]}...")
    else:
        print("未找到明确的内容区域")
    
    # 查找所有可能的内容标签
    all_divs = soup.find_all("div")
    print(f"找到 {len(all_divs)} 个div标签")
    
    # 查找包含"面试"关键词的标签
    interview_tags = []
    for tag in soup.find_all(text=True):
        if "面试" in tag and len(tag.strip()) > 5:
            interview_tags.append(tag.strip())
    
    print(f"找到 {len(interview_tags)} 个包含'面试'的文本片段")
    for i, tag in enumerate(interview_tags[:10]):
        print(f"文本 {i+1}: {tag[:100]}...")
        
except Exception as e:
    print(f"错误: {e}")
