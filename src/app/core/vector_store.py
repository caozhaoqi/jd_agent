"""
统一向量数据库访问层
解决当前项目中同时使用Chroma和FAISS的混乱问题
"""

import os
import json
import shutil
from typing import List, Dict, Any, Optional, Union, Tuple
from pathlib import Path
from datetime import datetime
from langchain.docstore.document import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from loguru import logger

from core.config import settings
from core.exceptions import (
    VectorStoreError, 
    VectorStoreConnectionError, 
    VectorStoreQueryError,
    DataProcessingError,
    handle_exceptions
)


class UnifiedVectorStore:
    """统一向量数据库访问层"""
    
    def __init__(self, collection_name: str = None, embeddings_model: str = None):
        """
        初始化统一向量数据库
        
        Args:
            collection_name: 集合名称，默认为配置中的值
            embeddings_model: 嵌入模型名称，默认为配置中的值
        """
        self.collection_name = collection_name or settings.VECTOR_DB_COLLECTION
        self.embeddings_model = embeddings_model or settings.EMBEDDING_MODEL_NAME
        self.persist_directory = settings.VECTOR_DB_PATH
        
        # 嵌入模型
        self.embeddings = None
        
        # Chroma客户端
        self.client = None
        
        # 统计信息
        self.stats = {
            "total_documents": 0,
            "last_updated": None,
            "collections": {}
        }
        
        # 初始化
        self._initialize()
    
    def _initialize(self):
        """初始化向量数据库"""
        try:
            # 创建必要的目录
            Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
            
            # 初始化嵌入模型 - 添加错误处理
            try:
                self.embeddings = HuggingFaceEmbeddings(
                    model_name=self.embeddings_model,
                    model_kwargs={"device": "cpu"},
                    encode_kwargs={"normalize_embeddings": True},
                )
                logger.success(f"✅ 嵌入模型加载成功: {self.embeddings_model}")
            except Exception as e:
                logger.warning(f"⚠️ 嵌入模型加载失败: {e}")
                logger.info("🔄 使用简单的TF-IDF嵌入模型作为后备方案")
                self.embeddings = None
            
            # 初始化Chroma客户端
            if self.embeddings:
                self.client = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embeddings,
                    collection_name=self.collection_name
                )
                logger.success(f"✅ 统一向量数据库初始化成功")
            else:
                logger.info("🔄 向量数据库将延迟初始化")
                self.client = None
            
            logger.info(f"集合名称: {self.collection_name}")
            logger.info(f"存储路径: {self.persist_directory}")
            logger.info(f"嵌入模型: {self.embeddings_model}")
            
        except Exception as e:
            logger.error(f"❌ 向量数据库初始化失败: {e}")
            self.client = None
            self.embeddings = None
    
    def _normalize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """标准化元数据格式"""
        normalized = {}
        
        # 标准化字段名称
        field_mapping = {
            "source": ["source", "url", "filepath", "file_path"],
            "title": ["title", "name", "heading"],
            "content": ["content", "text", "body", "description"],
            "author": ["author", "creator", "user"],
            "timestamp": ["timestamp", "time", "date", "publish_time"],
            "platform": ["platform", "site", "domain"],
            "tags": ["tags", "categories", "labels", "keywords"],
            "likes": ["likes", "upvotes", "hearts"],
            "replies": ["replies", "comments", "responses"]
        }
        
        # 映射字段值
        for standard_field, possible_fields in field_mapping.items():
            for field in possible_fields:
                if field in metadata and field not in normalized:
                    value = metadata[field]
                    
                    # 特殊处理
                    if standard_field == "tags" and isinstance(value, str):
                        # 逗号分隔的字符串转换为列表
                        value = [tag.strip() for tag in value.split(",") if tag.strip()]
                    
                    normalized[standard_field] = value
                    break
        
        # 添加文档类型标识
        normalized["doc_type"] = metadata.get("doc_type", "unknown")
        
        # 添加索引时间
        normalized["indexed_at"] = datetime.now().isoformat()
        
        return normalized
    
    @handle_exceptions("add_documents")
    def add_documents(
        self, 
        documents: List[Document], 
        doc_type: str = "unknown",
        batch_size: int = None
    ) -> List[str]:
        """
        添加文档到向量数据库
        
        Args:
            documents: 文档列表
            doc_type: 文档类型（blog, interview, etc.）
            batch_size: 批处理大小
            
        Returns:
            添加的文档ID列表
        """
        if not documents:
            logger.warning("没有文档需要添加")
            return []
        
        if not self.client:
            logger.warning("向量数据库客户端未初始化，跳过文档添加")
            return []
        
        batch_size = batch_size or settings.MAX_DOCUMENTS_PER_BATCH
        
        # 标准化文档元数据
        processed_docs = []
        for doc in documents:
            # 复制文档以避免修改原始文档
            new_doc = Document(
                page_content=doc.page_content,
                metadata=self._normalize_metadata({
                    **doc.metadata,
                    "doc_type": doc_type
                })
            )
            processed_docs.append(new_doc)
        
        # 批量添加文档
        all_ids = []
        for i in range(0, len(processed_docs), batch_size):
            batch = processed_docs[i:i + batch_size]
            
            try:
                ids = self.client.add_documents(batch)
                all_ids.extend(ids)
                
                logger.info(f"✅ 成功添加 {len(batch)} 个文档 (批次 {i//batch_size + 1})")
                
            except Exception as e:
                logger.error(f"❌ 批量添加文档失败 (批次 {i//batch_size + 1}): {e}")
                raise VectorStoreError(
                    message=f"添加文档失败: {str(e)}",
                    details={"batch_index": i//batch_size, "batch_size": len(batch)}
                )
        
        # 更新统计信息
        self.stats["total_documents"] += len(all_ids)
        self.stats["last_updated"] = datetime.now().isoformat()
        
        logger.success(f"✅ 总计添加 {len(all_ids)} 个文档到向量数据库")
        return all_ids
    
    @handle_exceptions("similarity_search")
    def similarity_search(
        self, 
        query: str, 
        k: int = 4,
        filter_dict: Dict[str, Any] = None,
        score_threshold: float = None
    ) -> List[Document]:
        """
        执行相似性搜索
        
        Args:
            query: 查询字符串
            k: 返回文档数量
            filter_dict: 过滤条件
            score_threshold: 相似性分数阈值
            
        Returns:
            相似文档列表
        """
        search_params = {"k": k}
        
        # 添加过滤条件
        if filter_dict:
            # 标准化过滤条件
            normalized_filter = {}
            for key, value in filter_dict.items():
                if key == "doc_type" and isinstance(value, str):
                    normalized_filter[key] = value
                elif key in ["platform", "author"]:
                    normalized_filter[key] = value
            search_params["filter"] = normalized_filter
        
        # 添加分数阈值
        if score_threshold:
            search_params["score_threshold"] = score_threshold
        
        try:
            logger.debug(f"🔍 执行搜索: '{query}', 参数: {search_params}")
            
            docs = self.client.similarity_search(query, **search_params)
            
            logger.info(f"🔍 搜索完成，返回 {len(docs)} 个结果")
            
            return docs
            
        except Exception as e:
            logger.error(f"❌ 搜索失败: {e}")
            raise VectorStoreQueryError(
                message=f"向量搜索失败: {str(e)}",
                details={
                    "query": query,
                    "search_params": search_params
                }
            )
    
    def search_with_scores(
        self, 
        query: str, 
        k: int = 4,
        filter_dict: Dict[str, Any] = None,
        score_threshold: float = None
    ) -> List[Tuple[Document, float]]:
        """
        执行相似性搜索并返回分数
        
        Args:
            query: 查询字符串
            k: 返回文档数量
            filter_dict: 过滤条件
            score_threshold: 相似性分数阈值
            
        Returns:
            (文档, 分数) 元组列表
        """
        search_params = {"k": k}
        
        if filter_dict:
            normalized_filter = {}
            for key, value in filter_dict.items():
                if key in ["doc_type", "platform", "author"]:
                    normalized_filter[key] = value
            search_params["filter"] = normalized_filter
        
        if score_threshold:
            search_params["score_threshold"] = score_threshold
        
        try:
            logger.debug(f"🔍 执行带分数搜索: '{query}', 参数: {search_params}")
            
            results = self.client.similarity_search_with_score(query, **search_params)
            
            logger.info(f"🔍 带分数搜索完成，返回 {len(results)} 个结果")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 带分数搜索失败: {e}")
            raise VectorStoreQueryError(
                message=f"向量搜索失败: {str(e)}",
                details={
                    "query": query,
                    "search_params": search_params
                }
            )
    
    def search_by_type(
        self, 
        query: str, 
        doc_type: str,
        k: int = 4,
        score_threshold: float = None
    ) -> List[Document]:
        """按文档类型搜索"""
        filter_dict = {"doc_type": doc_type}
        return self.similarity_search(
            query=query, 
            k=k, 
            filter_dict=filter_dict,
            score_threshold=score_threshold
        )
    
    def search_multi_type(
        self, 
        query: str, 
        doc_types: List[str],
        k_per_type: int = 2,
        score_threshold: float = None
    ) -> Dict[str, List[Document]]:
        """按多个文档类型搜索"""
        results = {}
        
        for doc_type in doc_types:
            try:
                docs = self.search_by_type(
                    query=query,
                    doc_type=doc_type,
                    k=k_per_type,
                    score_threshold=score_threshold
                )
                results[doc_type] = docs
            except Exception as e:
                logger.warning(f"搜索文档类型 '{doc_type}' 失败: {e}")
                results[doc_type] = []
        
        return results
    
    @handle_exceptions("get_stats")
    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            # 获取集合统计信息
            collection = self.client._collection
            count = collection.count()
            
            self.stats.update({
                "total_documents": count,
                "last_updated": datetime.now().isoformat(),
                "collection_name": self.collection_name,
                "persist_directory": self.persist_directory,
                "embeddings_model": self.embeddings_model
            })
            
            return self.stats
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise VectorStoreError(f"获取统计信息失败: {str(e)}")
    
    def delete_documents(self, ids: List[str]) -> bool:
        """删除指定文档"""
        try:
            self.client.delete(ids=ids)
            logger.success(f"✅ 成功删除 {len(ids)} 个文档")
            return True
        except Exception as e:
            logger.error(f"❌ 删除文档失败: {e}")
            return False
    
    def clear_collection(self) -> bool:
        """清空集合"""
        try:
            self.client.delete_collection()
            self._initialize()
            logger.success("✅ 集合已清空并重新初始化")
            return True
        except Exception as e:
            logger.error(f"❌ 清空集合失败: {e}")
            return False
    
    def backup(self, backup_path: str) -> bool:
        """备份向量数据库"""
        try:
            backup_dir = Path(backup_path)
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # 复制整个数据库目录
            shutil.copytree(
                self.persist_directory,
                backup_dir / "vector_db",
                dirs_exist_ok=True
            )
            
            # 复制统计信息
            stats_file = backup_dir / "stats.json"
            with open(stats_file, "w", encoding="utf-8") as f:
                json.dump(self.get_stats(), f, ensure_ascii=False, indent=2)
            
            logger.success(f"✅ 向量数据库备份成功: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 向量数据库备份失败: {e}")
            return False
    
    def restore(self, backup_path: str) -> bool:
        """从备份恢复向量数据库"""
        try:
            backup_dir = Path(backup_path)
            source_db = backup_dir / "vector_db"
            
            if not source_db.exists():
                raise DataProcessingError(f"备份目录不存在: {source_db}")
            
            # 备份当前数据库
            if Path(self.persist_directory).exists():
                backup_current = f"{self.persist_directory}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.move(self.persist_directory, backup_current)
            
            # 恢复数据库
            shutil.copytree(source_db, self.persist_directory)
            
            # 重新初始化
            self._initialize()
            
            logger.success(f"✅ 向量数据库恢复成功: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 向量数据库恢复失败: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 测试连接
            collection = self.client._collection
            count = collection.count()
            
            # 测试搜索
            test_docs = self.client.similarity_search("测试", k=1)
            
            return {
                "status": "healthy",
                "collection_name": self.collection_name,
                "document_count": count,
                "embeddings_model": self.embeddings_model,
                "persist_directory": self.persist_directory,
                "last_check": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "collection_name": self.collection_name,
                "last_check": datetime.now().isoformat()
            }


class VectorStoreFactory:
    """向量数据库工厂类"""
    
    _instances = {}
    
    @classmethod
    def get_instance(cls, collection_name: str = None) -> UnifiedVectorStore:
        """获取向量数据库实例（单例模式）"""
        key = collection_name or settings.VECTOR_DB_COLLECTION
        
        if key not in cls._instances:
            cls._instances[key] = UnifiedVectorStore(collection_name=key)
        
        return cls._instances[key]
    
    @classmethod
    def clear_instances(cls):
        """清除所有实例（主要用于测试）"""
        cls._instances.clear()


# 全局向量数据库实例
vector_store = VectorStoreFactory.get_instance()


if __name__ == "__main__":
    """测试统一向量数据库"""
    
    # 初始化
    vs = UnifiedVectorStore()
    
    # 健康检查
    health = vs.health_check()
    print(f"健康检查: {health}")
    
    # 获取统计信息
    stats = vs.get_stats()
    print(f"统计信息: {stats}")
    
    # 创建测试文档
    from langchain.docstore.document import Document
    
    test_docs = [
        Document(
            page_content="这是一个博客文章的内容，关于Python编程。",
            metadata={
                "title": "Python编程指南",
                "author": "张三",
                "platform": "博客",
                "tags": ["Python", "编程", "教程"]
            }
        ),
        Document(
            page_content="这是一个面试经验分享，关于字节跳动的前端面试。",
            metadata={
                "title": "字节跳动前端面试经验",
                "company": "字节跳动",
                "position": "前端工程师",
                "platform": "牛客网",
                "tags": ["面试", "前端", "字节跳动"]
            }
        )
    ]
    
    # 添加文档
    doc_ids = vs.add_documents(test_docs, doc_type="test")
    print(f"添加的文档ID: {doc_ids}")
    
    # 测试搜索
    search_results = vs.similarity_search("Python编程", k=5)
    print(f"搜索结果数量: {len(search_results)}")
    
    # 按类型搜索
    blog_results = vs.search_by_type("编程", doc_type="test")
    print(f"博客搜索结果数量: {len(blog_results)}")
    
    # 多类型搜索
    multi_results = vs.search_multi_type("编程", doc_types=["test"], k_per_type=2)
    print(f"多类型搜索结果: {multi_results}")
    
    print("✅ 统一向量数据库测试完成")