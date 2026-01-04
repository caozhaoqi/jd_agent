"""
简化缓存管理系统
解决当前项目中缺乏缓存机制的问题
"""

import os
import json
import hashlib
import pickle
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger

from core.config import settings
from core.exceptions import CacheError, handle_exceptions


class LocalCache:
    """本地内存缓存"""
    
    def __init__(self, max_size: int = None, ttl: int = None):
        self.max_size = max_size or settings.CACHE_MAX_SIZE
        self.ttl = ttl or settings.CACHE_TTL
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, datetime] = {}
    
    def _generate_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        # 将参数转换为字符串并计算哈希
        key_data = {
            "args": args,
            "kwargs": sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _is_expired(self, key: str) -> bool:
        """检查缓存是否过期"""
        if key not in self._cache:
            return True
        
        cached_time = self._cache[key].get("timestamp")
        if not cached_time:
            return True
        
        cache_time = datetime.fromisoformat(cached_time)
        return datetime.now() - cache_time > timedelta(seconds=self.ttl)
    
    def _evict_if_needed(self):
        """如果缓存满了，移除最旧的条目"""
        if len(self._cache) >= self.max_size:
            # 找到最久未访问的键
            oldest_key = min(self._access_times, key=self._access_times.get)
            del self._cache[oldest_key]
            del self._access_times[oldest_key]
            logger.debug(f"缓存淘汰: 移除键 {oldest_key}")
    
    def get(self, key: str) -> Any:
        """获取缓存值"""
        if key not in self._cache or self._is_expired(key):
            return None
        
        # 更新访问时间
        self._access_times[key] = datetime.now()
        
        return self._cache[key]["value"]
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """设置缓存值"""
        try:
            if len(self._cache) >= self.max_size:
                self._evict_if_needed()
            
            self._cache[key] = {
                "value": value,
                "timestamp": datetime.now().isoformat()
            }
            self._access_times[key] = datetime.now()
            
            return True
            
        except Exception as e:
            logger.error(f"设置缓存失败: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存键"""
        try:
            if key in self._cache:
                del self._cache[key]
            if key in self._access_times:
                del self._access_times[key]
            return True
        except Exception as e:
            logger.error(f"删除缓存失败: {e}")
            return False
    
    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._access_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl": self.ttl,
            "hit_rate": getattr(self, '_hit_rate', 0.0)
        }


class FileCache:
    """文件缓存"""
    
    def __init__(self, cache_dir: str = None, ttl: int = None):
        self.cache_dir = Path(cache_dir or os.path.join(settings.VECTOR_DB_PATH, "cache"))
        self.ttl = ttl or settings.CACHE_TTL
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{key}.cache"
    
    def _is_expired(self, file_path: Path) -> bool:
        """检查文件缓存是否过期"""
        if not file_path.exists():
            return True
        
        file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
        return datetime.now() - file_time > timedelta(seconds=self.ttl)
    
    def get(self, key: str) -> Any:
        """获取缓存值"""
        try:
            file_path = self._get_file_path(key)
            
            if self._is_expired(file_path):
                self.delete(key)  # 删除过期文件
                return None
            
            with open(file_path, 'rb') as f:
                data = pickle.load(f)
            
            return data.get("value")
            
        except Exception as e:
            logger.warning(f"获取文件缓存失败: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """设置缓存值"""
        try:
            ttl = ttl or self.ttl
            file_path = self._get_file_path(key)
            
            cache_data = {
                "value": value,
                "timestamp": datetime.now().isoformat(),
                "ttl": ttl
            }
            
            with open(file_path, 'wb') as f:
                pickle.dump(cache_data, f)
            
            return True
            
        except Exception as e:
            logger.error(f"设置文件缓存失败: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存键"""
        try:
            file_path = self._get_file_path(key)
            if file_path.exists():
                file_path.unlink()
            return True
        except Exception as e:
            logger.warning(f"删除文件缓存失败: {e}")
            return False
    
    def clear(self):
        """清空所有缓存文件"""
        try:
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink()
        except Exception as e:
            logger.error(f"清空文件缓存失败: {e}")
    
    def cleanup_expired(self):
        """清理过期的缓存文件"""
        try:
            current_time = datetime.now()
            for cache_file in self.cache_dir.glob("*.cache"):
                file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                if current_time - file_time > timedelta(seconds=self.ttl):
                    cache_file.unlink()
                    logger.debug(f"清理过期缓存: {cache_file.name}")
        except Exception as e:
            logger.error(f"清理过期缓存失败: {e}")


class CacheManager:
    """缓存管理器 - 多级缓存"""
    
    def __init__(self, use_file_cache: bool = True):
        self.local_cache = LocalCache()
        self.file_cache = FileCache() if use_file_cache else None
    
    @handle_exceptions("cache_get")
    def get(self, key: str) -> Any:
        """获取缓存值（先从内存缓存，再从文件缓存）"""
        # 先从内存缓存获取
        value = self.local_cache.get(key)
        if value is not None:
            return value
        
        # 再从文件缓存获取
        if self.file_cache:
            value = self.file_cache.get(key)
            if value is not None:
                # 将文件缓存的值加载到内存缓存
                self.local_cache.set(key, value)
                return value
        
        return None
    
    @handle_exceptions("cache_set")
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """设置缓存值（同时存储到内存和文件缓存）"""
        # 存储到内存缓存
        self.local_cache.set(key, value, ttl)
        
        # 存储到文件缓存
        if self.file_cache:
            self.file_cache.set(key, value, ttl)
        
        return True
    
    @handle_exceptions("cache_delete")
    def delete(self, key: str) -> bool:
        """删除缓存键"""
        self.local_cache.delete(key)
        if self.file_cache:
            self.file_cache.delete(key)
        return True
    
    def clear(self):
        """清空所有缓存"""
        self.local_cache.clear()
        if self.file_cache:
            self.file_cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        stats = {
            "local_cache": self.local_cache.get_stats(),
            "file_cache": {
                "enabled": self.file_cache is not None,
                "cache_dir": str(self.file_cache.cache_dir) if self.file_cache else None
            }
        }
        
        if self.file_cache:
            try:
                file_count = len(list(self.file_cache.cache_dir.glob("*.cache")))
                stats["file_cache"]["file_count"] = file_count
            except:
                pass
        
        return stats
    
    def cleanup_expired(self):
        """清理过期缓存"""
        if self.file_cache:
            self.file_cache.cleanup_expired()


class ModelCache:
    """模型调用缓存"""
    
    def __init__(self):
        self.cache = CacheManager(use_file_cache=True)
    
    def get_model_cache_key(self, model_name: str, prompt: str, **kwargs) -> str:
        """生成模型调用缓存键"""
        cache_data = {
            "model": model_name,
            "prompt": prompt,
            "kwargs": sorted(kwargs.items())
        }
        cache_str = json.dumps(cache_data, sort_keys=True, default=str)
        return f"model_{hashlib.md5(cache_str.encode()).hexdigest()}"
    
    def get(self, model_name: str, prompt: str, **kwargs) -> Any:
        """获取模型调用结果"""
        key = self.get_model_cache_key(model_name, prompt, **kwargs)
        return self.cache.get(key)
    
    def set(self, model_name: str, prompt: str, result: Any, **kwargs) -> bool:
        """缓存模型调用结果"""
        key = self.get_model_cache_key(model_name, prompt, **kwargs)
        return self.cache.set(key, result)
    
    def invalidate_model(self, model_name: str):
        """使指定模型的所有缓存失效"""
        # 这里简化处理，实际可以维护模型特定的缓存键列表
        self.cache.clear()


class SearchCache:
    """搜索结果缓存"""
    
    def __init__(self):
        self.cache = CacheManager(use_file_cache=True)
    
    def get_search_cache_key(self, query: str, k: int = 4, filters: Dict = None) -> str:
        """生成搜索缓存键"""
        cache_data = {
            "query": query,
            "k": k,
            "filters": filters or {}
        }
        cache_str = json.dumps(cache_data, sort_keys=True, default=str)
        return f"search_{hashlib.md5(cache_str.encode()).hexdigest()}"
    
    def get(self, query: str, k: int = 4, filters: Dict = None) -> Any:
        """获取搜索结果"""
        key = self.get_search_cache_key(query, k, filters)
        return self.cache.get(key)
    
    def set(self, query: str, results: Any, k: int = 4, filters: Dict = None) -> bool:
        """缓存搜索结果"""
        key = self.get_search_cache_key(query, k, filters)
        return self.cache.set(key, results)


# 全局缓存实例
model_cache = ModelCache()
search_cache = SearchCache()
cache_manager = CacheManager()


if __name__ == "__main__":
    """测试缓存系统"""
    
    # 测试本地缓存
    local_cache = LocalCache(max_size=3, ttl=5)
    
    # 设置缓存
    local_cache.set("test1", "value1")
    local_cache.set("test2", "value2")
    local_cache.set("test3", "value3")
    
    # 获取缓存
    print(f"test1: {local_cache.get('test1')}")
    print(f"test2: {local_cache.get('test2')}")
    
    # 测试缓存管理
    cache_mgr = CacheManager()
    
    # 设置缓存
    cache_mgr.set("model_result", {"response": "Hello World", "confidence": 0.9})
    
    # 获取缓存
    result = cache_mgr.get("model_result")
    print(f"缓存结果: {result}")
    
    # 获取统计信息
    stats = cache_mgr.get_stats()
    print(f"缓存统计: {stats}")
    
    print("✅ 缓存系统测试完成")