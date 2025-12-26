#!/usr/bin/env python3
"""
最终测试牛客网爬虫脚本
"""
import sys
import os

# 添加src目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, 'src'))

# 导入所需模块
import requests
from bs4 import BeautifulSoup
import time
import random

def test_nowcoder_crawler():
    """
    测试牛客网爬虫的核心功能
    """
    print("=== 测试牛客网爬虫 ===")
    
    base_url = "https://www.nowcoder.com"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.nowcoder.com/discuss/interview?orderType=3&companyId=0&tagId=0"
    }
    
    # 测试1: 获取面经列表
    print("\n1. 测试获取面经列表...")
    list_url = f"{base_url}/discuss?type=2&order=3&page=1"
    
    try:
        response = requests.get(list_url, headers=headers)
        response.raise_for_status()
        print(f"   列表页面状态码: {response.status_code}")
        
        soup = BeautifulSoup(response.text, "html.parser")
        all_links = soup.find_all("a", href=True)
        
        interviews = []
        seen_urls = set()
        
        for link in all_links:
            href = link.get("href", "")
            text = link.text.strip()
            
            if href.startswith("/discuss/") and text and len(text) > 5:
                detail_url = base_url + href
                if detail_url not in seen_urls:
                    seen_urls.add(detail_url)
                    interviews.append((text, detail_url))
        
        print(f"   找到 {len(interviews)} 条面经")
        
        # 打印前3条
        for i, (title, url) in enumerate(interviews[:3]):
            print(f"   {i+1}. {title} -> {url}")
            
    except Exception as e:
        print(f"   测试失败: {e}")
        return False
    
    # 测试2: 获取面经详情
    if interviews:
        print("\n2. 测试获取面经详情...")
        title, detail_url = interviews[0]
        print(f"   测试面经: {title}")
        print(f"   URL: {detail_url}")
        
        try:
            response = requests.get(detail_url, headers=headers)
            response.raise_for_status()
            print(f"   详情页面状态码: {response.status_code}")
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 提取内容
            content = ""
            content_div = None
            
            # 尝试不同的选择器
            selectors = [
                {"class": lambda x: x and "content" in x},
                {"class": lambda x: x and "post" in x},
                {"class": "nc-post-content"}
            ]
            
            for selector in selectors:
                content_div = soup.find("div", **selector)
                if content_div:
                    break
            
            if content_div:
                content = content_div.get_text(separator="\n", strip=True)
                print(f"   成功提取内容 ({len(content)} 字符)")
                print(f"   内容预览: {content[:200]}...")
            else:
                print(f"   未找到内容区域")
                
            # 提取公司信息
            company = ""
            title_tag = soup.find("h1") or soup.find("h2")
            if title_tag:
                import re
                title_text = title_tag.text
                
                # 简单的公司提取
                company_pattern = r"(B站|美的|春秋航空|阿里巴巴|腾讯|百度|京东|字节跳动)"
                company_match = re.search(company_pattern, title_text)
                if company_match:
                    company = company_match.group(1)
                    print(f"   提取到公司: {company}")
            
            return True
            
        except Exception as e:
            print(f"   测试失败: {e}")
            return False
    
    return False

def main():
    """
    主函数
    """
    success = test_nowcoder_crawler()
    
    if success:
        print("\n=== 测试成功！牛客网爬虫可以正常工作 ===")
        return 0
    else:
        print("\n=== 测试失败！请检查爬虫代码 ===")
        return 1

if __name__ == "__main__":
    sys.exit(main())
