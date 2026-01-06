from prometheus_client import Counter, Histogram, Gauge
from functools import wraps
import psutil
import threading
import time

# --- API 监控指标 ---
# 请求计数
api_requests_total = Counter(
    "api_requests_total",
    "Total number of API requests",
    ["method", "endpoint", "status_code"],
)

# 请求处理时间
api_request_duration_seconds = Histogram(
    "api_request_duration_seconds",
    "API request duration in seconds",
    ["method", "endpoint"],
)

# 活跃连接数
api_active_connections = Gauge(
    "api_active_connections", "Number of active API connections"
)


# --- Redis 监控指标 ---
# Redis 缓存命中率
redis_cache_hits = Counter("redis_cache_hits", "Redis cache hits")
redis_cache_misses = Counter("redis_cache_misses", "Redis cache misses")

# Redis 命令执行计数
redis_commands_total = Counter(
    "redis_commands_total", "Total number of Redis commands executed", ["command"]
)


# --- 查询缓存监控指标 ---
# 查询缓存命中
cache_hits = Counter("cache_hits", "Cache hits")
# 查询缓存未命中
cache_misses = Counter("cache_misses", "Cache misses")
# 查询缓存总数
cache_queries_total = Counter("cache_queries_total", "Total cache queries")
# 相似查询命中
similar_cache_hits = Counter("similar_cache_hits", "Similar cache hits")
# 查询缓存延迟
cache_operation_duration_seconds = Histogram(
    "cache_operation_duration_seconds", "Cache operation duration in seconds", ["operation"]
)


# --- LLM 监控指标 ---
# LLM 调用计数
llm_calls_total = Counter(
    "llm_calls_total",
    "Total number of LLM calls",
    ["model", "status"],  # status: success, failure, cache_hit
)

# LLM 调用延迟
llm_call_duration_seconds = Histogram(
    "llm_call_duration_seconds", "LLM call duration in seconds", ["model"]
)


# --- 系统资源监控指标 ---
# CPU 使用率
system_cpu_usage = Gauge("system_cpu_usage", "Current CPU usage percentage")

# 内存使用情况
system_memory_usage = Gauge("system_memory_usage", "Current memory usage percentage")

system_memory_available = Gauge(
    "system_memory_available_bytes", "Available memory in bytes"
)

# 磁盘使用情况
system_disk_usage = Gauge(
    "system_disk_usage", "Current disk usage percentage", ["path"]
)

# 网络 IO
system_network_bytes_sent = Counter(
    "system_network_bytes_sent_total", "Total bytes sent over network"
)

system_network_bytes_recv = Counter(
    "system_network_bytes_recv_total", "Total bytes received over network"
)


# 监控装饰器，用于统计函数执行时间和计数
def monitor_function(func, counter=None, histogram=None, labels=None):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if counter:
            counter.labels(**(labels or {})).inc()

        if histogram:
            with histogram.labels(**(labels or {})).time():
                return await func(*args, **kwargs)
        else:
            return await func(*args, **kwargs)

    return wrapper


# 系统资源监控更新函数
def update_system_metrics():
    """定期更新系统资源监控指标"""
    while True:
        try:
            # 更新 CPU 使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            system_cpu_usage.set(cpu_percent)

            # 更新内存使用情况
            mem = psutil.virtual_memory()
            system_memory_usage.set(mem.percent)
            system_memory_available.set(mem.available)

            # 更新磁盘使用情况
            disk_usage = psutil.disk_usage("/")
            system_disk_usage.labels(path="/").set(disk_usage.percent)

            # 更新网络 IO
            net_io = psutil.net_io_counters()
            system_network_bytes_sent.inc(net_io.bytes_sent)
            system_network_bytes_recv.inc(net_io.bytes_recv)

        except Exception as e:
            # 记录错误但不中断监控线程
            import logging

            logging.error(f"Failed to update system metrics: {e}")

        # 每 10 秒更新一次
        time.sleep(10)


# 启动系统资源监控线程
_system_monitor_thread = None


def start_system_monitor():
    """启动系统资源监控线程"""
    global _system_monitor_thread

    if not _system_monitor_thread or not _system_monitor_thread.is_alive():
        _system_monitor_thread = threading.Thread(
            target=update_system_metrics, daemon=True
        )
        _system_monitor_thread.start()
