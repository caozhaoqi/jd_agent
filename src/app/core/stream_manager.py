import asyncio
from contextvars import ContextVar
from typing import Optional

# 定义一个上下文变量，用来存储当前请求的队列
# 每个请求进来都会有一个独立的 Queue，互不冲突
_msg_queue: ContextVar[Optional[asyncio.Queue]] = ContextVar("msg_queue", default=None)

def init_stream_queue():
    """初始化当前请求的队列"""
    q = asyncio.Queue()
    _msg_queue.set(q)
    return q

def get_stream_queue() -> Optional[asyncio.Queue]:
    """获取当前请求的队列"""
    return _msg_queue.get()

async def send_thought(step: str, detail: str = ""):
    """
    节点调用的发送函数 (替代 logger.debug)
    """
    q = get_stream_queue()
    if q:
        # 构造前端 ThinkingBlock 需要的数据格式
        data = {
            "type": "thought",
            "content": f"{step} {detail}".strip()
        }
        await q.put(data)