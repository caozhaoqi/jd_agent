import redis
from core.settings import settings
from loguru import logger
import json
import gzip
import pickle
from typing import Any, Optional, Dict
from core.monitoring import (
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
        self.connection_pool = None
        self.is_connected = False
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0
        }
        self.connect()

    def connect(self):
        """
        连接到 Redis 服务器 - 优化连接配置
        """
        try:
            # 连接池配置
            redis_kwargs = {
                "decode_responses": True,
                "socket_connect_timeout": settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                "socket_timeout": settings.REDIS_SOCKET_TIMEOUT,
                "retry_on_timeout": settings.REDIS_RETRY_ON_TIMEOUT,
                "max_connections": settings.REDIS_MAX_CONNECTIONS,
                "health_check_interval": settings.REDIS_HEALTH_CHECK_INTERVAL,
                "connection_pool_class": redis.ConnectionPool,
                "socket_keepalive": True,
                "socket_keepalive_options": {},
            }

            if settings.REDIS_PASSWORD:
                redis_kwargs["password"] = settings.REDIS_PASSWORD

            # 创建连接池
            from urllib.parse import urlparse
            parsed_url = urlparse(self.redis_url)
            
            self.connection_pool = redis.ConnectionPool(
                host=parsed_url.hostname or 'localhost',
                port=parsed_url.port or 6379,
                password=parsed_url.password,
                db=int(parsed_url.path.strip('/')) if parsed_url.path and parsed_url.path.strip('/').isdigit() else 0,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                retry_on_timeout=settings.REDIS_RETRY_ON_TIMEOUT,
                health_check_interval=settings.REDIS_HEALTH_CHECK_INTERVAL,
                decode_responses=False  # 我们自己处理序列化
            )

            # 创建客户端
            self.redis_client = redis.Redis(connection_pool=self.connection_pool)

            # 测试连接
            self.redis_client.ping()
            self.is_connected = True
            logger.info(f"✅ [Redis] Connected to Redis server at {self.redis_url}")
            logger.info(f"🔧 [Redis] Connection pool configured with {settings.REDIS_MAX_CONNECTIONS} max connections")
            
        except Exception as e:
            self.is_connected = False
            logger.error(f"❌ [Redis] Failed to connect to Redis: {e}")
            self.redis_client = None
            self.stats["errors"] += 1

    def get(self, key: str, prefix: str = "") -> Optional[Any]:
        """
        从缓存中获取数据 - 支持智能前缀和压缩
        """
        if not self.redis_client or not self.is_connected:
            logger.warning("⚠️ [Redis] Redis client not connected, skipping cache get")
            self.stats["misses"] += 1
            return None

        try:
            # 添加前缀
            full_key = f"{prefix}{key}" if prefix else key
            
            # 记录Redis命令执行
            redis_commands_total.labels(command="get").inc()

            value = self.redis_client.get(full_key)
            if value:
                # 记录缓存命中
                redis_cache_hits.inc()
                self.stats["hits"] += 1
                
                # 解压缩（如果启用）
                if settings.CACHE_COMPRESSION and len(value) > settings.CACHE_COMPRESSION_THRESHOLD:
                    try:
                        # 尝试gzip解压缩
                        decompressed = gzip.decompress(value)
                        return pickle.loads(decompressed)
                    except Exception:
                        # 如果解压失败，尝试JSON
                        return json.loads(value)
                else:
                    return json.loads(value)
            
            # 记录缓存未命中
            redis_cache_misses.inc()
            self.stats["misses"] += 1
            return None
            
        except Exception as e:
            logger.error(f"❌ [Redis] Failed to get key {full_key}: {e}")
            self.stats["errors"] += 1
            return None

    def set(self, key: str, value: Any, expire_seconds: int = None, prefix: str = "", cache_type: str = "default") -> bool:
        """
        设置缓存数据 - 支持智能压缩和分类缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            expire_seconds: 过期时间，如果为None则根据缓存类型自动设置
            prefix: 键前缀
            cache_type: 缓存类型 (default, short, medium, long, llm)
        """
        if not self.redis_client or not self.is_connected:
            logger.warning("⚠️ [Redis] Redis client not connected, skipping cache set")
            self.stats["errors"] += 1
            return False

        # 自动设置过期时间
        if expire_seconds is None:
            ttl_map = {
                "default": settings.CACHE_TTL_DEFAULT,
                "short": settings.CACHE_TTL_SHORT,
                "medium": settings.CACHE_TTL_MEDIUM,
                "long": settings.CACHE_TTL_LONG,
                "llm": settings.CACHE_TTL_LLM
            }
            expire_seconds = ttl_map.get(cache_type, settings.CACHE_TTL_DEFAULT)

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
            # 添加前缀
            full_key = f"{prefix}{key}" if prefix else key
            
            logger.debug(
                f"📦 [Redis] Setting key: {full_key}, type: {cache_type}, expire: {expire_seconds}s, value type: {type(value).__name__}"
            )

            # 记录Redis命令执行
            redis_commands_total.labels(command="setex").inc()

            # 先处理数据，确保可序列化
            serializable_value = make_serializable(value)

            # 序列化数据
            if settings.CACHE_COMPRESSION and len(str(serializable_value)) > settings.CACHE_COMPRESSION_THRESHOLD:
                # 使用压缩
                json_value = json.dumps(serializable_value)
                compressed_value = gzip.compress(json_value.encode('utf-8'))
                final_value = compressed_value
                logger.debug(f"🗜️ [Redis] Data compressed: {len(json_value)} -> {len(compressed_value)} bytes")
            else:
                # 不使用压缩
                final_value = json.dumps(serializable_value).encode('utf-8')

            # 存储到Redis
            self.redis_client.setex(full_key, expire_seconds, final_value)
            logger.debug(f"✅ [Redis] Successfully set key: {full_key}")
            
            self.stats["sets"] += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ [Redis] Failed to set key {full_key}: {e}")
            logger.error(f"❌ [Redis] Failed value type: {type(value).__name__}")
            logger.error(f"❌ [Redis] Failed value details: {value}")
            import traceback
            logger.error(f"❌ [Redis] Full traceback: {traceback.format_exc()}")
            self.stats["errors"] += 1
            return False

    def delete(self, key: str, prefix: str = "") -> bool:
        """
        删除缓存数据 - 支持前缀
        """
        if not self.redis_client or not self.is_connected:
            logger.warning("⚠️ [Redis] Redis client not connected, skipping cache delete")
            self.stats["errors"] += 1
            return False

        try:
            # 添加前缀
            full_key = f"{prefix}{key}" if prefix else key
            
            # 记录Redis命令执行
            redis_commands_total.labels(command="delete").inc()

            result = self.redis_client.delete(full_key)
            if result:
                self.stats["deletes"] += 1
                logger.debug(f"✅ [Redis] Successfully deleted key: {full_key}")
            return result > 0
            
        except Exception as e:
            logger.error(f"❌ [Redis] Failed to delete key {full_key}: {e}")
            self.stats["errors"] += 1
            return False

    def exists(self, key: str, prefix: str = "") -> bool:
        """
        检查缓存数据是否存在 - 支持前缀
        """
        if not self.redis_client or not self.is_connected:
            logger.warning("⚠️ [Redis] Redis client not connected, skipping cache exists check")
            return False

        try:
            # 添加前缀
            full_key = f"{prefix}{key}" if prefix else key
            
            # 记录Redis命令执行
            redis_commands_total.labels(command="exists").inc()

            return self.redis_client.exists(full_key) > 0
        except Exception as e:
            logger.error(f"❌ [Redis] Failed to check key {full_key} existence: {e}")
            self.stats["errors"] += 1
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        """
        return {
            **self.stats,
            "hit_rate": self.stats["hits"] / max(self.stats["hits"] + self.stats["misses"], 1),
            "is_connected": self.is_connected,
            "connection_pool_size": self.connection_pool.max_connections if self.connection_pool else 0
        }

    def cleanup_expired(self, prefix: str = "") -> int:
        """
        清理过期的缓存键
        """
        if not self.redis_client or not self.is_connected:
            logger.warning("⚠️ [Redis] Redis client not connected, skipping cleanup")
            return 0

        try:
            # 扫描并清理过期键
            pattern = f"{prefix}*" if prefix else "*"
            keys = self.redis_client.keys(pattern)
            
            expired_count = 0
            for key in keys:
                ttl = self.redis_client.ttl(key)
                if ttl == -1:  # -1表示键没有设置过期时间
                    continue
                elif ttl < 0:  # 负值表示键已过期
                    self.redis_client.delete(key)
                    expired_count += 1
            
            if expired_count > 0:
                logger.info(f"🧹 [Redis] Cleaned up {expired_count} expired keys with prefix: {prefix}")
            
            return expired_count
            
        except Exception as e:
            logger.error(f"❌ [Redis] Failed to cleanup expired keys: {e}")
            return 0

    def close(self):
        """
        关闭Redis连接
        """
        try:
            if self.redis_client:
                self.redis_client.close()
            if self.connection_pool:
                self.connection_pool.disconnect()
            self.is_connected = False
            logger.info("🔌 [Redis] Connection closed")
        except Exception as e:
            logger.error(f"❌ [Redis] Failed to close connection: {e}")

    def __del__(self):
        """
        析构函数，确保连接被正确关闭
        """
        self.close()


# 创建 Redis 客户端实例
redis_client = RedisClient()
