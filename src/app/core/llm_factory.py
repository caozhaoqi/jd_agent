from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_deepseek import ChatDeepSeek
from core.config import settings
from core.redis_client import redis_client
import hashlib
import json
import time
from typing import Any, List, Dict, Optional, Union
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.runnables import Runnable
from loguru import logger
from core.monitoring import llm_calls_total, llm_call_duration_seconds


SUPPORTED_PROVIDERS = {
    "openai": {
        "class": ChatOpenAI,
        "default_model": "gpt-4",
        "params": ["model_name", "openai_api_key", "openai_api_base", "temperature", "max_tokens"]
    },
    "anthropic": {
        "class": ChatAnthropic,
        "default_model": "claude-3-sonnet-20240229",
        "params": ["model", "anthropic_api_key", "temperature", "max_tokens"]
    },
    "deepseek": {
        "class": ChatDeepSeek,
        "default_model": "deepseek-chat",
        "params": ["model", "deepseek_api_key", "deepseek_base_url", "temperature", "max_tokens"]
    }
}


class CachedLLM(Runnable):
    def __init__(
        self, llm, cache_expire_seconds: int = settings.CACHE_EXPIRATION_LLM
    ):
        self.llm = llm
        self.cache_expire_seconds = cache_expire_seconds

    def _normalize_content(self, content: Any) -> Any:
        if isinstance(content, str):
            return " ".join(content.split())
        if isinstance(content, list):
            return [self._normalize_content(item) for item in content]
        if isinstance(content, dict):
            return {k: self._normalize_content(v) for k, v in content.items()}
        return content

    def _generate_cache_key(self, messages: List[BaseMessage], **kwargs) -> str:
        serializable_messages = []
        for msg in messages:
            try:
                normalized_content = self._normalize_content(msg.content)
                serializable_messages.append(
                    {
                        "type": msg.type,
                        "content": normalized_content,
                        "additional_kwargs": msg.additional_kwargs,
                    }
                )
            except Exception as e:
                logger.warning(f"序列化消息失败: {e}, 使用 str() 降级。")
                serializable_messages.append(str(msg))

        cache_data = {
            "model_name": getattr(self.llm, 'model_name', getattr(self.llm, 'model', 'unknown')),
            "temperature": getattr(self.llm, 'temperature', 0.5),
            "messages": serializable_messages,
            "other_kwargs": {k: v for k, v in kwargs.items() if k not in ['streaming']}
        }

        try:
            cache_str = json.dumps(cache_data, sort_keys=True)
            cache_key = f"llm_cache:{hashlib.md5(cache_str.encode()).hexdigest()}"
            logger.debug(f"生成的缓存键: {cache_key} for data: {cache_str[:200]}...")
            return cache_key
        except Exception as e:
            logger.error(f"生成缓存键失败: {e}")
            return f"llm_cache:fallback_{hash(str(messages))}"

    async def ainvoke(self, input_data: Any, config: Any = None, **kwargs) -> Any:
        if isinstance(input_data, list) and len(input_data) > 0 and isinstance(input_data[0], BaseMessage):
            messages = input_data
        elif isinstance(input_data, dict) and "messages" in input_data:
            messages = input_data["messages"]
        else:
            return await self.llm.ainvoke(input_data, config=config, **kwargs)
        
        model_name = getattr(self.llm, 'model_name', getattr(self.llm, 'model', 'unknown'))
        
        if kwargs.get("streaming", False) or getattr(self.llm, 'streaming', False):
            logger.debug("流式请求，跳过缓存")
            return await self._measure_and_call_llm(self.llm.ainvoke, messages, model_name, config=config, **kwargs)

        cache_key = self._generate_cache_key(messages, **kwargs)
        cached_result = redis_client.get(cache_key)

        if cached_result:
            logger.info(f"缓存命中: {cache_key}")
            llm_calls_total.labels(model=model_name, status="cache_hit").inc()
            return AIMessage.model_validate_json(cached_result)

        logger.info(f"缓存未命中: {cache_key}")
        result = await self._measure_and_call_llm(self.llm.ainvoke, messages, model_name, config=config, **kwargs)

        try:
            redis_client.set(cache_key, result.model_dump_json(), self.cache_expire_seconds)
            logger.info(f"结果已缓存: {cache_key}")
        except Exception as e:
            logger.error(f"缓存结果失败: {e}")

        return result

    async def _measure_and_call_llm(self, method, messages, model_name, config=None, **kwargs):
        start_time = time.time()
        try:
            if config is not None:
                result = await method(messages, config=config, **kwargs)
            else:
                result = await method(messages, **kwargs)
            duration = time.time() - start_time
            llm_calls_total.labels(model=model_name, status="success").inc()
            llm_call_duration_seconds.labels(model=model_name).observe(duration)
            return result
        except Exception as e:
            llm_calls_total.labels(model=model_name, status="failure").inc()
            raise e

    def invoke(self, input_data: Any, config: Any = None, **kwargs) -> Any:
        return self.llm.invoke(input_data, config=config, **kwargs)
    
    async def astream(self, input_data: Any, config: Any = None, **kwargs):
        async for chunk in self.llm.astream(input_data, config=config, **kwargs):
            yield chunk
    
    def stream(self, input_data: Any, config: Any = None, **kwargs):
        for chunk in self.llm.stream(input_data, config=config, **kwargs):
            yield chunk
    
    def __getattr__(self, name: str):
        return getattr(self.llm, name)


