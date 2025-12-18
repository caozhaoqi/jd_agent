#!/usr/bin/env python3
"""
Confluence连接测试脚本

使用方法：
1. 直接运行此脚本
2. 按照提示输入Confluence服务器地址、用户名和API Token
3. 脚本会测试连接是否成功
"""

import os
import sys
from getpass import getpass

# 添加src目录到Python搜索路径
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from app.utils.logger import logger
from atlassian import Confluence


def test_confluence_connection():
    """测试Confluence连接"""
    logger.info("🚀 开始测试Confluence连接...")

    try:
        # 获取用户输入
        url = input("请输入Confluence服务器地址")
        username = input("请输入用户名: ")

        if not username:
            logger.error("❌ 用户名不能为空")
            return False

        # 使用getpass安全输入密码/API Token
        password = getpass("请输入API Token或密码: ")

        if not password:
            logger.error("❌ 密码/API Token不能为空")
            return False

        # 测试连接
        logger.info(f"🔌 正在连接到: {url}")

        confluence = Confluence(
            url=url,
            username=username,
            password=password,
            cloud=False,  # 企业内部服务器设置为False
        )

        # 测试API调用
        spaces = confluence.get_all_spaces(start=0, limit=5)

        if spaces and spaces.get("results"):
            logger.success("✅ Confluence连接成功!")
            logger.info(f"📊 发现 {len(spaces['results'])} 个空间")

            # 显示前几个空间
            for i, space in enumerate(spaces["results"][:3]):
                logger.info(f"   {i+1}. {space.get('name')} (key: {space.get('key')})")

            return True
        else:
            logger.warning("⚠️ 连接成功，但没有找到任何空间")
            return True

    except Exception as e:
        logger.error(f"❌ 连接失败: {e}")
        logger.info("💡 请检查:")
        logger.info("   1. 服务器地址是否正确")
        logger.info("   2. 用户名和API Token是否正确")
        logger.info("   3. 网络连接是否正常")
        logger.info("   4. API Token是否有足够的权限")
        return False


if __name__ == "__main__":
    test_confluence_connection()
