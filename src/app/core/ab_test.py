import hashlib
import json
import time
from typing import Dict, Any, Optional, List
from loguru import logger
from core.redis_client import RedisClient
from core.monitoring import api_requests_total

class ABTestManager:
    """
    A/B测试框架管理类
    支持多种缓存策略和错误提示文案的A/B测试
    """

    def __init__(self):
        self.redis_client = RedisClient()
        self.test_prefix = "ab_test:"
        self.variants_prefix = "ab_variants:"
        self.results_prefix = "ab_results:"
        
        # 默认测试配置
        self.default_tests = {
            "cache_strategy": {
                "enabled": True,
                "variants": {
                    "control": {"weight": 40, "strategy": "default"},
                    "ttl_optimized": {"weight": 30, "strategy": "ttl_optimized"},
                    "similarity_boosted": {"weight": 30, "strategy": "similarity_boosted"}
                },
                "description": "不同缓存策略效果对比测试"
            },
            "error_message": {
                "enabled": True,
                "variants": {
                    "original": {"weight": 50, "message": "请求失败，请稍后重试"},
                    "friendly": {"weight": 50, "message": "暂时无法完成请求，建议您稍后再试哦"}
                },
                "description": "不同错误提示文案效果测试"
            }
        }
        
        # 初始化测试配置
        self._init_tests()

    def _init_tests(self):
        """初始化测试配置"""
        try:
            for test_name, config in self.default_tests.items():
                if not self.redis_client.exists(f"{self.test_prefix}{test_name}"):
                    self.create_test(test_name, config)
        except Exception as e:
            logger.error(f"初始化A/B测试配置失败: {e}")

    def create_test(self, test_name: str, config: Dict[str, Any]) -> bool:
        """
        创建新的A/B测试
        
        Args:
            test_name: 测试名称
            config: 测试配置，包含enabled、variants、description
        """
        try:
            # 验证配置
            if "enabled" not in config or "variants" not in config:
                logger.error("测试配置缺少必要字段")
                return False
            
            # 验证权重和为100
            total_weight = sum(variant["weight"] for variant in config["variants"].values())
            if total_weight != 100:
                logger.warning(f"测试{test_name}的权重和不为100%，实际为{total_weight}%")
            
            # 存储测试配置
            test_key = f"{self.test_prefix}{test_name}"
            self.redis_client.set(test_key, config, expire_seconds=31536000)  # 1年过期
            
            logger.info(f"创建A/B测试成功: {test_name}")
            return True
        except Exception as e:
            logger.error(f"创建A/B测试失败: {e}")
            return False

    def get_variant(self, test_name: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        根据用户ID获取测试变体
        使用一致性哈希算法分配流量
        
        Args:
            test_name: 测试名称
            user_id: 用户唯一标识符
        """
        try:
            # 获取测试配置
            test_key = f"{self.test_prefix}{test_name}"
            test_config = self.redis_client.get(test_key)
            
            if not test_config or not test_config.get("enabled", False):
                return None
            
            variants = test_config.get("variants", {})
            if not variants:
                return None
            
            # 生成用户的哈希值
            hash_key = f"{test_name}:{user_id}"
            hash_value = hashlib.md5(hash_key.encode()).hexdigest()
            numeric_hash = int(hash_value, 16) % 100
            
            # 根据权重分配变体
            cumulative_weight = 0
            for variant_name, variant in variants.items():
                cumulative_weight += variant.get("weight", 0)
                if numeric_hash < cumulative_weight:
                    # 记录用户变体
                    user_variant_key = f"{self.variants_prefix}{test_name}:{user_id}"
                    self.redis_client.set(user_variant_key, variant_name, expire_seconds=31536000)
                    
                    return {
                        "variant_name": variant_name,
                        "config": variant
                    }
            
            # 默认返回第一个变体
            first_variant = next(iter(variants.items()), None)
            if first_variant:
                return {
                    "variant_name": first_variant[0],
                    "config": first_variant[1]
                }
            
            return None
        except Exception as e:
            logger.error(f"获取测试变体失败: {e}")
            return None

    def record_result(self, test_name: str, user_id: str, variant_name: str, 
                     result: str, metrics: Dict[str, Any] = None) -> bool:
        """
        记录测试结果
        
        Args:
            test_name: 测试名称
            user_id: 用户ID
            variant_name: 变体名称
            result: 结果类型（如：success, failure, error_encountered）
            metrics: 相关指标（如：响应时间、用户操作）
        """
        try:
            # 生成结果记录
            result_record = {
                "timestamp": time.time(),
                "user_id": user_id,
                "variant_name": variant_name,
                "result": result,
                "metrics": metrics or {},
                "test_name": test_name
            }
            
            # 使用有序集合存储结果，方便按时间查询
            results_key = f"{self.results_prefix}{test_name}"
            self.redis_client.redis_client.zadd(
                results_key,
                {json.dumps(result_record): result_record["timestamp"]}
            )
            
            # 同时记录到常规结果集合
            variant_results_key = f"{self.results_prefix}{test_name}:{variant_name}"
            self.redis_client.redis_client.lpush(
                variant_results_key,
                json.dumps(result_record)
            )
            
            # 设置过期时间（30天）
            self.redis_client.redis_client.expire(results_key, 2592000)
            self.redis_client.redis_client.expire(variant_results_key, 2592000)
            
            # 更新变体结果计数
            count_key = f"{self.results_prefix}{test_name}:{variant_name}:{result}:count"
            self.redis_client.redis_client.incr(count_key)
            self.redis_client.redis_client.expire(count_key, 2592000)
            
            logger.debug(f"记录A/B测试结果成功: {test_name} - {variant_name} - {result}")
            return True
        except Exception as e:
            logger.error(f"记录A/B测试结果失败: {e}")
            return False

    def get_test_results(self, test_name: str, variant_name: Optional[str] = None, 
                        time_range: int = 86400) -> Dict[str, Any]:
        """
        获取测试结果统计
        
        Args:
            test_name: 测试名称
            variant_name: 特定变体名称（可选）
            time_range: 时间范围（秒，默认24小时）
        """
        try:
            results = {}
            cutoff_time = time.time() - time_range
            
            if variant_name:
                # 获取特定变体的结果
                variant_results_key = f"{self.results_prefix}{test_name}:{variant_name}"
                variant_results = self.redis_client.redis_client.lrange(variant_results_key, 0, -1)
                
                results[variant_name] = self._analyze_results(variant_results, cutoff_time)
            else:
                # 获取测试配置
                test_key = f"{self.test_prefix}{test_name}"
                test_config = self.redis_client.get(test_key)
                
                if not test_config:
                    return {"error": "测试不存在"}
                
                variants = test_config.get("variants", {})
                
                # 分析所有变体的结果
                for variant in variants.keys():
                    variant_results_key = f"{self.results_prefix}{test_name}:{variant}"
                    variant_results = self.redis_client.redis_client.lrange(variant_results_key, 0, -1)
                    
                    results[variant] = self._analyze_results(variant_results, cutoff_time)
            
            return results
        except Exception as e:
            logger.error(f"获取测试结果失败: {e}")
            return {"error": str(e)}

    def _analyze_results(self, raw_results: List[bytes], cutoff_time: float) -> Dict[str, Any]:
        """
        分析测试结果
        
        Args:
            raw_results: 原始结果列表
            cutoff_time: 时间截止点
        """
        try:
            total = 0
            results_count = {}
            metrics_sum = {}
            metrics_count = {}
            
            for raw_result in raw_results:
                result = json.loads(raw_result)
                
                # 过滤时间范围
                if result["timestamp"] < cutoff_time:
                    continue
                
                total += 1
                result_type = result["result"]
                
                # 统计结果类型
                if result_type not in results_count:
                    results_count[result_type] = 0
                results_count[result_type] += 1
                
                # 统计指标
                metrics = result.get("metrics", {})
                for key, value in metrics.items():
                    if isinstance(value, (int, float)):
                        if key not in metrics_sum:
                            metrics_sum[key] = 0
                            metrics_count[key] = 0
                        metrics_sum[key] += value
                        metrics_count[key] += 1
            
            # 计算平均值
            metrics_avg = {}
            for key in metrics_sum:
                if metrics_count[key] > 0:
                    metrics_avg[key] = metrics_sum[key] / metrics_count[key]
            
            return {
                "total": total,
                "results_count": results_count,
                "metrics_avg": metrics_avg
            }
        except Exception as e:
            logger.error(f"分析测试结果失败: {e}")
            return {"total": 0, "results_count": {}, "metrics_avg": {}}

    def get_cache_strategy(self, user_id: str) -> str:
        """
        获取用户的缓存策略
        
        Args:
            user_id: 用户ID
        """
        variant = self.get_variant("cache_strategy", user_id)
        if variant:
            return variant["config"].get("strategy", "default")
        return "default"

    def get_error_message(self, user_id: str) -> str:
        """
        获取用户的错误提示消息
        
        Args:
            user_id: 用户ID
        """
        variant = self.get_variant("error_message", user_id)
        if variant:
            return variant["config"].get("message", "请求失败，请稍后重试")
        return "请求失败，请稍后重试"

    def list_tests(self) -> Dict[str, Any]:
        """列出所有A/B测试"""
        try:
            tests = {}
            keys = self.redis_client.redis_client.keys(f"{self.test_prefix}*")
            
            for key in keys:
                test_name = key.decode().replace(self.test_prefix, "")
                test_config = self.redis_client.get(key.decode())
                if test_config:
                    tests[test_name] = test_config
            
            return tests
        except Exception as e:
            logger.error(f"列出A/B测试失败: {e}")
            return {}

    def update_test(self, test_name: str, updates: Dict[str, Any]) -> bool:
        """
        更新测试配置
        
        Args:
            test_name: 测试名称
            updates: 更新的配置
        """
        try:
            test_key = f"{self.test_prefix}{test_name}"
            current_config = self.redis_client.get(test_key)
            
            if not current_config:
                logger.error(f"测试{test_name}不存在")
                return False
            
            # 更新配置
            current_config.update(updates)
            self.redis_client.set(test_key, current_config, expire_seconds=31536000)
            
            logger.info(f"更新A/B测试成功: {test_name}")
            return True
        except Exception as e:
            logger.error(f"更新A/B测试失败: {e}")
            return False

    def delete_test(self, test_name: str) -> bool:
        """
        删除测试
        
        Args:
            test_name: 测试名称
        """
        try:
            # 删除测试配置
            test_key = f"{self.test_prefix}{test_name}"
            self.redis_client.delete(test_key)
            
            # 删除相关的变体和结果
            variant_keys = self.redis_client.redis_client.keys(f"{self.variants_prefix}{test_name}:*")
            result_keys = self.redis_client.redis_client.keys(f"{self.results_prefix}{test_name}*")
            
            if variant_keys:
                self.redis_client.redis_client.delete(*variant_keys)
            
            if result_keys:
                self.redis_client.redis_client.delete(*result_keys)
            
            logger.info(f"删除A/B测试成功: {test_name}")
            return True
        except Exception as e:
            logger.error(f"删除A/B测试失败: {e}")
            return False


# 创建全局A/B测试管理器实例
ab_test_manager = ABTestManager()
