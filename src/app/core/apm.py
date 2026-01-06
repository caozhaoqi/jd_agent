from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry import context
import os
from functools import wraps
from typing import Callable, Any
import time

resource = Resource.create({
    ResourceAttributes.SERVICE_NAME: "jd-agent-api",
    ResourceAttributes.SERVICE_VERSION: "1.0.0",
    ResourceAttributes.DEPLOYMENT_ENVIRONMENT: os.getenv("ENVIRONMENT", "development")
})

tracer_provider = TracerProvider(resource=resource)
otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
    insecure=True
)
tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
trace.set_tracer_provider(tracer_provider)

meter_provider = MeterProvider(
    resource=resource,
    metric_readers=[
        PeriodicExportingMetricReader(
            OTLPMetricExporter(
                endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
                insecure=True
            ),
            export_interval_millis=60000
        )
    ]
)
metrics.set_meter_provider(meter_provider)

tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

request_counter = meter.create_counter(
    name="http.server.requests",
    description="Total number of HTTP requests",
    unit="1"
)

request_duration = meter.create_histogram(
    name="http.server.request.duration",
    description="HTTP request duration in seconds",
    unit="s"
)

db_query_duration = meter.create_histogram(
    name="db.query.duration",
    description="Database query duration in seconds",
    unit="s"
)

db_query_counter = meter.create_counter(
    name="db.query.count",
    description="Total number of database queries",
    unit="1"
)

cache_operations_counter = meter.create_counter(
    name="cache.operations",
    description="Total number of cache operations",
    unit="1"
)

active_connections_gauge = meter.create_up_down_counter(
    name="connections.active",
    description="Number of active connections",
    unit="1"
)

llm_token_counter = meter.create_counter(
    name="llm.tokens",
    description="Total number of LLM tokens",
    unit="1"
)

llm_duration = meter.create_histogram(
    name="llm.duration",
    description="LLM call duration in seconds",
    unit="s"
)

def setup_fastapi_instrumentation(app):
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()

def monitor_endpoint(path: str, method: str):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                status_code = 200
                return result
            except Exception as e:
                status_code = 500
                raise
            finally:
                duration = time.time() - start_time
                request_counter.add(1, {"path": path, "method": method})
                request_duration.record(duration, {"path": path, "method": method})
        return wrapper
    return decorator

def monitor_db_query(query_type: str):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                db_query_counter.add(1, {"type": query_type, "status": "success"})
                return result
            except Exception as e:
                db_query_counter.add(1, {"type": query_type, "status": "error"})
                raise
            finally:
                duration = time.time() - start_time
                db_query_duration.record(duration, {"type": query_type})
        return wrapper
    return decorator

def monitor_cache_operation(operation: str):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                result = await func(*args, **kwargs)
                cache_operations_counter.add(1, {"operation": operation, "status": "hit"})
                return result
            except Exception as e:
                cache_operations_counter.add(1, {"operation": operation, "status": "miss"})
                raise
        return wrapper
    return decorator

class APMClient:
    def __init__(self):
        self._tracer = trace.get_tracer(__name__)
        self._meter = metrics.get_meter(__name__)
        
    def start_span(self, name: str, attributes: dict = None):
        span = self._tracer.start_span(name)
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        return span
        
    def record_llm_call(self, model: str, duration: float, tokens: int = None, success: bool = True):
        llm_duration.record(duration, {"model": model})
        if tokens:
            llm_token_counter.add(tokens, {"model": model})
        llm_calls_status = "success" if success else "error"
        llm_counter = self._meter.create_counter(
            name="llm.calls",
            description="Total number of LLM calls"
        )
        counter.add(1, {"model": model, "status": llm_calls_status})
        
    def record_error(self, error: Exception, context: dict = None):
        with self._tracer.start_as_current_span("error") as span:
            span.set_attribute("error.type", type(error).__name__)
            span.set_attribute("error.message", str(error))
            if context:
                for key, value in context.items():
                    span.set_attribute(f"context.{key}", value)
                    
apm_client = APMClient()
