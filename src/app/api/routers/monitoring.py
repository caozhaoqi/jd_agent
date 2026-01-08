from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, REGISTRY
from core.redis_client import redis_client
from core.query_cache import query_cache
from core.models import ChatSession, ChatMessage
from sqlalchemy.ext.asyncio import AsyncSession
from core.db_auth import get_db_dependency
from sqlalchemy import func
import time

router = APIRouter()

@router.get("/metrics", response_class=PlainTextResponse)
def get_metrics():
    """暴露Prometheus指标"""
    return PlainTextResponse(generate_latest(REGISTRY))

@router.get("/dashboard/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db_dependency)):
    """获取仪表板统计信息"""
    # 获取系统时间
    current_time = time.time()
    
    # 获取缓存统计
    redis_stats = redis_client.get_stats()
    query_cache_stats = query_cache.get_cache_stats()
    
    # 计算缓存命中率
    total_cache_requests = redis_stats.get("hits", 0) + redis_stats.get("misses", 0)
    cache_hit_rate = redis_stats.get("hits", 0) / max(total_cache_requests, 1)
    
    # 获取数据库统计
    try:
        # 获取会话总数
        session_count_result = await db.execute(func.count(ChatSession.id))
        session_count = session_count_result.scalar_one_or_none() or 0
        
        # 获取消息总数
        message_count_result = await db.execute(func.count(ChatMessage.id))
        message_count = message_count_result.scalar_one_or_none() or 0
        
        # 获取最近24小时的会话数
        last_24h = current_time - 86400
        recent_sessions_result = await db.execute(
            func.count(ChatSession.id).where(ChatSession.created_at >= last_24h)
        )
        recent_sessions = recent_sessions_result.scalar_one_or_none() or 0
        
    except Exception as e:
        return {
            "error": f"获取数据库统计失败: {e}",
            "redis_stats": redis_stats,
            "query_cache_stats": query_cache_stats,
            "cache_hit_rate": cache_hit_rate
        }
    
    return {
        "timestamp": current_time,
        "cache_stats": {
            "total_requests": total_cache_requests,
            "hits": redis_stats.get("hits", 0),
            "misses": redis_stats.get("misses", 0),
            "hit_rate": cache_hit_rate
        },
        "redis_info": redis_stats,
        "query_cache_info": query_cache_stats,
        "database_stats": {
            "total_sessions": session_count,
            "total_messages": message_count,
            "recent_sessions_24h": recent_sessions
        }
    }

@router.get("/health")
def health_check():
    """健康检查端点"""
    return {
        "status": "ok",
        "timestamp": time.time(),
        "redis_connected": redis_client.is_connected
    }
