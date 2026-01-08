"""
机器学习缓存预测器
用于预测查询的缓存命中率并优化缓存策略
"""

import json
import numpy as np
import pandas as pd
import time
from typing import Any, Dict, List, Optional, Tuple
from loguru import logger
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
import joblib

from core.redis_client import RedisClient
from core.query_cache import QueryCache


class MLCachePredictor:
    """机器学习缓存预测器类"""

    def __init__(self, query_cache: QueryCache):
        self.query_cache = query_cache
        self.redis_client = RedisClient()
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.is_trained = False
        self.model_path = "./ml_cache_predictor.joblib"
        self.vectorizer_path = "./ml_vectorizer.joblib"
        self.cache_prefix = "ml_cache_"
        self.training_data = []
        self.min_training_samples = 100  # 最小训练样本数
        
        # 尝试加载已训练的模型
        self._load_model()

    def _extract_query_features(self, query: str) -> np.ndarray:
        """提取查询的特征向量"""
        try:
            return self.vectorizer.transform([query]).toarray()[0]
        except Exception as e:
            logger.error(f"提取查询特征失败: {e}")
            return np.zeros(self.vectorizer.max_features)

    def _extract_cache_features(self, query: str, params: Dict[str, Any] = None) -> Dict[str, float]:
        """提取缓存相关特征"""
        # 计算与历史查询的相似度特征
        similar_query = self.query_cache._find_similar_query(query, params)
        similarity_score = 0.0
        
        if similar_query:
            # 找到最相似的历史查询
            for cached_query in self.query_cache.query_history:
                sim = self.query_cache._calculate_similarity(query, cached_query)
                if sim > similarity_score:
                    similarity_score = sim
        
        # 提取查询长度特征
        query_length = len(query.split())
        
        # 提取参数复杂度特征
        param_complexity = len(params) if params else 0
        
        return {
            "similarity_score": similarity_score,
            "query_length": query_length,
            "param_complexity": param_complexity,
            "current_time": time.time() % 86400  # 一天中的秒数
        }

    def record_cache_event(self, query: str, params: Dict[str, Any], is_hit: bool, cache_key: str = None):
        """记录缓存命中/未命中事件"""
        try:
            # 提取特征
            query_features = self._extract_query_features(query)
            cache_features = self._extract_cache_features(query, params)
            
            # 组合所有特征
            combined_features = {
                **cache_features,
                "is_hit": 1 if is_hit else 0,
                "query_features": query_features.tolist(),
                "timestamp": time.time()
            }
            
            # 保存到训练数据
            self.training_data.append(combined_features)
            
            # 保存到Redis以持久化
            event_key = f"{self.cache_prefix}event:{int(time.time())}_{hash(query) % 1000000}"
            self.redis_client.set(event_key, combined_features, expire_seconds=86400 * 7)  # 保存7天
            
            logger.debug(f"记录缓存事件: 查询='{query[:30]}...', 命中={is_hit}")
            
            # 如果样本数足够，自动训练模型
            if len(self.training_data) >= self.min_training_samples and not self.is_trained:
                logger.info(f"训练数据达到 {self.min_training_samples} 条，开始训练模型")
                self.train_model()
                
        except Exception as e:
            logger.error(f"记录缓存事件失败: {e}")

    def train_model(self):
        """训练缓存预测模型"""
        try:
            logger.info("开始训练缓存预测模型...")
            
            if len(self.training_data) < self.min_training_samples:
                logger.warning(f"训练数据不足 ({len(self.training_data)} < {self.min_training_samples})，跳过训练")
                return False
            
            # 准备训练数据
            X = []
            y = []
            
            for event in self.training_data:
                # 组合所有特征
                features = [
                    event["similarity_score"],
                    event["query_length"],
                    event["param_complexity"],
                    event["current_time"]
                ] + event["query_features"]
                
                X.append(features)
                y.append(event["is_hit"])
            
            # 转换为numpy数组
            X = np.array(X)
            y = np.array(y)
            
            # 划分训练集和测试集
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # 训练模型
            self.model.fit(X_train, y_train)
            
            # 评估模型
            y_pred = self.model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred)
            recall = recall_score(y_test, y_pred)
            
            logger.info(f"模型训练完成 - 准确率: {accuracy:.4f}, 精确率: {precision:.4f}, 召回率: {recall:.4f}")
            
            # 保存模型
            self._save_model()
            
            self.is_trained = True
            return True
            
        except Exception as e:
            logger.error(f"训练模型失败: {e}")
            return False

    def predict_cache_hit(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """预测查询的缓存命中率"""
        try:
            if not self.is_trained:
                # 如果模型未训练，返回基于规则的预测
                similar_query = self.query_cache._find_similar_query(query, params)
                return {
                    "hit_probability": 0.8 if similar_query else 0.2,
                    "confidence": 0.5,
                    "model_used": "rule_based"
                }
            
            # 提取特征
            query_features = self._extract_query_features(query)
            cache_features = self._extract_cache_features(query, params)
            
            # 组合所有特征
            combined_features = [
                cache_features["similarity_score"],
                cache_features["query_length"],
                cache_features["param_complexity"],
                cache_features["current_time"]
            ] + query_features.tolist()
            
            # 预测
            combined_features = np.array([combined_features])
            prediction = self.model.predict(combined_features)[0]
            probabilities = self.model.predict_proba(combined_features)[0]
            
            hit_probability = probabilities[1]  # 第二个元素是命中的概率
            confidence = max(probabilities)  # 最大概率作为置信度
            
            logger.debug(f"预测缓存命中: 查询='{query[:30]}...', 概率={hit_probability:.4f}, 置信度={confidence:.4f}")
            
            return {
                "hit_probability": hit_probability,
                "confidence": confidence,
                "model_used": "machine_learning"
            }
            
        except Exception as e:
            logger.error(f"预测缓存命中失败: {e}")
            # 回退到基于规则的预测
            similar_query = self.query_cache._find_similar_query(query, params)
            return {
                "hit_probability": 0.8 if similar_query else 0.2,
                "confidence": 0.5,
                "model_used": "fallback_rule_based"
            }

    def optimize_ttl(self, query: str, params: Dict[str, Any] = None, base_ttl: int = 3600) -> int:
        """根据预测结果优化TTL"""
        try:
            prediction = self.predict_cache_hit(query, params)
            
            # 根据命中概率调整TTL
            hit_probability = prediction["hit_probability"]
            
            if hit_probability > 0.8:
                # 高命中率，延长TTL
                return base_ttl * 2
            elif hit_probability < 0.3:
                # 低命中率，缩短TTL
                return max(base_ttl // 2, 300)  # 最短5分钟
            else:
                # 中等命中率，保持默认TTL
                return base_ttl
                
        except Exception as e:
            logger.error(f"优化TTL失败: {e}")
            return base_ttl

    def _save_model(self):
        """保存模型到文件"""
        try:
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.vectorizer, self.vectorizer_path)
            logger.info(f"模型已保存到 {self.model_path} 和 {self.vectorizer_path}")
        except Exception as e:
            logger.error(f"保存模型失败: {e}")

    def _load_model(self):
        """从文件加载模型"""
        try:
            self.model = joblib.load(self.model_path)
            self.vectorizer = joblib.load(self.vectorizer_path)
            self.is_trained = True
            logger.info(f"已加载训练好的模型")
        except FileNotFoundError:
            logger.info("未找到已训练的模型，将使用新模型")
        except Exception as e:
            logger.error(f"加载模型失败: {e}")

    def get_model_stats(self) -> Dict[str, Any]:
        """获取模型统计信息"""
        return {
            "is_trained": self.is_trained,
            "training_samples": len(self.training_data),
            "vectorizer_features": self.vectorizer.max_features if hasattr(self.vectorizer, 'max_features') else 0,
            "model_type": type(self.model).__name__
        }

    def load_training_data(self):
        """从Redis加载历史训练数据"""
        try:
            # 从Redis获取所有事件数据
            event_keys = self.redis_client.keys(f"{self.cache_prefix}event:*")
            
            if event_keys:
                events = self.redis_client.mget(event_keys)
                self.training_data.extend([event for event in events if event])
                logger.info(f"已加载 {len(events)} 条历史训练数据")
            
        except Exception as e:
            logger.error(f"加载训练数据失败: {e}")


# 创建全局ML缓存预测器实例
from core.query_cache import query_cache
ml_cache_predictor = MLCachePredictor(query_cache)
