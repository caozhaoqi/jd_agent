#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import requests
from dotenv import load_dotenv
from base64 import b64encode

# 加载.env文件
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path)

# 从环境变量获取Confluence配置
CONFLUENCE_URL = os.getenv("CONFLUENCE_URL", "")
CONFLUENCE_USERNAME = os.getenv("CONFLUENCE_USERNAME")
CONFLUENCE_PASSWORD = os.getenv("CONFLUENCE_PASSWORD")
CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")

if not CONFLUENCE_USERNAME or not (CONFLUENCE_PASSWORD or CONFLUENCE_API_TOKEN):
    print(
        "错误: 请在.env文件中配置CONFLUENCE_USERNAME和CONFLUENCE_PASSWORD/CONFLUENCE_API_TOKEN"
    )
    sys.exit(1)

# 选择认证方式：优先使用API Token，其次使用密码
if CONFLUENCE_API_TOKEN:
    # 使用API Token认证
    auth = (CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN)
    print("使用API Token进行认证")
else:
    # 使用用户名密码认证
    auth = (CONFLUENCE_USERNAME, CONFLUENCE_PASSWORD)
    print("使用用户名密码进行认证")


# 测试用户提供的API方法：获取文档内容
def test_get_document_content(page_id):
    url = f"{CONFLUENCE_URL}/rest/api/content/{page_id}?expand=body.storage"
    print(f"\n测试API: GET {url}")

    try:
        response = requests.get(url, auth=auth)

        if response.status_code == 200:
            print("✅ API请求成功")
            data = response.json()
            print("\n文档信息:")
            print(f"标题: {data.get('title')}")
            print(f"空间: {data.get('space', {}).get('name')}")
            print(f"类型: {data.get('type')}")
            print(f"版本: {data.get('version', {}).get('number')}")

            # 获取文档内容
            content = data.get("body", {}).get("storage", {}).get("value", "")
            print("\n文档内容 (前500字符):")
            print(content[:500] + "...") if len(content) > 500 else print(content)

            return data
        else:
            print(f"❌ API请求失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            return None
    except Exception as e:
        print(f"❌ API请求异常: {e}")
        return None


# 测试获取文档版本历史
def test_get_document_history(page_id):
    url = f"{CONFLUENCE_URL}/rest/api/content/{page_id}?expand=history,version"
    print(f"\n测试API: GET {url}")

    try:
        response = requests.get(url, auth=auth)

        if response.status_code == 200:
            print("✅ API请求成功")
            data = response.json()

            print("\n版本历史:")
            print(f"当前版本: {data.get('version', {}).get('number')}")
            print(f"创建时间: {data.get('history', {}).get('createdDate')}")
            print(
                f"创建者: {data.get('history', {}).get('createdBy', {}).get('displayName')}"
            )
            print(f"最后更新时间: {data.get('version', {}).get('when')}")
            print(
                f"最后更新者: {data.get('version', {}).get('by', {}).get('displayName')}"
            )

            return data
        else:
            print(f"❌ API请求失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            return None
    except Exception as e:
        print(f"❌ API请求异常: {e}")
        return None


# 测试获取文档评论
def test_get_document_comments(page_id):
    url = f"{CONFLUENCE_URL}/rest/api/content/{page_id}/child/comment"
    print(f"\n测试API: GET {url}")

    try:
        response = requests.get(url, auth=auth)

        if response.status_code == 200:
            print("✅ API请求成功")
            data = response.json()

            comments = data.get("results", [])
            print(f"\n评论数: {len(comments)}")

            for i, comment in enumerate(comments[:5]):  # 只显示前5条
                print(f"\n评论 {i+1}:")
                print(f"作者: {comment.get('creator', {}).get('displayName')}")
                print(f"创建时间: {comment.get('createdDate')}")
                print(
                    f"内容: {comment.get('body', {}).get('storage', {}).get('value', '')[:200]}..."
                )

            if len(comments) > 5:
                print(f"\n... 还有 {len(comments) - 5} 条评论")

            return data
        else:
            print(f"❌ API请求失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            return None
    except Exception as e:
        print(f"❌ API请求异常: {e}")
        return None


if __name__ == "__main__":
    # 测试页面ID（用户可以根据需要修改）
    test_page_id = "38718986"

    print("=== Confluence API测试 ===")
    print(f"Confluence URL: {CONFLUENCE_URL}")
    print(f"用户名: {CONFLUENCE_USERNAME}")

    # 测试获取文档内容
    test_get_document_content(test_page_id)

    # 测试获取文档版本历史
    test_get_document_history(test_page_id)

    # 测试获取文档评论
    test_get_document_comments(test_page_id)
