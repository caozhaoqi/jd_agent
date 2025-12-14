from typing import Dict, Set, Optional
import asyncio
import uuid
from loguru import logger

class SSEConnection:
    """
    SSE连接对象，用于管理单个客户端连接
    """
    
    def __init__(self, client_id: str, send_queue: asyncio.Queue):
        self.client_id = client_id
        self.send_queue = send_queue
        self.last_active = asyncio.get_event_loop().time()
        self.is_connected = True
        self.heartbeat_task: Optional[asyncio.Task] = None
    
    async def send(self, data: str):
        """
        发送数据到客户端
        """
        if self.is_connected:
            await self.send_queue.put(data)
            self.last_active = asyncio.get_event_loop().time()
    
    async def close(self):
        """
        关闭连接
        """
        self.is_connected = False
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        try:
            # 清空队列
            while not self.send_queue.empty():
                self.send_queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
    
    def is_expired(self, timeout: int = 300) -> bool:
        """
        检查连接是否过期
        """
        return asyncio.get_event_loop().time() - self.last_active > timeout
    
    async def start_heartbeat(self, interval: int = 30):
        """
        启动心跳机制
        """
        while self.is_connected:
            try:
                await self.send("data: \n\n")  # 发送空消息作为心跳
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"💓 [SSE Heartbeat] Error for client {self.client_id}: {e}")
                break

class SSEManager:
    """
    SSE连接管理器，用于跟踪和管理所有活跃的SSE连接
    """
    
    def __init__(self):
        self.connections: Dict[str, SSEConnection] = {}
        self.cleanup_task: Optional[asyncio.Task] = None
        self.lock = asyncio.Lock()
    
    async def __aenter__(self):
        self.start_cleanup_task()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
    
    def start_cleanup_task(self):
        """
        启动定期清理任务
        """
        async def cleanup():
            while True:
                await asyncio.sleep(60)  # 每分钟清理一次
                await self._cleanup_expired_connections()
        
        self.cleanup_task = asyncio.create_task(cleanup())
        self.cleanup_task.add_done_callback(lambda task: logger.error(f"🧹 [SSE Cleanup] Task failed: {task.exception()}") if task.exception() else None)
    
    async def _cleanup_expired_connections(self):
        """
        清理过期的连接
        """
        async with self.lock:
            expired_ids = [client_id for client_id, conn in self.connections.items() if conn.is_expired()]
            for client_id in expired_ids:
                logger.info(f"🧹 [SSE Cleanup] Removing expired connection: {client_id}")
                conn = self.connections.pop(client_id)
                await conn.close()
    
    async def add_connection(self) -> (str, asyncio.Queue):
        """
        添加一个新的SSE连接
        """
        client_id = str(uuid.uuid4())
        send_queue = asyncio.Queue()
        conn = SSEConnection(client_id, send_queue)
        
        async with self.lock:
            self.connections[client_id] = conn
            
        # 启动心跳
        conn.heartbeat_task = asyncio.create_task(conn.start_heartbeat())
        
        logger.info(f"➕ [SSE Manager] Added new connection: {client_id} (Total: {len(self.connections)})")
        return client_id, send_queue
    
    async def remove_connection(self, client_id: str):
        """
        移除一个SSE连接
        """
        async with self.lock:
            if client_id in self.connections:
                conn = self.connections.pop(client_id)
                await conn.close()
                logger.info(f"➖ [SSE Manager] Removed connection: {client_id} (Total: {len(self.connections)})")
    
    async def send_to_client(self, client_id: str, data: str):
        """
        向特定客户端发送数据
        """
        async with self.lock:
            if client_id in self.connections:
                await self.connections[client_id].send(data)
    
    async def broadcast(self, data: str):
        """
        向所有客户端广播数据
        """
        async with self.lock:
            for client_id, conn in self.connections.items():
                try:
                    await conn.send(data)
                except Exception as e:
                    logger.error(f"📢 [SSE Broadcast] Error sending to client {client_id}: {e}")
    
    async def cleanup(self):
        """
        清理所有连接和任务
        """
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        async with self.lock:
            for client_id, conn in self.connections.items():
                await conn.close()
            self.connections.clear()
        
        logger.info("🛡️ [SSE Manager] All connections and tasks cleaned up")
    
    def get_active_connections_count(self) -> int:
        """
        获取当前活跃连接数
        """
        return len(self.connections)

# 创建全局SSE管理器实例
sse_manager = SSEManager()