import sys
import os
from loguru import logger

# 1. 确保日志目录存在
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 2. 移除默认的 handler (避免重复)
logger.remove()

# 3. 添加控制台输出 (带颜色，适合开发)
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)

# 4. 添加文件输出 (适合生产排查)
# rotation="1 day": 每天生成一个新文件
# retention="10 days": 只保留最近10天的日志
logger.add(
    os.path.join(LOG_DIR, "app_{time:YYYY-MM-DD}.log"),
    rotation="1 day",
    retention="10 days",
    level="DEBUG",
    encoding="utf-8"
)

# 导出配置好的 logger
__all__ = ["logger"]