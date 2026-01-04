import asyncio
import threading
from typing import Optional, Dict, Any, Callable
from loguru import logger

# 定义一个全局的队列存储，使用 thread_id 作为键
_msg_queues: Dict[str, asyncio.Queue] = {}

# 使用线程本地存储来避免多请求竞争条件
_thread_local = threading.local()


def init_stream_queue(
    queue: Optional[asyncio.Queue] = None, thread_id: Optional[str] = None
) -> asyncio.Queue:
    """在请求开始时初始化队列"""
    q = queue if queue is not None else asyncio.Queue()
    if thread_id:
        _msg_queues[thread_id] = q
        logger.info(
            f"📤 [Stream Manager] 队列已初始化: thread_id={thread_id}, 队列对象={id(q)}, 当前队列数量: {len(_msg_queues)}"
        )
    return q


def set_queue_accessor(accessor: Callable[[], Optional[asyncio.Queue]]):
    """设置队列访问器（仅用于向后兼容）"""
    # 使用线程本地存储保存访问器
    _thread_local.queue_accessor = accessor
    logger.info(
        f"📤 [Stream Manager] 队列访问器已设置: thread={threading.current_thread().name}"
    )


def get_stream_queue(thread_id: Optional[str] = None) -> Optional[asyncio.Queue]:
    """获取当前请求的队列 - 优先使用 thread_id，然后使用线程本地访问器"""
    if thread_id:
        queue = _msg_queues.get(thread_id)
        logger.info(
            f"📤 [Stream Manager] 获取队列: thread_id={thread_id}, 队列存在={queue is not None}, 当前队列数量: {len(_msg_queues)}"
        )
        return queue
    
    # 尝试使用线程本地访问器
    accessor = getattr(_thread_local, 'queue_accessor', None)
    if accessor:
        queue = accessor()
        logger.info(
            f"📤 [Stream Manager] 通过线程访问器获取队列: 成功={queue is not None}"
        )
        return queue
    
    logger.warning(
        f"📤 [Stream Manager] 获取队列失败: thread_id=None, thread_accessor={accessor is not None}"
    )
    return None


def get_current_thread_id() -> Optional[str]:
    """获取当前线程的 thread_id"""
    return getattr(_thread_local, 'thread_id', None)


def set_current_thread_id(thread_id: str):
    """设置当前线程的 thread_id"""
    _thread_local.thread_id = thread_id
    logger.info(
        f"📤 [Stream Manager] 设置线程 thread_id: {thread_id}, thread={threading.current_thread().name}"
    )


async def send_thought(
    step_title: str,
    detail: str = "",
    thread_id: Optional[str] = None,
    delay: float = 1.0,
):
    """
    各 Agent 节点调用此函数发送思考过程
    delay: 发送消息前的延迟时间（秒），用于模拟真实处理时间
    """
    # 如果没有提供 thread_id，尝试从线程本地存储获取
    if not thread_id:
        thread_id = get_current_thread_id()
    
    q = get_stream_queue(thread_id)
    if q:
        # 添加延迟以模拟真实的处理时间
        await asyncio.sleep(delay)
        logger.info(
            f"📤 [Stream Manager] 发送思考过程: {step_title}, thread_id: {thread_id}, queue_id: {id(q)}"
        )
        await q.put({"type": "thought", "content": step_title, "detail": detail})
    else:
        logger.error(
            f"❌ [Stream Manager] 无法获取队列发送思考过程: {step_title}, thread_id: {thread_id}"
        )


async def send_token(text: str, thread_id: Optional[str] = None):
    """发送最终生成的 Token"""
    # 如果没有提供 thread_id，尝试从线程本地存储获取
    if not thread_id:
        thread_id = get_current_thread_id()
        
    q = get_stream_queue(thread_id)
    if q:
        logger.info(
            f"📤 [Stream Manager] 发送Token: 长度={len(text)}, thread_id: {thread_id}"
        )
        await q.put({"type": "token", "content": text})


async def send_done(thread_id: Optional[str] = None):
    """发送结束信号"""
    # 如果没有提供 thread_id，尝试从线程本地存储获取
    if not thread_id:
        thread_id = get_current_thread_id()
        
    q = get_stream_queue(thread_id)
    if q:
        logger.info(
            f"📤 [Stream Manager] 发送DONE信号, thread_id: {thread_id}"
        )
        await q.put(None)  # None 代表结束
    else:
        logger.error(
            f"❌ [Stream Manager] 无法获取队列发送DONE信号, thread_id: {thread_id}"
        )


async def send_data(key: str, data: Any, thread_id: Optional[str] = None):
    """
    发送结构化数据给前端仪表盘
    key: 'user_profile' | 'rag_sources' | 'current_step'
    """
    # 如果没有提供 thread_id，尝试从线程本地存储获取
    if not thread_id:
        thread_id = get_current_thread_id()
        
    q = get_stream_queue(thread_id)
    if q:
        logger.info(
            f"📤 [Stream Manager] 发送数据: key={key}, data_type={type(data).__name__}, thread_id: {thread_id}"
        )
        await q.put({"type": "data", "key": key, "value": data})
    else:
        logger.error(
            f"❌ [Stream Manager] 无法获取队列发送数据: key={key}, thread_id: {thread_id}"
        )


def clear_queue(thread_id: str):
    """清除指定 thread_id 的队列"""
    if thread_id in _msg_queues:
        logger.info(
            f"📤 [Stream Manager] 开始清除队列: thread_id={thread_id}, 当前队列数量: {len(_msg_queues)}"
        )
        del _msg_queues[thread_id]
        logger.info(
            f"📤 [Stream Manager] 队列已清除: thread_id={thread_id}, 当前队列数量: {len(_msg_queues)}"
        )
    else:
        logger.warning(
            f"📤 [Stream Manager] 尝试清除不存在的队列: thread_id={thread_id}, 当前队列数量: {len(_msg_queues)}"
        )
