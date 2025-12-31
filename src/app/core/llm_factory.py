from langchain_openai import ChatOpenAI
from app.core.settings import settings
from app.core.redis_client import redis_client
import hashlib
import json
import time
from typing import Any, List
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.runnables import Runnable
from loguru import logger
from app.core.monitoring import llm_calls_total, llm_call_duration_seconds


class CachedLLM(Runnable):
    """
    带有缓存功能的 LLM 包装器
    """

    def __init__(
        self, llm, cache_expire_seconds: int = settings.CACHE_EXPIRATION_LLM
    ):
        self.llm = llm
        self.cache_expire_seconds = cache_expire_seconds

    def _normalize_content(self, content: Any) -> Any:
        """递归地规范化消息内容，去除多余空格和换行"""
        if isinstance(content, str):
            return " ".join(content.split())
        if isinstance(content, list):
            return [self._normalize_content(item) for item in content]
        if isinstance(content, dict):
            return {k: self._normalize_content(v) for k, v in content.items()}
        return content

    def _generate_cache_key(self, messages: List[BaseMessage], **kwargs) -> str:
        """生成稳定且规范化的缓存键"""
        serializable_messages = []
        for msg in messages:
            try:
                # 规范化内容
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

        # 包含所有影响结果的参数
        cache_data = {
            "model_name": self.llm.model_name,
            "temperature": self.llm.temperature,
            "messages": serializable_messages,
            # 将 kwargs 中其他可能影响结果的参数也加入
            "other_kwargs": {k: v for k, v in kwargs.items() if k not in ['streaming']}
        }

        try:
            # 使用 sort_keys=True 确保 JSON 字符串的稳定性
            cache_str = json.dumps(cache_data, sort_keys=True)
            cache_key = f"llm_cache:{hashlib.md5(cache_str.encode()).hexdigest()}"
            logger.debug(f"生成的缓存键: {cache_key} for data: {cache_str[:200]}...")
            return cache_key
        except Exception as e:
            logger.error(f"生成缓存键失败: {e}")
            # 降级策略
            return f"llm_cache:fallback_{hash(str(messages))}"

    async def ainvoke(self, input_data: Any, config: Any = None, **kwargs) -> Any:
        """异步调用 LLM，先检查缓存（符合 LangChain Runnable 接口）"""
        # 处理 LangChain 链式操作中的输入格式
        # input_data 可能是消息列表、字符串或其他格式
        # 在链式操作中，prompt 的输出通常是消息列表
        if isinstance(input_data, list) and len(input_data) > 0 and isinstance(input_data[0], BaseMessage):
            # 如果输入是消息列表
            messages = input_data
        elif isinstance(input_data, dict) and "messages" in input_data:
            # 如果输入是字典且包含 messages 键
            messages = input_data["messages"]
        else:
            # 其他情况，直接传递给底层 LLM（让它处理格式转换）
            return await self.llm.ainvoke(input_data, config=config, **kwargs)
        
        model_name = self.llm.model_name
        
        if kwargs.get("streaming", False) or self.llm.streaming:
            logger.debug("流式请求，跳过缓存")
            return await self._measure_and_call_llm(self.llm.ainvoke, messages, model_name, config=config, **kwargs)

        cache_key = self._generate_cache_key(messages, **kwargs)
        cached_result = redis_client.get(cache_key)

        if cached_result:
            logger.info(f"缓存命中: {cache_key}")
            llm_calls_total.labels(model=model_name, status="cache_hit").inc()
            # Pydantic v2 中，直接使用 model_validate_json
            return AIMessage.model_validate_json(cached_result)

        logger.info(f"缓存未命中: {cache_key}")
        result = await self._measure_and_call_llm(self.llm.ainvoke, messages, model_name, config=config, **kwargs)

        try:
            # Pydantic v2 中，使用 model_dump_json
            redis_client.set(cache_key, result.model_dump_json(), self.cache_expire_seconds)
            logger.info(f"结果已缓存: {cache_key}")
        except Exception as e:
            logger.error(f"缓存结果失败: {e}")

        return result

    async def _measure_and_call_llm(self, method, messages, model_name, config=None, **kwargs):
        """测量并调用LLM方法"""
        start_time = time.time()
        try:
            # 如果方法支持 config 参数，传递它
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
        """同步调用（LangChain Runnable 接口要求）"""
        # 对于同步调用，我们直接使用底层 LLM，因为缓存主要是异步的
        return self.llm.invoke(input_data, config=config, **kwargs)
    
    async def astream(self, input_data: Any, config: Any = None, **kwargs):
        """异步流式调用"""
        async for chunk in self.llm.astream(input_data, config=config, **kwargs):
            yield chunk
    
    def stream(self, input_data: Any, config: Any = None, **kwargs):
        """同步流式调用"""
        for chunk in self.llm.stream(input_data, config=config, **kwargs):
            yield chunk
    
    def __getattr__(self, name: str):
        """代理其他方法调用"""
        return getattr(self.llm, name)


def get_llm(
    temperature=0.5, max_tokens=1000, streaming: bool = False, use_cache: bool = True
):
    """
    获取 LLM 实例，支持缓存
    """
    llm = ChatOpenAI(
        model_name=settings.MODEL_NAME,
        openai_api_key=settings.OPENAI_API_KEY,
        openai_api_base=settings.OPENAI_API_BASE,
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=streaming,
    )

    if use_cache and not streaming:
        return CachedLLM(llm)

    return llm
