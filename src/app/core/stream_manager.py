import asyncio
from typing import Optional, Dict, Any, Callable

# 定义一个全局的队列存储，使用 thread_id 作为键
_msg_queues: Dict[str, asyncio.Queue] = {}

# 定义一个队列访问器，允许外部设置访问队列的方法
_queue_accessor: Optional[Callable[[], Optional[asyncio.Queue]]] = None


def init_stream_queue(queue: Optional[asyncio.Queue] = None, thread_id: Optional[str] = None) -> asyncio.Queue:
    """在请求开始时初始化队列"""
    q = queue if queue is not None else asyncio.Queue()
    if thread_id:
        _msg_queues[thread_id] = q
    return q


def set_queue_accessor(accessor: Callable[[], Optional[asyncio.Queue]]):
    """设置队列访问器"""
    global _queue_accessor
    _queue_accessor = accessor


def get_stream_queue(thread_id: Optional[str] = None) -> Optional[asyncio.Queue]:
    """获取当前请求的队列"""
    if thread_id:
        return _msg_queues.get(thread_id)
    if _queue_accessor:
        return _queue_accessor()
    return None

async def send_thought(step_title: str, detail: str = "", thread_id: Optional[str] = None):
    """
    各 Agent 节点调用此函数发送思考过程
    """
    q = get_stream_queue(thread_id)
    if q:
        await q.put({
            "type": "thought",
            "content": step_title,
            "detail": detail
        })

async def send_token(text: str, thread_id: Optional[str] = None):
    """发送最终生成的 Token"""
    q = get_stream_queue(thread_id)
    if q:
        await q.put({
            "type": "token",
            "content": text
        })

async def send_done(thread_id: Optional[str] = None):
    """发送结束信号"""
    q = get_stream_queue(thread_id)
    if q:
        await q.put(None) # None 代表结束


async def send_data(key: str, data: Any, thread_id: Optional[str] = None):
    """
    发送结构化数据给前端仪表盘
    key: 'user_profile' | 'rag_sources' | 'current_step'
    """
    q = get_stream_queue(thread_id)
    if q:
        await q.put({
            "type": "data",
            "key": key,
            "value": data
        })


def clear_queue(thread_id: str):
    """清除指定 thread_id 的队列"""
    if thread_id in _msg_queues:
        del _msg_queues[thread_id]