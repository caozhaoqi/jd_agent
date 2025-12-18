#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from dotenv import load_dotenv
from atlassian import Confluence

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


# 创建Confluence客户端
def create_confluence_client():
    print("创建Confluence客户端...")

    # 选择认证方式：优先使用API Token，其次使用密码
    if CONFLUENCE_API_TOKEN:
        # 使用API Token认证
        password = CONFLUENCE_API_TOKEN
        print("使用API Token进行认证")
    else:
        # 使用用户名密码认证
        password = CONFLUENCE_PASSWORD
        print("使用用户名密码进行认证")

    try:
        confluence = Confluence(
            url=CONFLUENCE_URL,
            username=CONFLUENCE_USERNAME,
            password=password,
            proxies={},
            cloud=False,  # 企业内部服务器设置为False
        )

        # 测试连接
        confluence.get_all_spaces(start=0, limit=1)
        print("✅ Confluence服务器连接成功")

        return confluence
    except Exception as e:
        print(f"❌ Confluence服务器连接失败: {e}")
        return None


# 测试获取文档内容
def test_get_document_content(confluence, page_id):
    print(f"\n测试获取文档内容: {page_id}")

    try:
        page = confluence.get_page_by_id(page_id, expand="body.storage,space,version")

        if page:
            print("✅ 获取文档内容成功")
            print("\n文档信息:")
            print(f"标题: {page.get('title')}")
            print(f"空间: {page.get('space', {}).get('name')}")
            print(f"类型: {page.get('type')}")
            print(f"版本: {page.get('version', {}).get('number')}")

            # 获取文档内容
            content = page.get("body", {}).get("storage", {}).get("value", "")
            print("\n文档内容 (前500字符):")
            print(content[:500] + "...") if len(content) > 500 else print(content)

            return page
        else:
            print("❌ 无法获取文档内容")
            return None
    except Exception as e:
        print(f"❌ 获取文档内容异常: {e}")
        return None


# 测试获取文档版本历史
def test_get_document_history(confluence, page_id):
    print(f"\n测试获取文档版本历史: {page_id}")

    try:
        page = confluence.get_page_by_id(page_id, expand="history,version")

        if page:
            print("✅ 获取文档版本历史成功")
            print("\n版本历史:")
            print(f"当前版本: {page.get('version', {}).get('number')}")
            print(f"创建时间: {page.get('history', {}).get('createdDate')}")
            print(
                f"创建者: {page.get('history', {}).get('createdBy', {}).get('displayName')}"
            )
            print(f"最后更新时间: {page.get('version', {}).get('when')}")
            print(
                f"最后更新者: {page.get('version', {}).get('by', {}).get('displayName')}"
            )

            return page
        else:
            print("❌ 无法获取文档版本历史")
            return None
    except Exception as e:
        print(f"❌ 获取文档版本历史异常: {e}")
        return None


# 测试获取文档评论
def test_get_document_comments(confluence, page_id):
    print(f"\n测试获取文档评论: {page_id}")

    try:
        comments = confluence.get_page_child_by_type(page_id, type="comment")

        if comments:
            print(f"✅ 获取文档评论成功，共 {len(comments)} 条评论")

            for i, comment in enumerate(comments[:5]):  # 只显示前5条
                print(f"\n评论 {i+1}:")
                print(f"作者: {comment.get('creator', {}).get('displayName')}")
                print(f"创建时间: {comment.get('createdDate')}")
                print(
                    f"内容: {comment.get('body', {}).get('storage', {}).get('value', '')[:200]}..."
                )

            if len(comments) > 5:
                print(f"\n... 还有 {len(comments) - 5} 条评论")

            return comments
        else:
            print("❌ 无法获取文档评论")
            return None
    except Exception as e:
        print(f"❌ 获取文档评论异常: {e}")
        return None


if __name__ == "__main__":
    # 测试页面ID（用户可以根据需要修改）
    test_page_id = "38718986"

    print("=== Confluence API测试 (使用atlassian-python-api) ===")
    print(f"Confluence URL: {CONFLUENCE_URL}")
    print(f"用户名: {CONFLUENCE_USERNAME}")

    # 创建Confluence客户端
    confluence = create_confluence_client()

    if confluence:
        # 测试获取文档内容
        test_get_document_content(confluence, test_page_id)

        # 测试获取文档版本历史
        test_get_document_history(confluence, test_page_id)

        # 测试获取文档评论
        test_get_document_comments(confluence, test_page_id)
