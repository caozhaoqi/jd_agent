import os
from typing import Dict, Any
from core.config import settings
from dotenv import load_dotenv

# 获取项目根目录路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))

# 加载项目根目录下的.env文件
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

# 打印配置信息用于调试
print(f"加载的.env文件路径: {env_path}")
print(f"CONFLUENCE_URL: {os.environ.get('CONFLUENCE_URL')}")
print(f"CONFLUENCE_USERNAME: {os.environ.get('CONFLUENCE_USERNAME')}")

class ConfluenceConfig:
    """Confluence配置类"""

    def __init__(self):
        # 从环境变量获取配置，如果环境变量不存在则使用默认值
        self.url = os.environ.get("CONFLUENCE_URL", "https://wiki.hcmcloud.cn")
        self.username = os.environ.get("CONFLUENCE_USERNAME", "hb_1150118968")
        self.password = os.environ.get("CONFLUENCE_PASSWORD", "1JIRAwiki!?")
        self.api_token = os.environ.get("CONFLUENCE_API_TOKEN", "")
        self.spaces = (
            os.environ.get("CONFLUENCE_SPACES", "").split(",")
            if os.environ.get("CONFLUENCE_SPACES")
            else []
        )

        # 代理配置（可选）
        self.proxies = {
            "http": os.environ.get("HTTP_PROXY", ""),
            "https": os.environ.get("HTTPS_PROXY", ""),
        }

        # 移除空代理配置
        self.proxies = {k: v for k, v in self.proxies.items() if v}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "url": self.url,
            "username": self.username,
            "password": "********" if self.password else "",
            "api_token": "********" if self.api_token else "",
            "spaces": self.spaces,
            "proxies": self.proxies,
        }


# 创建全局配置实例
confluence_config = ConfluenceConfig()
