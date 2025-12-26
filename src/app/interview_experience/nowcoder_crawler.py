import os
import sys
import time
import random
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
from app.utils.logger import logger

class NowCoderCrawler:
    """牛客网面经爬虫类"""

    def __init__(self):
        self.base_url = "https://www.nowcoder.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.nowcoder.com/discuss/interview?orderType=3&companyId=0&tagId=0"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_category_url(self, category: str = "all", order_type: int = 3, page: int = 1) -> str:
        """获取面经分类URL
        order_type: 排序类型 1:最新 2:最热 3:精华
        """
        return f"{self.base_url}/discuss?type=2&order={order_type}&page={page}"

    def get_interview_list(self, category: str = "all", order_type: int = 3, page: int = 1) -> List[Dict[str, Any]]:
        """获取面经列表"""
        try:
            url = self.get_category_url(category, order_type, page)
            
            logger.info(f"正在爬取牛客面经列表: {url}")
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 查找所有链接
            all_links = soup.find_all("a", href=True)
            
            interviews = []
            seen_urls = set()
            
            # 过滤出面经相关链接
            for link in all_links:
                href = link.get("href", "")
                text = link.text.strip()
                
                # 只保留以/discuss/开头且有实际文本的链接
                if href.startswith("/discuss/") and text and len(text) > 5:
                    detail_url = self.base_url + href
                    
                    # 去重
                    if detail_url not in seen_urls:
                        seen_urls.add(detail_url)
                        
                        # 简单提取时间信息
                        publish_time = ""
                        import re
                        # 查找包含时间的文本
                        parent_text = link.find_parent().get_text(separator=" ", strip=True)
                        time_pattern = r"(\d{4}-\d{2}-\d{2}|\d{2}-\d{2}|昨天|今天)"
                        time_match = re.search(time_pattern, parent_text)
                        if time_match:
                            publish_time = time_match.group(1)
                    
                        interviews.append({
                            "title": text,
                            "url": detail_url,
                            "author": "",
                            "publish_time": publish_time,
                            "likes": 0,
                            "replies": 0,
                            "tags": []
                        })
            
            logger.info(f"成功爬取 {len(interviews)} 条牛客面经列表项")
            return interviews
        except Exception as e:
            logger.error(f"获取牛客面经列表失败: {e}")
            return []

    def get_interview_detail(self, url: str) -> Optional[Dict[str, Any]]:
        """获取面经详情"""
        try:
            logger.info(f"正在爬取牛客面经详情: {url}")
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 获取内容
            content = ""
            # 尝试多种可能的内容选择器
            content_selectors = [
                {"class": lambda x: x and ("content" in x or "post" in x or "article" in x)},
                {"id": lambda x: x and ("content" in x or "post" in x)},
                {"class": "nc-post-content"}
            ]
            
            for selector in content_selectors:
                content_tag = soup.find("div", **selector)
                if content_tag:
                    # 移除脚本和样式
                    for script in content_tag.find_all("script"):
                        script.decompose()
                    for style in content_tag.find_all("style"):
                        style.decompose()
                    content = content_tag.get_text(separator="\n", strip=True)
                    break
            
            # 获取公司信息
            company = ""
            # 尝试从标题中提取公司信息
            title_tag = soup.find("h1") or soup.find("h2")
            if title_tag:
                title_text = title_tag.text
                # 简单的公司名称提取（可以根据实际情况优化）
                import re
                company_pattern = r"(B站|美的|春秋航空|嵌入式|后端|前端|算法|产品|运营)"
                company_match = re.search(company_pattern, title_text)
                if company_match:
                    company = company_match.group(1)
            
            # 获取职位信息
            position = ""
            if title_tag:
                # 简单的职位提取
                position_pattern = r"(后端|前端|算法|产品|运营|嵌入式|开发|工程师)"
                position_match = re.search(position_pattern, title_tag.text)
                if position_match:
                    position = position_match.group(1)
            
            return {
                "url": url,
                "content": content,
                "company": company,
                "position": position
            }
        except Exception as e:
            logger.error(f"获取牛客面经详情失败: {e}")
            return None

    def crawl(self, start_page: int = 1, end_page: int = 10, order_type: int = 3) -> List[Dict[str, Any]]:
        """批量爬取牛客面经
        start_page: 起始页数
        end_page: 结束页数
        order_type: 排序类型 1:最新 2:最热 3:精华
        """
        all_interviews = []
        
        for page in range(start_page, end_page + 1):
            logger.info(f"正在爬取第 {page} 页面经")
            
            # 获取面经列表
            interview_list = self.get_interview_list(order_type=order_type, page=page)
            if not interview_list:
                logger.warning(f"第 {page} 页未获取到面经列表")
                continue
            
            # 获取每个面经的详情
            for interview in interview_list:
                detail = self.get_interview_detail(interview["url"])
                if detail:
                    interview.update(detail)
                    all_interviews.append(interview)
                
                # 添加随机延迟，避免被封
                time.sleep(random.uniform(1, 3))
            
            # 每爬完一页添加更长的延迟
            if page < end_page:
                time.sleep(random.uniform(5, 10))
        
        logger.success(f"牛客面经爬取完成，共获取 {len(all_interviews)} 条面经")
        return all_interviews


if __name__ == "__main__":
    """测试爬虫"""
    crawler = NowCoderCrawler()
    interviews = crawler.crawl(start_page=1, end_page=2, order_type=3)
    
    # 打印结果
    for i, interview in enumerate(interviews[:5]):
        logger.info(f"面经 {i+1}:")
        logger.info(f"标题: {interview.get('title')}")
        logger.info(f"公司: {interview.get('company')}")
        logger.info(f"职位: {interview.get('position')}")
        logger.info(f"URL: {interview.get('url')}")
        logger.info(f"内容前100字: {interview.get('content', '')[:100]}...")
        logger.info("=" * 50)
