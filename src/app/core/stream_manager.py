import asyncio
from contextvars import ContextVar
from typing import Optional, Dict, Any

# 定义上下文变量，确保并发请求互不干扰
_msg_queue: ContextVar[Optional[asyncio.Queue]] = ContextVar("msg_queue", default=None)

def init_stream_queue():
    """在请求开始时初始化队列"""
    q = asyncio.Queue()
    _msg_queue.set(q)
    return q

def get_stream_queue() -> Optional[asyncio.Queue]:
    return _msg_queue.get()

async def send_thought(step_title: str, detail: str = ""):
    """
    各 Agent 节点调用此函数发送思考过程
    """
    q = get_stream_queue()
    if q:
        await q.put({
            "type": "thought",
            "content": step_title,
            "detail": detail
        })

async def send_token(text: str):
    """发送最终生成的 Token"""
    q = get_stream_queue()
    if q:
        await q.put({
            "type": "token",
            "content": text
        })

async def send_done():
    """发送结束信号"""
    q = get_stream_queue()
    if q:
        await q.put(None) # None 代表结束


async def send_data(key: str, data: Any):
    """
    发送结构化数据给前端仪表盘
    key: 'user_profile' | 'rag_sources' | 'current_step'
    """
    q = get_stream_queue()
    if q:
        await q.put({
            "type": "data",
            "key": key,
            "value": data
        })