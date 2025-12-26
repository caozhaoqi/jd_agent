#!/usr/bin/env python3
"""
简化版牛客网爬虫测试脚本
"""
import requests
from bs4 import BeautifulSoup
import time
import random

def get_nowcoder_interviews(page=1, order_type=3):
    """
    简化版牛客网面经爬取函数
    """
    base_url = "https://www.nowcoder.com"
    url = f"{base_url}/discuss?type=2&order={order_type}&page={page}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.nowcoder.com/discuss/interview?orderType=3&companyId=0&tagId=0"
    }
    
    print(f"\n正在爬取页面: {url}")
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print(f"页面响应状态码: {response.status_code}")
        
        # 保存页面内容用于调试
        with open(f'nowcoder_page_{page}.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"页面内容已保存到 nowcoder_page_{page}.html")
        
        # 解析页面
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 查找所有可能包含面经的链接
        all_links = soup.find_all("a", href=True)
        print(f"页面中共找到 {len(all_links)} 个链接")
        
        # 过滤出面经相关链接
        interview_links = []
        seen_urls = set()
        
        for link in all_links:
            href = link.get("href", "")
            text = link.text.strip()
            
            if href.startswith("/discuss/") and text and len(text) > 5:
                full_url = base_url + href
                if full_url not in seen_urls:
                    seen_urls.add(full_url)
                    interview_links.append((text, full_url))
        
        print(f"找到 {len(interview_links)} 条面经链接")
        
        # 打印前5条面经
        for i, (title, url) in enumerate(interview_links[:5]):
            print(f"\n{i+1}. 标题: {title}")
            print(f"   URL: {url}")
        
        return interview_links
        
    except Exception as e:
        print(f"爬取失败: {e}")
        return []

def test_crawler():
    """测试爬虫功能"""
    print("=== 牛客网面经爬虫测试 ===")
    
    # 测试第一页
    interviews = get_nowcoder_interviews(page=1)
    
    if interviews:
        print("\n=== 测试获取面经详情 ===")
        # 测试获取第一条面经的详情
        title, url = interviews[0]
        print(f"\n获取面经详情: {title}")
        print(f"URL: {url}")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            print(f"面经详情页面状态码: {response.status_code}")
            
            # 保存详情页面
            with open('html/nowcoder_detail.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print("面经详情已保存到 nowcoder_detail.html")
            
            # 简单解析内容
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 查找内容区域
            content_div = soup.find("div", class_=lambda x: x and ("content" in x or "post" in x))
            
            if content_div:
                content = content_div.get_text(separator="\n", strip=True)
                print(f"\n面经内容前500字: {content[:500]}...")
            else:
                print("未找到内容区域")
                
        except Exception as e:
            print(f"获取面经详情失败: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_crawler()
