from langchain_openai import ChatOpenAI
from app.core.config import settings
from app.core.redis_client import redis_client
import hashlib
import json
from typing import Any, Dict, List, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, FunctionMessage
from loguru import logger

class CachedLLM:
    """
    带有缓存功能的 LLM 包装器
    """
    
    def __init__(self, llm, cache_expire_seconds: int = 3600):
        self.llm = llm
        self.cache_expire_seconds = cache_expire_seconds
    
    def _generate_cache_key(self, messages: Any, **kwargs) -> str:
        """
        生成缓存键
        """
        # 辅助函数：递归处理消息内容，确保完全可序列化
        def process_message_content(content):
            # 处理 None 值
            if content is None:
                return None
            
            # 处理基本数据类型
            if isinstance(content, (str, int, float, bool)):
                return content
            
            # 处理字典类型，确保键是字符串
            if isinstance(content, dict):
                processed_dict = {}
                for k, v in content.items():
                    # 确保键是字符串
                    str_key = str(k)
                    processed_dict[str_key] = process_message_content(v)
                return processed_dict
            
            # 处理列表类型，递归处理每个元素
            if isinstance(content, list):
                return [process_message_content(item) for item in content]
            
            # 处理元组类型，转换为列表并递归处理
            if isinstance(content, tuple):
                return [process_message_content(item) for item in content]
            
            # 显式处理 LangChain 的 BaseMessage 类型
            from langchain_core.messages import BaseMessage
            if isinstance(content, BaseMessage):
                # 直接构造可序列化的字典
                return {
                    "type": content.type,
                    "content": process_message_content(content.content),
                    "additional_kwargs": process_message_content(content.additional_kwargs),
                    "response_metadata": process_message_content(content.response_metadata)
                }
            
            # 处理带有 to_json 方法的对象（如 LangChain 的其他对象）
            if hasattr(content, 'to_json'):
                try:
                    json_data = content.to_json()
                    return process_message_content(json_data)
                except Exception as e:
                    logger.debug(f"⚠️ [LLM Cache] to_json() failed: {e}, falling back to direct dict")
            
            # 处理带有 dict 方法的对象（如 Pydantic 模型）
            if hasattr(content, 'dict'):
                try:
                    dict_data = content.dict()
                    return process_message_content(dict_data)
                except Exception as e:
                    logger.debug(f"⚠️ [LLM Cache] dict() failed: {e}, falling back to __dict__")
            
            # 处理带有 __dict__ 属性的普通对象
            if hasattr(content, '__dict__'):
                try:
                    # 获取对象的 __dict__ 属性，过滤掉私有属性
                    obj_dict = {k: v for k, v in content.__dict__.items() if not k.startswith('_')}
                    return process_message_content(obj_dict)
                except Exception as e:
                    logger.debug(f"⚠️ [LLM Cache] __dict__ failed: {e}, falling back to string")
            
            # 最后尝试转换为字符串
            return str(content)
        
        # 将消息转换为可序列化的格式
        serialized_messages = []
        
        for msg in messages:
            try:
                logger.debug(f"📝 [LLM Cache] Processing message type: {type(msg).__name__}")
                
                # 显式检查是否为HumanMessage类型
                from langchain_core.messages import HumanMessage, BaseMessage
                if isinstance(msg, (BaseMessage, HumanMessage)):
                    # 优先使用 to_json 方法（LangChain v0.1+ 推荐使用）
                    try:
                        if hasattr(msg, 'to_json'):
                            msg_json = msg.to_json()
                            serialized_messages.append(process_message_content(msg_json))
                            continue
                    except Exception as e:
                        logger.debug(f"⚠️ [LLM Cache] to_json() failed: {e}, falling back to type+content")
                
                # 处理元组类型（高优先级，避免后面检查属性时出错）
                elif isinstance(msg, tuple):
                    logger.debug(f"📝 [LLM Cache] Processing tuple message: {msg}")
                    serialized_messages.append(process_message_content(msg))
                
                # 处理列表类型
                elif isinstance(msg, list):
                    logger.debug(f"📝 [LLM Cache] Processing list message: {msg}")
                    serialized_messages.append(process_message_content(msg))
                
                # 处理字典类型
                elif isinstance(msg, dict):
                    logger.debug(f"📝 [LLM Cache] Processing dict message: {msg}")
                    serialized_messages.append(process_message_content(msg))
                
                # 检查是否有 type 和 content 属性
                elif hasattr(msg, 'type') and hasattr(msg, 'content'):
                    # 标准 BaseMessage 对象
                    serialized_messages.append({
                        "type": msg.type,
                        "content": process_message_content(msg.content)
                    })
                
                elif hasattr(msg, 'dict'):
                    # 尝试使用 dict 方法
                    try:
                        msg_dict = msg.dict()
                        serialized_messages.append({
                            "type": msg_dict.get('type', 'unknown'),
                            "content": process_message_content(msg_dict.get('content', msg_dict))
                        })
                        continue
                    except Exception as e:
                        logger.debug(f"⚠️ [LLM Cache] dict() failed: {e}, falling back to string")
                
                else:
                    # 尝试转换为字符串
                    serialized_messages.append({
                        "type": "unknown",
                        "content": str(msg)
                    })
            except Exception as e:
                logger.error(f"❌ [LLM Cache] Failed to serialize message: {e}, msg type: {type(msg).__name__}")
                logger.error(f"❌ [LLM Cache] Message details: {msg}")
                # 如果序列化失败，使用字符串表示
                serialized_messages.append({
                    "type": "error",
                    "content": str(msg)
                })
        
        # 将参数和消息组合
        cache_data = {
            "model_name": kwargs.get("model_name", settings.MODEL_NAME),
            "temperature": kwargs.get("temperature", 0.7),
            "messages": serialized_messages
        }
        
        # 生成哈希值作为缓存键
        try:
            logger.debug(f"🔑 [LLM Cache] Generating cache key with data type: {type(cache_data).__name__}")
            cache_str = json.dumps(cache_data, sort_keys=True)
            cache_key = hashlib.md5(cache_str.encode()).hexdigest()
            logger.debug(f"✅ [LLM Cache] Successfully generated cache key: {cache_key}")
            return f"llm_cache:{cache_key}"
        except Exception as e:
            logger.error(f"❌ [LLM Cache] Failed to generate cache key: {e}")
            logger.error(f"❌ [LLM Cache] Failed cache_data: {cache_data}")
            # 如果生成缓存键失败，使用时间戳作为备选
            import time
            fallback_key = f"llm_cache:fallback_{int(time.time())}"
            logger.debug(f"🔄 [LLM Cache] Using fallback cache key: {fallback_key}")
            return fallback_key
    
    def __call__(self, messages: List[BaseMessage], **kwargs) -> Any:
        """
        调用 LLM，先检查缓存
        """
        # 只有非流式调用才使用缓存
        if kwargs.get("streaming", False) or hasattr(self.llm, "streaming") and self.llm.streaming:
            logger.debug("🚿 [LLM Cache] Skipping cache for streaming request")
            return self.llm(messages, **kwargs)
        
        # 生成缓存键
        cache_key = self._generate_cache_key(messages, **kwargs)
        
        # 检查缓存
        cached_result = redis_client.get(cache_key)
        if cached_result:
            logger.info(f"💾 [LLM Cache] Hit cache for key: {cache_key}")
            try:
                # 将缓存结果转换为 LangChain 预期的格式
                from langchain_core.outputs import ChatGeneration, ChatResult
                from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, FunctionMessage
                
                # 处理元组类型的缓存结果
                if isinstance(cached_result, (tuple, list)):
                    logger.debug(f"📝 [LLM Cache] Processing tuple/list cached result: {cached_result}")
                    # 如果是元组或列表，尝试使用第一个元素
                    if len(cached_result) > 0 and isinstance(cached_result[0], dict) and "message" in cached_result[0]:
                        cached_result = cached_result[0]
                
                # 确保 message 数据可用且格式正确
                if isinstance(cached_result, dict) and "message" in cached_result:
                    message_dict = cached_result["message"]
                    
                    # 处理 message_dict 为元组类型的情况
                    if isinstance(message_dict, (tuple, list)):
                        logger.debug(f"📝 [LLM Cache] Processing tuple/list message_dict: {message_dict}")
                        # 如果是元组或列表，尝试使用第一个元素
                        if len(message_dict) > 0 and isinstance(message_dict[0], dict) and "type" in message_dict[0] and "content" in message_dict[0]:
                            message_dict = message_dict[0]
                    
                    # 检查 message_dict 是否为有效的 BaseMessage 字典格式
                    if isinstance(message_dict, dict) and "type" in message_dict and "content" in message_dict:
                        # 根据type字段创建对应的消息实例
                        msg_type = message_dict.get("type")
                        content = message_dict.get("content")
                        additional_kwargs = message_dict.get("additional_kwargs", {})
                        response_metadata = message_dict.get("response_metadata", {})
                        
                        # 确保content是字符串类型
                        if content is None:
                            content = ""
                        elif not isinstance(content, str):
                            content = str(content)
                        
                        # 创建对应的消息实例
                        if msg_type == "human":
                            message = HumanMessage(content=content, additional_kwargs=additional_kwargs, response_metadata=response_metadata)
                        elif msg_type == "ai":
                            message = AIMessage(content=content, additional_kwargs=additional_kwargs, response_metadata=response_metadata)
                        elif msg_type == "system":
                            message = SystemMessage(content=content, additional_kwargs=additional_kwargs, response_metadata=response_metadata)
                        elif msg_type == "function":
                            message = FunctionMessage(content=content, additional_kwargs=additional_kwargs, response_metadata=response_metadata)
                        else:
                            # 默认使用AIMessage
                            message = AIMessage(content=content, additional_kwargs=additional_kwargs, response_metadata=response_metadata)
                        
                        # 总是返回字符串内容，与缓存未命中时的行为保持一致
                        return message.content
            except Exception as e:
                logger.error(f"❌ [LLM Cache] Failed to process cached result: {e}")
                # 如果处理缓存结果失败，尝试直接提取内容并转换为字符串
                try:
                    if isinstance(cached_result, dict):
                        # 尝试从缓存结果中提取内容
                        if "message" in cached_result:
                            message_data = cached_result["message"]
                            if isinstance(message_data, dict) and "content" in message_data:
                                content = message_data["content"]
                                if content is None:
                                    content = ""
                                elif not isinstance(content, str):
                                    content = str(content)
                                logger.debug(f"📝 [LLM Cache] Directly extracted content from cache: {content[:100]}...")
                                return content
                    # 如果无法提取内容，将整个缓存结果转换为字符串
                    logger.debug(f"📝 [LLM Cache] Converting entire cached result to string")
                    return str(cached_result)
                except Exception as inner_e:
                    logger.error(f"❌ [LLM Cache] Failed to extract or convert cached result: {inner_e}")
                    # 如果处理失败，跳过缓存，直接调用 LLM
        
        # 缓存未命中或处理失败，调用 LLM
        logger.info(f"🔄 [LLM Cache] Miss cache for key: {cache_key}")
        # 记录 messages 参数的类型和内容，特别是当它是元组类型时
        try:
            logger.debug(f"📝 [LLM Call] messages type: {type(messages).__name__}, messages: {messages}")
            
            # 处理元组类型的 messages
            if isinstance(messages, tuple):
                logger.debug(f"⚠️ [LLM Call] Found tuple messages: {messages}")
                # 将元组转换为列表
                messages = list(messages)
            
            # 处理列表中的元组元素，确保它们是 BaseMessage 类型
            from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, FunctionMessage
            processed_messages = []
            for msg in messages:
                if isinstance(msg, tuple):
                    logger.debug(f"⚠️ [LLM Call] Found tuple element in messages: {msg}")
                    # 如果是元组，尝试将其转换为 BaseMessage
                    if len(msg) > 0 and isinstance(msg[0], dict) and "type" in msg[0]:
                            # 根据type字段创建对应的消息实例
                        try:
                            msg_dict = msg[0]
                            msg_type = msg_dict.get("type")
                            content = msg_dict.get("content")
                            additional_kwargs = msg_dict.get("additional_kwargs", {})
                            response_metadata = msg_dict.get("response_metadata", {})
                            
                            if msg_type == "human":
                                base_msg = HumanMessage(content=content, additional_kwargs=additional_kwargs, response_metadata=response_metadata)
                            elif msg_type == "ai":
                                base_msg = AIMessage(content=content, additional_kwargs=additional_kwargs, response_metadata=response_metadata)
                            elif msg_type == "system":
                                base_msg = SystemMessage(content=content, additional_kwargs=additional_kwargs, response_metadata=response_metadata)
                            elif msg_type == "function":
                                base_msg = FunctionMessage(content=content, additional_kwargs=additional_kwargs, response_metadata=response_metadata)
                            else:
                                base_msg = HumanMessage(content=str(msg_dict))
                            
                            processed_messages.append(base_msg)
                            continue
                        except Exception as e:
                            logger.debug(f"❌ [LLM Call] Failed to convert tuple element to BaseMessage: {e}")
                    # 如果转换失败，将元组转换为字符串
                    processed_messages.append(HumanMessage(content=str(msg)))
                elif not isinstance(msg, BaseMessage):
                    # 如果不是 BaseMessage 类型，尝试将其转换为 BaseMessage
                    logger.debug(f"⚠️ [LLM Call] Found non-BaseMessage element: {msg}, type: {type(msg).__name__}")
                    try:
                        if isinstance(msg, dict) and "type" in msg:
                            # 根据type字段创建对应的消息实例
                            msg_type = msg.get("type")
                            content = msg.get("content")
                            additional_kwargs = msg.get("additional_kwargs", {})
                            response_metadata = msg.get("response_metadata", {})
                            
                            if msg_type == "human":
                                base_msg = HumanMessage(content=content, additional_kwargs=additional_kwargs, response_metadata=response_metadata)
                            elif msg_type == "ai":
                                base_msg = AIMessage(content=content, additional_kwargs=additional_kwargs, response_metadata=response_metadata)
                            elif msg_type == "system":
                                base_msg = SystemMessage(content=content, additional_kwargs=additional_kwargs, response_metadata=response_metadata)
                            elif msg_type == "function":
                                base_msg = FunctionMessage(content=content, additional_kwargs=additional_kwargs, response_metadata=response_metadata)
                            else:
                                base_msg = HumanMessage(content=str(msg))
                            
                            processed_messages.append(base_msg)
                        else:
                            # 否则，将其转换为 HumanMessage
                            processed_messages.append(HumanMessage(content=str(msg)))
                    except Exception as e:
                        logger.debug(f"❌ [LLM Call] Failed to convert element to BaseMessage: {e}")
                        # 如果转换失败，将其转换为 HumanMessage
                        processed_messages.append(HumanMessage(content=str(msg)))
                else:
                    # 如果已经是 BaseMessage 类型，直接添加
                    processed_messages.append(msg)
            
            logger.debug(f"📝 [LLM Call] Processed messages: {processed_messages}")
            result = self.llm(processed_messages, **kwargs)
        except Exception as e:
            logger.error(f"❌ [LLM Call] Failed to call LLM: {e}")
            logger.error(f"❌ [LLM Call] messages type: {type(messages).__name__}, messages: {messages}")
            raise
        
        # 处理结果类型，确保返回正确的格式
        try:
            from langchain_core.outputs import ChatResult, ChatGeneration
            from langchain_core.messages import BaseMessage
            
            # 检查结果类型
            if isinstance(result, ChatResult):
                # 如果是 ChatResult 类型，提取文本内容
                llm_text = result.generations[0].message.content
                
                # 将结果缓存
                cache_data = {
                    "message": result.generations[0].message.dict(),
                    "generation_info": result.generations[0].generation_info if isinstance(result.generations[0].generation_info, (dict, list, str, int, float, bool, type(None))) else str(result.generations[0].generation_info),
                    "llm_output": result.llm_output if isinstance(result.llm_output, (dict, list, str, int, float, bool, type(None))) else str(result.llm_output)
                }
                redis_client.set(cache_key, cache_data, self.cache_expire_seconds)
                logger.info(f"💾 [LLM Cache] Saved result to cache for key: {cache_key}")
                
                return llm_text
            elif isinstance(result, BaseMessage):
                # 如果直接返回 BaseMessage 类型，提取文本内容
                llm_text = result.content
                
                # 将结果缓存
                cache_data = {
                    "message": result.dict(),
                    "generation_info": None,
                    "llm_output": None
                }
                redis_client.set(cache_key, cache_data, self.cache_expire_seconds)
                logger.info(f"💾 [LLM Cache] Saved result to cache for key: {cache_key}")
                
                return llm_text
            elif isinstance(result, str):
                # 如果已经是字符串类型，直接返回
                # 将结果缓存
                cache_data = {
                    "message": {"type": "ai", "content": result},
                    "generation_info": None,
                    "llm_output": None
                }
                redis_client.set(cache_key, cache_data, self.cache_expire_seconds)
                logger.info(f"💾 [LLM Cache] Saved result to cache for key: {cache_key}")
                
                return result
            else:
                # 其他类型，尝试转换为字符串
                llm_text = str(result)
                
                # 将结果缓存
                cache_data = {
                    "message": {"type": "ai", "content": llm_text},
                    "generation_info": None,
                    "llm_output": None
                }
                redis_client.set(cache_key, cache_data, self.cache_expire_seconds)
                logger.info(f"💾 [LLM Cache] Saved result to cache for key: {cache_key}")
                
                return llm_text
        except Exception as e:
            logger.error(f"❌ [LLM Cache] Failed to process LLM result: {e}")
            # 如果处理失败，将结果转换为字符串返回
            try:
                from langchain_core.outputs import ChatResult
                from langchain_core.messages import BaseMessage
                
                if isinstance(result, ChatResult):
                    return result.generations[0].message.content
                elif isinstance(result, BaseMessage):
                    return result.content
                else:
                    return str(result)
            except Exception as inner_e:
                logger.error(f"❌ [LLM Cache] Failed to convert error result to string: {inner_e}")
                # 最后尝试直接转换为字符串
                return str(result)
    
    async def ainvoke(self, messages: List[BaseMessage], **kwargs) -> Any:
        """
        异步调用 LLM，先检查缓存
        """
        # 只有非流式调用才使用缓存
        if kwargs.get("streaming", False) or hasattr(self.llm, "streaming") and self.llm.streaming:
            logger.debug("🚿 [LLM Cache] Skipping cache for streaming request")
            return await self.llm.ainvoke(messages, **kwargs)
        
        # 生成缓存键
        cache_key = self._generate_cache_key(messages, **kwargs)
        
        # 检查缓存
        cached_result = redis_client.get(cache_key)
        if cached_result:
            logger.info(f"💾 [LLM Cache] Hit cache for key: {cache_key}")
            try:
                # 将缓存结果转换为 LangChain 预期的格式
                from langchain_core.outputs import ChatGeneration, ChatResult
                from langchain_core.messages import BaseMessage, AIMessage, SystemMessage, FunctionMessage, HumanMessage
                
                # 处理元组类型的缓存结果
                if isinstance(cached_result, (tuple, list)):
                    logger.debug(f"📝 [LLM Cache] Processing tuple/list cached result: {cached_result}")
                    # 如果是元组或列表，尝试使用第一个元素
                    if len(cached_result) > 0 and isinstance(cached_result[0], dict) and "message" in cached_result[0]:
                        cached_result = cached_result[0]
                
                # 确保 message 数据可用且格式正确
                if isinstance(cached_result, dict) and "message" in cached_result:
                    message_dict = cached_result["message"]
                    
                    # 处理 message_dict 为元组类型的情况
                    if isinstance(message_dict, (tuple, list)):
                        logger.debug(f"📝 [LLM Cache] Processing tuple/list message_dict: {message_dict}")
                        # 如果是元组或列表，尝试使用第一个元素
                        if len(message_dict) > 0 and isinstance(message_dict[0], dict) and "type" in message_dict[0] and "content" in message_dict[0]:
                            message_dict = message_dict[0]
                    
                    # 检查 message_dict 是否为有效的 BaseMessage 字典格式
                    if isinstance(message_dict, dict) and "type" in message_dict and "content" in message_dict:
                        # 根据type字段创建对应的消息实例
                        msg_type = message_dict.get("type")
                        content = message_dict.get("content")
                        additional_kwargs = message_dict.get("additional_kwargs", {})
                        response_metadata = message_dict.get("response_metadata", {})
                        
                        # 确保content是字符串类型
                        if content is None:
                            content = ""
                        elif not isinstance(content, str):
                            content = str(content)
                        
                        # 创建对应的消息实例
                        if msg_type == "human":
                            message = HumanMessage(content=content, additional_kwargs=additional_kwargs, response_metadata=response_metadata)
                        elif msg_type == "ai":
                            message = AIMessage(content=content, additional_kwargs=additional_kwargs, response_metadata=response_metadata)
                        elif msg_type == "system":
                            message = SystemMessage(content=content, additional_kwargs=additional_kwargs, response_metadata=response_metadata)
                        elif msg_type == "function":
                            message = FunctionMessage(content=content, additional_kwargs=additional_kwargs, response_metadata=response_metadata)
                        else:
                            # 默认使用AIMessage
                            message = AIMessage(content=content, additional_kwargs=additional_kwargs, response_metadata=response_metadata)
                        
                        # 总是返回字符串内容，与缓存未命中时的行为保持一致
                        return message.content
            except Exception as e:
                logger.error(f"❌ [LLM Cache] Failed to process cached result: {e}")
                # 如果处理缓存结果失败，尝试直接提取内容并转换为字符串
                try:
                    if isinstance(cached_result, dict):
                        # 尝试从缓存结果中提取内容
                        if "message" in cached_result:
                            message_data = cached_result["message"]
                            if isinstance(message_data, dict) and "content" in message_data:
                                content = message_data["content"]
                                if content is None:
                                    content = ""
                                elif not isinstance(content, str):
                                    content = str(content)
                                logger.debug(f"📝 [LLM Cache] Directly extracted content from cache: {content[:100]}...")
                                return content
                    # 如果无法提取内容，将整个缓存结果转换为字符串
                    logger.debug(f"📝 [LLM Cache] Converting entire cached result to string")
                    return str(cached_result)
                except Exception as inner_e:
                    logger.error(f"❌ [LLM Cache] Failed to extract or convert cached result: {inner_e}")
                    # 如果处理失败，跳过缓存，直接调用 LLM
        
        # 缓存未命中或处理失败，调用 LLM
        logger.info(f"🔄 [LLM Cache] Miss cache for key: {cache_key}")
        # 记录 messages 参数的类型和内容，特别是当它是元组类型时
        try:
            logger.debug(f"📝 [LLM Call] messages type: {type(messages).__name__}, messages: {messages}")
            
            # 处理元组类型的 messages
            if isinstance(messages, tuple):
                logger.debug(f"⚠️ [LLM Call] Found tuple messages: {messages}")
                # 将元组转换为列表
                messages = list(messages)
            
            # 处理列表中的元组元素，确保它们是 BaseMessage 类型
            from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, FunctionMessage
            processed_messages = []
            for msg in messages:
                if isinstance(msg, tuple):
                    logger.debug(f"⚠️ [LLM Call] Found tuple element in messages: {msg}")
                    # 如果是元组，尝试将其转换为 BaseMessage
                    if len(msg) > 0 and isinstance(msg[0], dict) and "type" in msg[0]:
                            # 根据type字段创建对应的消息实例
                        try:
                            msg_dict = msg[0]
                            msg_type = msg_dict.get("type")
                            content = msg_dict.get("content")
                            additional_kwargs = msg_dict.get("additional_kwargs", {})
                            response_metadata = msg_dict.get("response_metadata", {})
                            
                            if msg_type == "human":
                                base_msg = HumanMessage(content=content, additional_kwargs=additional_kwargs, response_metadata=response_metadata)
                            elif msg_type == "ai":
                                base_msg = AIMessage(content=content, additional_kwargs=additional_kwargs, response_metadata=response_metadata)
                            elif msg_type == "system":
                                base_msg = SystemMessage(content=content, additional_kwargs=additional_kwargs, response_metadata=response_metadata)
                            elif msg_type == "function":
                                base_msg = FunctionMessage(content=content, additional_kwargs=additional_kwargs, response_metadata=response_metadata)
                            else:
                                base_msg = HumanMessage(content=str(msg_dict))
                            
                            processed_messages.append(base_msg)
                            continue
                        except Exception as e:
                            logger.debug(f"❌ [LLM Call] Failed to convert tuple element to BaseMessage: {e}")
                    # 如果转换失败，将元组转换为字符串
                    processed_messages.append(HumanMessage(content=str(msg)))
                elif not isinstance(msg, BaseMessage):
                    # 如果不是 BaseMessage 类型，尝试将其转换为 BaseMessage
                    logger.debug(f"⚠️ [LLM Call] Found non-BaseMessage element: {msg}, type: {type(msg).__name__}")
                    try:
                        if isinstance(msg, dict) and "type" in msg:
                            # 根据type字段创建对应的消息实例
                            msg_type = msg.get("type")
                            content = msg.get("content")
                            additional_kwargs = msg.get("additional_kwargs", {})
                            response_metadata = msg.get("response_metadata", {})
                            
                            if msg_type == "human":
                                base_msg = HumanMessage(content=content, additional_kwargs=additional_kwargs, response_metadata=response_metadata)
                            elif msg_type == "ai":
                                base_msg = AIMessage(content=content, additional_kwargs=additional_kwargs, response_metadata=response_metadata)
                            elif msg_type == "system":
                                base_msg = SystemMessage(content=content, additional_kwargs=additional_kwargs, response_metadata=response_metadata)
                            elif msg_type == "function":
                                base_msg = FunctionMessage(content=content, additional_kwargs=additional_kwargs, response_metadata=response_metadata)
                            else:
                                base_msg = HumanMessage(content=str(msg))
                            
                            processed_messages.append(base_msg)
                        else:
                            # 否则，将其转换为 HumanMessage
                            processed_messages.append(HumanMessage(content=str(msg)))
                    except Exception as e:
                        logger.debug(f"❌ [LLM Call] Failed to convert element to BaseMessage: {e}")
                        # 如果转换失败，将其转换为 HumanMessage
                        processed_messages.append(HumanMessage(content=str(msg)))
                else:
                    # 如果已经是 BaseMessage 类型，直接添加
                    processed_messages.append(msg)
            
            logger.debug(f"📝 [LLM Call] Processed messages: {processed_messages}")
            result = await self.llm.ainvoke(processed_messages, **kwargs)
        except Exception as e:
            logger.error(f"❌ [LLM Call] Failed to call LLM: {e}")
            logger.error(f"❌ [LLM Call] messages type: {type(messages).__name__}, messages: {messages}")
            raise
        
        # 处理结果类型，确保返回正确的格式
        try:
            from langchain_core.outputs import ChatResult, ChatGeneration
            from langchain_core.messages import BaseMessage
            
            # 检查结果类型
            if isinstance(result, ChatResult):
                # 如果是 ChatResult 类型，提取文本内容
                llm_text = result.generations[0].message.content
                
                # 将结果缓存
                cache_data = {
                    "message": result.generations[0].message.dict(),
                    "generation_info": result.generations[0].generation_info if isinstance(result.generations[0].generation_info, (dict, list, str, int, float, bool, type(None))) else str(result.generations[0].generation_info),
                    "llm_output": result.llm_output if isinstance(result.llm_output, (dict, list, str, int, float, bool, type(None))) else str(result.llm_output)
                }
                redis_client.set(cache_key, cache_data, self.cache_expire_seconds)
                logger.info(f"💾 [LLM Cache] Saved result to cache for key: {cache_key}")
                
                return llm_text
            elif isinstance(result, BaseMessage):
                # 如果直接返回 BaseMessage 类型，提取文本内容
                llm_text = result.content
                
                # 将结果缓存
                cache_data = {
                    "message": result.dict(),
                    "generation_info": None,
                    "llm_output": None
                }
                redis_client.set(cache_key, cache_data, self.cache_expire_seconds)
                logger.info(f"💾 [LLM Cache] Saved result to cache for key: {cache_key}")
                
                return llm_text
            elif isinstance(result, str):
                # 如果已经是字符串类型，直接返回
                # 将结果缓存
                cache_data = {
                    "message": {"type": "ai", "content": result},
                    "generation_info": None,
                    "llm_output": None
                }
                redis_client.set(cache_key, cache_data, self.cache_expire_seconds)
                logger.info(f"💾 [LLM Cache] Saved result to cache for key: {cache_key}")
                
                return result
            else:
                # 其他类型，尝试转换为字符串
                llm_text = str(result)
                
                # 将结果缓存
                cache_data = {
                    "message": {"type": "ai", "content": llm_text},
                    "generation_info": None,
                    "llm_output": None
                }
                redis_client.set(cache_key, cache_data, self.cache_expire_seconds)
                logger.info(f"💾 [LLM Cache] Saved result to cache for key: {cache_key}")
                
                return llm_text
        except Exception as e:
            logger.error(f"❌ [LLM Cache] Failed to process LLM result: {e}")
            # 如果处理失败，将结果转换为字符串返回
            try:
                from langchain_core.outputs import ChatResult
                from langchain_core.messages import BaseMessage
                
                if isinstance(result, ChatResult):
                    return result.generations[0].message.content
                elif isinstance(result, BaseMessage):
                    return result.content
                else:
                    return str(result)
            except Exception as inner_e:
                logger.error(f"❌ [LLM Cache] Failed to convert error result to string: {inner_e}")
                # 最后尝试直接转换为字符串
                return str(result)
    
    # 代理其他方法调用
    def __getattr__(self, name: str):
        return getattr(self.llm, name)

def get_llm(temperature=0.7, streaming: bool = False, use_cache: bool = True):
    """
    获取 LLM 实例，支持缓存
    """
    llm = ChatOpenAI(
        model_name=settings.MODEL_NAME, # e.g., "gpt-4" or "deepseek-chat"
        openai_api_key=settings.OPENAI_API_KEY,
        openai_api_base=settings.OPENAI_API_BASE,
        temperature=temperature,
        streaming=streaming
    )
    
    # 如果启用缓存且不是流式调用，则返回缓存包装器
    if use_cache and not streaming:
        return CachedLLM(llm)
    
    return llm