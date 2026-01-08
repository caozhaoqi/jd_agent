"""
智能查询缓存系统
用于提高RAG系统查询效率，减少重复计算
"""

import hashlib
import json
import time
from typing import Any, Dict, Optional, List
from loguru import logger
from core.redis_client import RedisClient
from core.monitoring import cache_hits, cache_misses, cache_queries_total

# 延迟导入机器学习缓存预测器
# 避免循环导入问题


class QueryCache:
    """智能查询缓存类"""

    def __init__(self):
        self.redis_client = RedisClient()
        self.default_ttl = 3600  # 默认TTL 1小时
        self.query_history = {}  # 本地查询历史记录
        self.similarity_threshold = 0.8  # 相似度阈值
        self.cache_prefix = "query_cache:"

    def _generate_cache_key(self, query: str, params: Dict[str, Any] = None) -> str:
        """生成缓存键"""
        # 将查询和参数组合
        cache_data = {
            "query": query.strip().lower(),
            "params": params or {}
        }
        
        # 生成哈希值作为键
        cache_key = hashlib.md5(
            json.dumps(cache_data, sort_keys=True).encode()
        ).hexdigest()
        
        return f"{self.cache_prefix}{cache_key}"

    def get(self, query: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """获取缓存的查询结果"""
        try:
            # 记录查询总数
            cache_queries_total.inc()
            
            cache_key = self._generate_cache_key(query, params)
            
            # 先尝试从Redis获取
            cached_result = self.redis_client.get(cache_key)
            if cached_result:
                cache_hits.inc()
                logger.debug(f"缓存命中: {query[:50]}...")
                # 记录缓存命中事件到ML预测器
                from core.ml_cache_predictor import ml_cache_predictor
                ml_cache_predictor.record_cache_event(query, params, True, cache_key)
                return cached_result
            
            # Redis未命中，检查相似查询
            cache_misses.inc()
            similar_result = self._find_similar_query(query, params)
            if similar_result:
                logger.info(f"相似查询命中: {query[:50]}...")
                # 记录相似查询命中事件到ML预测器
                from core.ml_cache_predictor import ml_cache_predictor
                ml_cache_predictor.record_cache_event(query, params, True, cache_key)
                return similar_result
            
            logger.debug(f"缓存未命中: {query[:50]}...")
            # 记录缓存未命中事件到ML预测器
            from core.ml_cache_predictor import ml_cache_predictor
            ml_cache_predictor.record_cache_event(query, params, False, cache_key)
            return None
            
        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
            return None

    def set(self, query: str, result: Dict[str, Any], params: Dict[str, Any] = None, 
            ttl: int = None) -> bool:
        """设置查询结果缓存"""
        try:
            cache_key = self._generate_cache_key(query, params)
            
            # 使用ML预测器优化TTL
            base_ttl = ttl or self.default_ttl
            from core.ml_cache_predictor import ml_cache_predictor
            optimized_ttl = ml_cache_predictor.optimize_ttl(query, params, base_ttl)
            
            # 将查询结果添加到Redis缓存
            success = self.redis_client.set(cache_key, result, expire_seconds=optimized_ttl)
            
            if success:
                # 更新本地查询历史
                self._update_query_history(query, params, result)
                logger.debug(f"缓存设置成功: {query[:50]}..., TTL: {optimized_ttl}秒 (优化前: {base_ttl}秒)")
            
            return success
            
        except Exception as e:
            logger.error(f"设置缓存失败: {e}")
            return False

    def _find_similar_query(self, query: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """查找相似的查询结果"""
        try:
            query_normalized = query.strip().lower()
            
            # 检查本地查询历史
            for cached_query, cached_data in self.query_history.items():
                similarity = self._calculate_similarity(query_normalized, cached_query)
                
                if similarity >= self.similarity_threshold:
                    # 找到了相似查询，检查参数是否也匹配
                    if self._params_match(params, cached_data.get("params")):
                        cache_hits.inc()
                        return cached_data["result"]
            
            return None
            
        except Exception as e:
            logger.error(f"查找相似查询失败: {e}")
            return None

    def _calculate_similarity(self, query1: str, query2: str) -> float:
        """计算两个查询的相似度"""
        try:
            # 简单的相似度计算：基于Jaccard相似系数
            words1 = set(query1.split())
            words2 = set(query2.split())
            
            if not words1 or not words2:
                return 0.0
            
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            
            return intersection / union if union > 0 else 0.0
            
        except Exception as e:
            logger.error(f"计算相似度失败: {e}")
            return 0.0

    def _params_match(self, params1: Dict[str, Any], params2: Dict[str, Any]) -> bool:
        """检查两个参数字典是否匹配"""
        if not params1 and not params2:
            return True
        
        if not params1 or not params2:
            return False
        
        # 比较关键参数
        key_params = ["model", "max_results", "similarity_threshold"]
        
        for key in key_params:
            if key in params1 or key in params2:
                if params1.get(key) != params2.get(key):
                    return False
        
        return True

    def _update_query_history(self, query: str, params: Dict[str, Any], result: Dict[str, Any]):
        """更新本地查询历史"""
        try:
            query_normalized = query.strip().lower()
            
            # 如果历史记录超过限制，删除最旧的记录
            max_history = 1000
            if len(self.query_history) >= max_history:
                # 删除最旧的记录
                oldest_key = min(self.query_history.keys())
                del self.query_history[oldest_key]
            
            # 更新或添加当前查询
            self.query_history[query_normalized] = {
                "query": query,
                "params": params,
                "result": result,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"更新查询历史失败: {e}")

    def invalidate_cache(self, pattern: str = None) -> bool:
        """使缓存失效"""
        try:
            if not pattern:
                # 清空所有缓存
                keys = self.redis_client.keys(f"{self.cache_prefix}*")
                if keys:
                    self.redis_client.delete(*keys)
                self.query_history.clear()
                logger.info("已清空所有查询缓存")
                return True
            
            # 按模式删除缓存
            pattern = f"{self.cache_prefix}{pattern}"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"已删除匹配模式 {pattern} 的缓存")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"使缓存失效失败: {e}")
            return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            # 获取Redis缓存信息
            redis_info = self.redis_client.info()
            memory_usage = redis_info.get("used_memory_human", "unknown")
            
            # 计算本地历史记录大小
            history_size = len(self.query_history)
            
            return {
                "memory_usage": memory_usage,
                "history_size": history_size,
                "cache_prefix": self.cache_prefix,
                "similarity_threshold": self.similarity_threshold,
                "default_ttl": self.default_ttl
            }
            
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {"error": str(e)}


# 创建全局查询缓存实例
query_cache = QueryCache()