#!/usr/bin/env python3
"""
测试更新后的牛客网爬虫
"""
import sys
import os

# 获取当前脚本的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录
project_root = os.path.dirname(current_dir)
# 将src目录添加到Python路径，这样app模块可以被正确导入
sys.path.insert(0, os.path.join(project_root, 'src'))

# 现在应该可以正确导入了
from app.interview_experience.nowcoder_crawler import NowCoderCrawler

def test_crawler():
    """测试爬虫功能"""
    print("测试牛客网面经爬虫...")
    crawler = NowCoderCrawler()
    
    # 测试获取面经列表
    print("\n1. 测试获取面经列表...")
    interviews = crawler.get_interview_list(page=1, order_type=3)
    
    if not interviews:
        print("错误：未获取到面经列表")
        return False
    
    print(f"成功获取到 {len(interviews)} 条面经")
    
    # 打印前3条面经信息
    print("\n前3条面经信息：")
    for i, interview in enumerate(interviews[:3]):
        print(f"\n{i+1}. 标题: {interview['title']}")
        print(f"   URL: {interview['url']}")
        print(f"   作者: {interview['author']}")
        print(f"   发布时间: {interview['publish_time']}")
    
    # 测试获取面经详情
    print("\n2. 测试获取面经详情...")
    if interviews:
        first_interview = interviews[0]
        detail = crawler.get_interview_detail(first_interview['url'])
        
        if detail:
            print(f"成功获取面经详情")
            print(f"   公司: {detail['company']}")
            print(f"   职位: {detail['position']}")
            print(f"   内容前100字: {detail['content'][:100]}...")
        else:
            print("警告：未获取到面经详情")
    
    print("\n测试完成！")
    return True

if __name__ == "__main__":
    test_crawler()