def get_llm(
    provider: str = "openai",
    model: Optional[str] = None,
    temperature: float = 0.5,
    max_tokens: int = 1000,
    streaming: bool = False,
    use_cache: bool = True,
    **kwargs
) -> Runnable:
    """
    获取 LLM 实例，支持多种模型提供商
    
    Args:
        provider: 模型提供商 (openai, anthropic, deepseek)
        model: 模型名称，不指定则使用默认值
        temperature: 温度参数
        max_tokens: 最大输出token
        streaming: 是否启用流式输出
        use_cache: 是否启用缓存
        **kwargs: 其他提供商特定参数
    """
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"不支持的模型提供商: {provider}，可选: {list(SUPPORTED_PROVIDERS.keys())}")
    
    provider_config = SUPPORTED_PROVIDERS[provider]
    llm_class = provider_config["class"]
    default_model = provider_config["default_model"]
    
    model = model or default_model
    
    llm_kwargs = {
        "temperature": temperature,
        "max_tokens": max_tokens,
        "streaming": streaming
    }
    
    if provider == "openai":
        llm_kwargs.update({
            "model": model,
            "openai_api_key": settings.OPENAI_API_KEY,
            "openai_api_base": settings.OPENAI_API_BASE
        })
    elif provider == "anthropic":
        llm_kwargs.update({
            "model": model,
            "anthropic_api_key": settings.ANTHROPIC_API_KEY if hasattr(settings, 'ANTHROPIC_API_KEY') else kwargs.get('anthropic_api_key')
        })
    elif provider == "deepseek":
        llm_kwargs.update({
            "model": model,
            "deepseek_api_key": settings.DEEPSEEK_API_KEY if hasattr(settings, 'DEEPSEEK_API_KEY') else kwargs.get('deepseek_api_key'),
            "deepseek_base_url": settings.DEEPSEEK_API_BASE if hasattr(settings, 'DEEEPSEEK_API_BASE') else kwargs.get('deepseek_base_url', 'https://api.deepseek.com/v1')
        })
    
    llm_kwargs.update(kwargs)
    
    llm = llm_class(**llm_kwargs)
    
    if use_cache and not streaming:
        return CachedLLM(llm)
    
    return llm


def list_supported_providers() -> Dict[str, Dict[str, Any]]:
    """列出所有支持的模型提供商"""
    return SUPPORTED_PROVIDERS


def get_provider_info(provider: str) -> Optional[Dict[str, Any]]:
    """获取特定提供商的信息"""
    return SUPPORTED_PROVIDERS.get(provider)
