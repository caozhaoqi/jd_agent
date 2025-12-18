import json
import asyncio
from fastapi import APIRouter, Depends
from app.core.error_handler import raise_bad_request, raise_internal_error, raise_not_found
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from loguru import logger

from app.api.deps import get_current_user, get_session
from app.core.models import User, ChatSession, ChatMessage, ChatRequest
from app.core.llm_factory import get_llm
from app.core.stream_manager import init_stream_queue
from app.core.sse_manager import sse_manager
from app.chains.rag_chain import ask_knowledge_base

router = APIRouter()


@router.get("/history/sessions")
def get_sessions(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return session.exec(select(ChatSession).where(ChatSession.user_id == user.id).order_by(ChatSession.id.desc())).all()


@router.get("/history/messages/{session_id}")
def get_messages(session_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    chat = session.get(ChatSession, session_id)
    if not chat or chat.user_id != user.id:
        raise_not_found(message="会话不存在")
    return chat.messages


@router.post("/stream")
async def stream_chat(
        req: ChatRequest,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_session)
):
    """
    通用多轮对话流式接口 (适配 DeepSeek 思考 UI)
    """
    # 初始化队列 (虽然简单对话主要靠流，但保持习惯初始化 ContextVar)
    init_stream_queue()

    # 1. 验证会话
    session = db.get(ChatSession, req.session_id)
    if not session:
        raise_not_found(message="会话不存在")

    # 2. 保存用户的新回复到数据库
    user_msg = ChatMessage(session_id=req.session_id, role="user", content=req.content)
    db.add(user_msg)
    db.commit()

    # 3. 准备历史上下文
    recent_msgs = session.messages[-10:]

    # 4. 构建 Prompt (人设切换逻辑保持不变)
    last_user_msg = req.content
    system_prompt = "你是一个专业的 AI 求职助手，负责解答用户的技术问题。"

    if "模拟面试" in last_user_msg or "开始面试" in last_user_msg:
        system_prompt = """
            你现在是【面试官模式】。
            请基于该会话的上下文（JD 和 简历），向候选人提出一个具体的面试问题。
            要求：
            1. 每次只问一个问题，不要堆砌。
            2. 问题要犀利、具体，考察技术深度。
            3. 等待用户回答后，再进行追问或点评。
            """
    elif "面试" in session.title:
        system_prompt = "你是一名严厉但专业的面试官。请根据求职者的回答进行追问，考察其技术深度。"

    # LangChain 消息构建
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    lc_messages = [SystemMessage(content=system_prompt)]

    for m in recent_msgs:
        if m.role == "user":
            lc_messages.append(HumanMessage(content=m.content))
        else:
            lc_messages.append(AIMessage(content=m.content))

    # 5. 调用 LLM
    llm = get_llm(temperature=0.7, streaming=True)
    chain = llm | StrOutputParser()

    # 6. 流式生成 (升级版：支持 JSON 事件流)
    async def generate_and_stream():
        # 创建SSE连接
        client_id, send_queue = await sse_manager.add_connection()
        
        try:
            # --- 知识库查询判断 --- 
            knowledge_context = ""
            has_knowledge = False
            
            # 判断是否需要查询知识库
            last_user_question = req.content.strip().lower()
            # 简单的判断逻辑：如果问题涉及技术面试、编程、公司、岗位等关键词，或者问题很具体
            should_query_knowledge = any(keyword in last_user_question for keyword in 
                                         ["什么是", "如何", "怎么", "为什么", "技术", "编程", "面试", 
                                          "岗位", "公司", "职责", "要求", "技能", "学习", "准备"])
            
            if should_query_knowledge:
                # --- A. 发送思考过程 (Thought) ---
                thought_payload = json.dumps({
                    "type": "thought",
                    "content": "正在分析问题并查询知识库..."
                }, ensure_ascii=False)
                
                # 发送到SSE连接管理器和直接yield
                await send_queue.put(f"data: {thought_payload}\n\n")
                yield f"data: {thought_payload}\n\n"
                
                # 查询知识库
                try:
                    rag_result = await ask_knowledge_base(last_user_question)
                    if rag_result and rag_result["sources"]:
                        has_knowledge = True
                        knowledge_context = rag_result["answer"]
                        sources = rag_result["sources"]
                        
                        # 发送知识库检索完成的思考
                        thought_payload = json.dumps({
                            "type": "thought",
                            "content": "知识库检索完成，正在融合上下文生成回答..."
                        }, ensure_ascii=False)
                        await send_queue.put(f"data: {thought_payload}\n\n")
                        yield f"data: {thought_payload}\n\n"
                    else:
                        thought_payload = json.dumps({
                            "type": "thought",
                            "content": "知识库中未找到相关信息，正在直接生成回答..."
                        }, ensure_ascii=False)
                        await send_queue.put(f"data: {thought_payload}\n\n")
                        yield f"data: {thought_payload}\n\n"
                except Exception as e:
                    logger.debug(f"知识库查询失败: {str(e)}")
                    thought_payload = json.dumps({
                        "type": "thought",
                        "content": "知识库查询失败，正在直接生成回答..."
                    }, ensure_ascii=False)
                    await send_queue.put(f"data: {thought_payload}\n\n")
                    yield f"data: {thought_payload}\n\n"
            else:
                # --- A. 发送思考过程 (Thought) ---
                thought_payload = json.dumps({
                    "type": "thought",
                    "content": "正在分析上下文与面试意图..."
                }, ensure_ascii=False)
                
                # 发送到SSE连接管理器和直接yield
                await send_queue.put(f"data: {thought_payload}\n\n")
                yield f"data: {thought_payload}\n\n"

            # 稍微停顿一下让用户看到思考动画 (可选)
            await asyncio.sleep(0.5)

            # --- B. 发送内容流 (Token) ---
            full_response = ""
            try:
                # 如果有知识库上下文，重新构建系统提示和消息
                if has_knowledge and knowledge_context:
                    # 更新系统提示，包含知识库信息
                    enhanced_system_prompt = f"{system_prompt}\n\n【知识库参考信息】：\n{knowledge_context}"
                    
                    # 重新构建消息列表
                    enhanced_lc_messages = [SystemMessage(content=enhanced_system_prompt)]
                    for m in recent_msgs:
                        if m.role == "user":
                            enhanced_lc_messages.append(HumanMessage(content=m.content))
                        else:
                            enhanced_lc_messages.append(AIMessage(content=m.content))
                    
                    # 使用增强的消息列表生成回答
                    async for chunk in chain.astream(enhanced_lc_messages):
                        full_response += chunk
                        token_payload = json.dumps({
                            "type": "token",
                            "content": chunk
                        }, ensure_ascii=False)
                        await send_queue.put(f"data: {token_payload}\n\n")
                        yield f"data: {token_payload}\n\n"
                else:
                    # 使用原始消息列表生成回答
                    async for chunk in chain.astream(lc_messages):
                        full_response += chunk
                        token_payload = json.dumps({
                            "type": "token",
                            "content": chunk
                        }, ensure_ascii=False)
                        await send_queue.put(f"data: {token_payload}\n\n")
                        yield f"data: {token_payload}\n\n"
            except Exception as e:
                # 发送错误信息
                err_payload = json.dumps({"type": "token", "content": f"\n[Error]: {str(e)}"})
                await send_queue.put(f"data: {err_payload}\n\n")
                yield f"data: {err_payload}\n\n"

            # --- C. 存库逻辑 ---
            try:
                if full_response:
                    ai_msg = ChatMessage(session_id=req.session_id, role="assistant", content=full_response)
                    db.add(ai_msg)
                    db.commit()
            except Exception as e:
                print(f"Error saving AI response: {e}")

            # --- D. 结束 ---
            await send_queue.put("data: [DONE]\n\n")
            yield "data: [DONE]\n\n"
        finally:
            # 确保连接被移除
            await sse_manager.remove_connection(client_id)

    return StreamingResponse(
        generate_and_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
