import os
import time
import hashlib
import threading
import asyncio
from pathlib import Path
from typing import Dict, Set, Optional, Callable
from datetime import datetime
from loguru import logger
from utils.logger import logger as sys_logger

class KnowledgeBaseAutoUpdater:
    """
    知识库自动更新服务
    功能：
    - 监控文档目录变化
    - 自动检测新增、修改、删除的文档
    - 支持增量更新和全量重建
    - 提供更新回调机制
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._watched_dirs: Dict[str, Dict] = {}
        self._file_hashes: Dict[str, str] = {}
        self._update_callbacks: Set[Callable] = set()
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._check_interval = 30  # 默认30秒检查一次
        self._last_update_time: Optional[datetime] = None
        self._update_stats = {
            "total_updates": 0,
            "added_files": 0,
            "modified_files": 0,
            "deleted_files": 0,
            "errors": 0
        }

    def start(self, check_interval: int = 30):
        """
        启动自动更新服务
        
        Args:
            check_interval: 检查间隔（秒）
        """
        if self._running:
            logger.warning("[AutoUpdate] 服务已在运行中")
            return
            
        self._check_interval = check_interval
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        logger.success(f"[AutoUpdate] 知识库自动更新服务已启动 (检查间隔: {check_interval}s)")

    def stop(self):
        """停止自动更新服务"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
            self._monitor_thread = None
        
        logger.info("[AutoUpdate] 知识库自动更新服务已停止")

    def add_watched_directory(
        self, 
        dir_path: str, 
        extensions: tuple = (".md", ".txt", ".json", ".pdf"),
        recursive: bool = True,
        auto_rebuild: bool = True
    ):
        """
        添加监控目录
        
        Args:
            dir_path: 目录路径
            extensions: 监控的文件扩展名
            recursive: 是否递归监控子目录
            auto_rebuild: 是否自动触发重建
        """
        abs_path = os.path.abspath(dir_path)
        
        if not os.path.exists(abs_path):
            logger.error(f"[AutoUpdate] 目录不存在: {abs_path}")
            return False
        
        if abs_path in self._watched_dirs:
            logger.warning(f"[AutoUpdate] 目录已在监控中: {abs_path}")
            return True
        
        self._watched_dirs[abs_path] = {
            "extensions": extensions,
            "recursive": recursive,
            "auto_rebuild": auto_rebuild
        }
        
        self._scan_directory(abs_path, extensions, recursive)
        logger.info(f"[AutoUpdate] 添加监控目录: {abs_path}")
        return True

    def remove_watched_directory(self, dir_path: str):
        """移除监控目录"""
        abs_path = os.path.abspath(dir_path)
        
        if abs_path in self._watched_dirs:
            del self._watched_dirs[abs_path]
            for key in list(self._file_hashes.keys()):
                if key.startswith(abs_path):
                    del self._file_hashes[key]
            logger.info(f"[AutoUpdate] 移除监控目录: {abs_path}")
            return True
        return False

    def register_update_callback(self, callback: Callable):
        """注册更新回调函数"""
        self._update_callbacks.add(callback)
        logger.debug(f"[AutoUpdate] 注册回调函数: {callback.__name__}")

    def unregister_update_callback(self, callback: Callable):
        """取消注册更新回调函数"""
        self._update_callbacks.discard(callback)

    def trigger_rebuild(self, full_rebuild: bool = False):
        """
        手动触发重建
        
        Args:
            full_rebuild: 是否全量重建
        """
        logger.info(f"[AutoUpdate] 手动触发重建 (全量: {full_rebuild})")
        self._notify_callbacks({
            "type": "manual",
            "full_rebuild": full_rebuild,
            "timestamp": datetime.now()
        })

    def get_status(self) -> dict:
        """获取服务状态"""
        return {
            "running": self._running,
            "watched_directories": list(self._watched_dirs.keys()),
            "monitored_files": len(self._file_hashes),
            "check_interval": self._check_interval,
            "last_update_time": self._last_update_time.isoformat() if self._last_update_time else None,
            "update_stats": self._update_stats.copy()
        }

    def _scan_directory(self, dir_path: str, extensions: tuple, recursive: bool):
        """扫描目录并计算文件哈希"""
        changes = {"added": [], "modified": [], "deleted": []}
        
        current_files = set()
        
        if recursive:
            pattern = "**/*"
        else:
            pattern = "*"
            
        for ext in extensions:
            for file_path in Path(dir_path).glob(f"{pattern}{ext}"):
                file_str = str(file_path)
                current_files.add(file_str)
                
                file_hash = self._compute_file_hash(file_str)
                
                if file_str not in self._file_hashes:
                    changes["added"].append(file_str)
                elif self._file_hashes[file_str] != file_hash:
                    changes["modified"].append(file_str)
                
                self._file_hashes[file_str] = file_hash
        
        for existing_file in list(self._file_hashes.keys()):
            if existing_file.startswith(dir_path) and existing_file not in current_files:
                changes["deleted"].append(existing_file)
                del self._file_hashes[existing_file]
        
        return changes

    def _compute_file_hash(self, file_path: str) -> str:
        """计算文件哈希值"""
        try:
            hasher = hashlib.md5()
            with open(file_path, 'rb') as f:
                hasher.update(f.read(8192))
            return hasher.hexdigest()
        except Exception as e:
            logger.warning(f"[AutoUpdate] 计算文件哈希失败: {file_path}, error: {e}")
            return ""

    def _monitor_loop(self):
        """监控主循环"""
        while self._running:
            try:
                changes_detected = False
                all_changes = {
                    "added": [],
                    "modified": [],
                    "deleted": [],
                    "timestamp": datetime.now()
                }
                
                for dir_path, config in self._watched_dirs.items():
                    if not self._running:
                        break
                        
                    changes = self._scan_directory(
                        dir_path, 
                        config["extensions"], 
                        config["recursive"]
                    )
                    
                    if changes["added"] or changes["modified"] or changes["deleted"]:
                        changes_detected = True
                        all_changes["added"].extend(changes["added"])
                        all_changes["modified"].extend(changes["modified"])
                        all_changes["deleted"].extend(changes["deleted"])
                        
                        self._update_stats["added_files"] += len(changes["added"])
                        self._update_stats["modified_files"] += len(changes["modified"])
                        self._update_stats["deleted_files"] += len(changes["deleted"])
                
                if changes_detected:
                    self._last_update_time = datetime.now()
                    self._update_stats["total_updates"] += 1
                    
                    logger.info(
                        f"[AutoUpdate] 检测到变化 - 新增: {len(all_changes['added'])}, "
                        f"修改: {len(all_changes['modified'])}, 删除: {len(all_changes['deleted'])}"
                    )
                    
                    self._notify_callbacks(all_changes)
                
            except Exception as e:
                self._update_stats["errors"] += 1
                logger.error(f"[AutoUpdate] 监控循环错误: {e}")
            
            time.sleep(self._check_interval)

    def _notify_callbacks(self, changes: dict):
        """通知所有注册的回调函数"""
        for callback in self._update_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.run(callback(changes))
                else:
                    callback(changes)
            except Exception as e:
                logger.error(f"[AutoUpdate] 回调函数执行失败: {e}")
                self._update_stats["errors"] += 1

auto_updater = KnowledgeBaseAutoUpdater()
