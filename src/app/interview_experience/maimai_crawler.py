import os
import sys
import time
import random
from typing import List, Dict, Any, Optional
import requests
import urllib.parse
from bs4 import BeautifulSoup
from utils.logger import logger

class MaimaiCrawler:
    """脉脉面经爬虫类"""

    def __init__(self):
        self.base_url = "https://maimai.cn"
        encoded_referer_query = urllib.parse.quote("面试经验")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": f"https://maimai.cn/web/gossip/search?query={encoded_referer_query}"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_search_url(self, keyword: str = "面试经验", page: int = 1) -> str:
        """获取搜索URL"""
        encoded_keyword = urllib.parse.quote(keyword)
        return f"{self.base_url}/feed/search?query={encoded_keyword}&page={page}"

    def get_interview_list(self, keyword: str = "面试经验", page: int = 1) -> List[Dict[str, Any]]:
        """获取面经列表"""
        try:
            url = self.get_search_url(keyword, page)
            logger.info(f"正在爬取脉脉面经列表: {url}")
            
            response = self.session.get(url)
            response.raise_for_status()
            
            # 检查页面是否是登录页面
            if "登录/注册" in response.text and ("下载脉脉" in response.text or "成就职业梦想" in response.text):
                logger.warning("\n" + "="*60)
                logger.warning("脉脉需要登录才能访问搜索内容！")
                logger.warning("建议解决方案：")
                logger.warning("1. 手动登录脉脉，获取cookies后添加到session中")
                logger.warning("2. 使用selenium或playwright等工具模拟登录")
                logger.warning("3. 使用脉脉APP的API接口（如果有）")
                logger.warning("="*60)
                return []
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 尝试多种可能的选择器
            gossip_list = []
            
            # 选择器1: 通用的gossip-item
            gossip_list = soup.find_all("div", class_="gossip-item")
            
            # 选择器2: 可能的feed-item类
            if not gossip_list:
                gossip_list = soup.find_all("div", class_="feed-item")
            
            # 选择器3: 可能的content类
            if not gossip_list:
                gossip_list = soup.find_all("div", class_="content")
            
            interviews = []
            for item in gossip_list:
                try:
                    # 获取标题和链接
                    title_tag = item.find("a", class_="gossip-title")
                    if not title_tag:
                        continue
                    
                    title = title_tag.text.strip()
                    href = title_tag.get("href", "")
                    if not href or not href.startswith("/web/gossip/"):
                        continue
                    detail_url = self.base_url + href
                    
                    # 获取内容预览
                    content_preview = ""
                    content_tag = item.find("div", class_="gossip-content")
                    if content_tag:
                        content_preview = content_tag.text.strip()
                    
                    # 获取作者和时间
                    info_tag = item.find("div", class_="gossip-info")
                    author = ""
                    publish_time = ""
                    if info_tag:
                        author_tag = info_tag.find("a", class_="user-name")
                        if author_tag:
                            author = author_tag.text.strip()
                        time_tag = info_tag.find("span", class_="publish-time")
                        if time_tag:
                            publish_time = time_tag.text.strip()
                    
                    # 获取点赞和评论数
                    stats_tag = item.find("div", class_="gossip-stats")
                    likes = 0
                    comments = 0
                    if stats_tag:
                        like_tag = stats_tag.find("span", class_="like-count")
                        if like_tag:
                            likes = int(like_tag.text.strip()) if like_tag.text.strip().isdigit() else 0
                        comment_tag = stats_tag.find("span", class_="comment-count")
                        if comment_tag:
                            comments = int(comment_tag.text.strip()) if comment_tag.text.strip().isdigit() else 0
                    
                    interviews.append({
                        "title": title,
                        "url": detail_url,
                        "content_preview": content_preview,
                        "author": author,
                        "publish_time": publish_time,
                        "likes": likes,
                        "comments": comments
                    })
                except Exception as e:
                    logger.error(f"解析脉脉面经列表项失败: {e}")
                    continue
            
            logger.info(f"成功爬取 {len(interviews)} 条脉脉面经列表项")
            return interviews
        except Exception as e:
            logger.error(f"获取脉脉面经列表失败: {e}")
            return []

    def get_interview_detail(self, url: str) -> Optional[Dict[str, Any]]:
        """获取面经详情"""
        try:
            logger.info(f"正在爬取脉脉面经详情: {url}")
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 获取完整内容
            content_tag = soup.find("div", class_="gossip-detail-content")
            content = ""
            if content_tag:
                # 移除脚本和样式
                for script in content_tag.find_all("script"):
                    script.decompose()
                for style in content_tag.find_all("style"):
                    style.decompose()
                content = content_tag.get_text(separator="\n", strip=True)
            
            # 获取公司信息（如果有）
            company = ""
            company_tag = soup.find("div", class_="company-info")
            if company_tag:
                company = company_tag.text.strip()
            
            # 获取职位信息（如果有）
            position = ""
            position_tag = soup.find("div", class_="position-info")
            if position_tag:
                position = position_tag.text.strip()
            
            return {
                "url": url,
                "content": content,
                "company": company,
                "position": position
            }
        except Exception as e:
            logger.error(f"获取脉脉面经详情失败: {e}")
            return None

    def crawl(self, keyword: str = "面试经验", start_page: int = 1, end_page: int = 10) -> List[Dict[str, Any]]:
        """批量爬取脉脉面经
        keyword: 搜索关键词
        start_page: 起始页数
        end_page: 结束页数
        """
        all_interviews = []
        
        for page in range(start_page, end_page + 1):
            logger.info(f"正在爬取第 {page} 页面经")
            
            # 获取面经列表
            interview_list = self.get_interview_list(keyword, page)
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
                time.sleep(random.uniform(2, 4))
            
            # 每爬完一页添加更长的延迟
            if page < end_page:
                time.sleep(random.uniform(8, 15))
        
        logger.success(f"脉脉面经爬取完成，共获取 {len(all_interviews)} 条面经")
        return all_interviews


if __name__ == "__main__":
    """测试爬虫"""
    crawler = MaimaiCrawler()
    interviews = crawler.crawl(keyword="面试经验", start_page=1, end_page=2)
    
    # 打印结果
    for i, interview in enumerate(interviews[:5]):
        logger.info(f"面经 {i+1}:")
        logger.info(f"标题: {interview.get('title')}")
        logger.info(f"公司: {interview.get('company')}")
        logger.info(f"职位: {interview.get('position')}")
        logger.info(f"URL: {interview.get('url')}")
        logger.info(f"内容前100字: {interview.get('content', '')[:100]}...")
        logger.info("=" * 50)
