#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from dotenv import load_dotenv
from atlassian import Confluence

# 加载.env文件
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

# 从环境变量获取Confluence配置
CONFLUENCE_URL = os.getenv('CONFLUENCE_URL', 'https://w.cn')
CONFLUENCE_USERNAME = os.getenv('CONFLUENCE_USERNAME')
CONFLUENCE_PASSWORD = os.getenv('CONFLUENCE_PASSWORD')

if not CONFLUENCE_USERNAME or not CONFLUENCE_PASSWORD:
    print("错误: 请在.env文件中配置CONFLUENCE_USERNAME和CONFLUENCE_PASSWORD")
    sys.exit(1)

# 创建Confluence客户端
def create_confluence_client():
    print("创建Confluence客户端...")
    print(f"Confluence URL: {CONFLUENCE_URL}")
    print(f"用户名: {CONFLUENCE_USERNAME}")
    print(f"密码: {CONFLUENCE_PASSWORD}")
    
    try:
        confluence = Confluence(
            url=CONFLUENCE_URL,
            username=CONFLUENCE_USERNAME,
            password=CONFLUENCE_PASSWORD,
            proxies={},
            cloud=False  # 企业内部服务器设置为False
        )
        
        # 测试连接
        spaces = confluence.get_all_spaces(start=0, limit=1)
        print("✅ Confluence服务器连接成功")
        print(f"测试连接结果: {spaces}")
        
        return confluence
    except Exception as e:
        print(f"❌ Confluence服务器连接失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("=== Confluence API测试 (仅使用用户名密码) ===")
    
    # 创建Confluence客户端
    confluence = create_confluence_client()
