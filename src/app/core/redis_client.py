import redis
from app.core.config import settings
from loguru import logger
import json
from typing import Any, Optional
from app.core.monitoring import (
    redis_cache_hits,
    redis_cache_misses,
    redis_commands_total,
)


class RedisClient:
    """
    Redis 客户端类，用于处理 Redis 连接和缓存操作
    """

    def __init__(self):
        self.redis_url = settings.effective_redis_url
        self.redis_client = None
        self.connect()

    def connect(self):
        """
        连接到 Redis 服务器
        """
        try:
            redis_kwargs = {
                "decode_responses": True,
                "socket_connect_timeout": settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                "socket_timeout": settings.REDIS_SOCKET_TIMEOUT,
                "retry_on_timeout": settings.REDIS_RETRY_ON_TIMEOUT,
                "max_connections": settings.REDIS_MAX_CONNECTIONS,
                "health_check_interval": 30,  # 健康检查间隔
            }

            if settings.REDIS_PASSWORD:
                redis_kwargs["password"] = settings.REDIS_PASSWORD

            self.redis_client = redis.from_url(self.redis_url, **redis_kwargs)

            # 测试连接
            self.redis_client.ping()
            logger.info(f"✅ [Redis] Connected to Redis server at {self.redis_url}")
        except Exception as e:
            logger.error(f"❌ [Redis] Failed to connect to Redis: {e}")
            self.redis_client = None

    def get(self, key: str) -> Optional[Any]:
        """
        从缓存中获取数据
        """
        if not self.redis_client:
            logger.warning("⚠️ [Redis] Redis client not connected, skipping cache get")
            return None

        try:
            # 记录Redis命令执行
            redis_commands_total.labels(command="get").inc()

            value = self.redis_client.get(key)
            if value:
                # 记录缓存命中
                redis_cache_hits.inc()
                return json.loads(value)
            # 记录缓存未命中
            redis_cache_misses.inc()
            return None
        except Exception as e:
            logger.error(f"❌ [Redis] Failed to get key {key}: {e}")
            return None

    def set(self, key: str, value: Any, expire_seconds: int = 3600) -> bool:
        """
        设置缓存数据
        """
        if not self.redis_client:
            logger.warning("⚠️ [Redis] Redis client not connected, skipping cache set")
            return False

        # 辅助函数：递归处理数据，确保可序列化
        def make_serializable(data):
            if isinstance(data, dict):
                # 确保字典的键都是字符串
                return {str(k): make_serializable(v) for k, v in data.items()}
            elif isinstance(data, list):
                return [make_serializable(item) for item in data]
            elif isinstance(data, (str, int, float, bool, type(None))):
                return data
            elif hasattr(data, "to_json"):
                # 处理带有 to_json 方法的对象（如 LangChain 的 BaseMessage）
                try:
                    data_json = data.to_json()
                    return make_serializable(data_json)
                except Exception:
                    return str(data)
            elif hasattr(data, "dict"):
                # 处理 Pydantic 模型和其他带 dict 方法的对象
                try:
                    data_dict = data.dict()
                    return make_serializable(data_dict)
                except Exception:
                    return str(data)
            elif hasattr(data, "__dict__"):
                # 处理普通对象
                try:
                    # 尝试将对象转换为字典
                    obj_dict = {
                        k: v for k, v in data.__dict__.items() if not k.startswith("_")
                    }
                    return make_serializable(obj_dict)
                except Exception:
                    return str(data)
            else:
                return str(data)

        try:
            logger.debug(
                f"📦 [Redis] Setting key: {key}, value type: {type(value).__name__}"
            )

            # 记录Redis命令执行
            redis_commands_total.labels(command="setex").inc()

            # 先处理数据，确保可序列化
            serializable_value = make_serializable(value)
            logger.debug(
                f"🔄 [Redis] Made value serializable, new type: {type(serializable_value).__name__}"
            )

            json_value = json.dumps(serializable_value)
            logger.debug(f"📝 [Redis] Successfully serialized value to JSON")

            self.redis_client.setex(key, expire_seconds, json_value)
            logger.debug(f"✅ [Redis] Successfully set key: {key}")
            return True
        except Exception as e:
            logger.error(f"❌ [Redis] Failed to set key {key}: {e}")
            logger.error(f"❌ [Redis] Failed value type: {type(value).__name__}")
            logger.error(f"❌ [Redis] Failed value details: {value}")
            import traceback

            logger.error(f"❌ [Redis] Full traceback: {traceback.format_exc()}")
            return False

    def delete(self, key: str) -> bool:
        """
        删除缓存数据
        """
        if not self.redis_client:
            logger.warning(
                "⚠️ [Redis] Redis client not connected, skipping cache delete"
            )
            return False

        try:
            # 记录Redis命令执行
            redis_commands_total.labels(command="delete").inc()

            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"❌ [Redis] Failed to delete key {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """
        检查缓存数据是否存在
        """
        if not self.redis_client:
            logger.warning(
                "⚠️ [Redis] Redis client not connected, skipping cache exists check"
            )
            return False

        try:
            # 记录Redis命令执行
            redis_commands_total.labels(command="exists").inc()

            return self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"❌ [Redis] Failed to check key {key} existence: {e}")
            return False


# 创建 Redis 客户端实例
redis_client = RedisClient()
