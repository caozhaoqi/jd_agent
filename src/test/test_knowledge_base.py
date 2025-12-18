#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试知识库查询功能
"""

import sys
import os

# 设置PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app.confluence.confluence_kb import ConfluenceKnowledgeBase

def test_knowledge_base():
    """测试知识库功能"""
    print("=== 知识库查询功能测试 ===\n")
    
    # 创建知识库实例
    kb = ConfluenceKnowledgeBase()
    
    # 加载页面数据
    all_pages = kb.load_all_pages()
    print(f"已加载 {len(all_pages)} 个知识库页面\n")
    
    # 测试搜索功能
    test_keywords = ["HCM Cloud", "流程", "薪酬"]
    
    for keyword in test_keywords:
        print(f"测试搜索关键词: '{keyword}'")
        results = kb.search_pages(keyword, top_k=3)
        
        if results:
            print(f"找到 {len(results)} 个相关页面:")
            for i, page in enumerate(results, 1):
                print(f"  {i}. {page['title']} (匹配度: {page['_score']})")
        else:
            print("没有找到相关页面")
        
        print()
    
    # 测试问答功能
    test_questions = [
        # "
    ]
    
    for question in test_questions:
        print(f"测试问答: '{question}'")
        answer = kb.get_answer(question, top_k=2)
        print(f"回答: {answer}")
        print()

if __name__ == "__main__":
    test_knowledge_base()
