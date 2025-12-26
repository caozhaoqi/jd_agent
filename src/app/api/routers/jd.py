from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlmodel import Session
from loguru import logger
import json
import asyncio

from app.api.deps import get_current_user, get_llm, get_session
from app.schemas.interview import JDRequest
from app.services.interview_service import generate_interview_guide
from app.services.memory_service import update_long_term_memory
from app.core.models import User, ChatSession, ChatMessage
from app.core.stream_manager import clear_queue
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing import List, Optional

router = APIRouter()


class CrawlJobsRequest(BaseModel):
    keywords: str = Field(..., description="搜索关键词，如职位名称、技术栈等")
    max_results: int = Field(10, description="最大返回结果数")


@router.post("/generate-guide")
async def create_guide(
    request: JDRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """
    流式生成面试指南 (适配 DeepSeek 思考 UI)
    """
    thread_id = f"user_{user.id}_job_{hash(request.jd_text)}"

    async def generate_and_stream():
        from app.core.stream_manager import get_stream_queue
        
        # 立即发送初始进度消息，让前端知道处理已开始
        initial_thought = json.dumps({"type": "thought", "content": "🚀 开始分析职位描述...", "detail": "正在初始化处理流程"}, ensure_ascii=False)
        yield f"data: {initial_thought}\n\n"

        message_queue = asyncio.Queue()

        async def process_stream_queue():
            queue = None
            while True:
                queue = get_stream_queue(thread_id)
                if queue:
                    break
                await asyncio.sleep(0.1)

            try:
                while True:
                    msg = await queue.get()
                    if msg is None:
                        break
                    payload = json.dumps(msg, ensure_ascii=False)
                    await message_queue.put(f"data: {payload}\n\n")
            except Exception as e:
                logger.error(f"Queue Error: {e}, thread_id: {thread_id}")
                error_payload = json.dumps({"type": "error", "content": str(e)})
                await message_queue.put(f"data: {error_payload}\n\n")

        async def generate_report():
            try:
                report = await generate_interview_guide(request, db, user.id)
                
                title = f"{report.meta.company_name} 面试准备" if report.meta.company_name else "岗位 JD 分析"
                new_session = ChatSession(title=title, user_id=user.id)
                db.add(new_session)
                db.commit()
                db.refresh(new_session)

                db.add(ChatMessage(session_id=new_session.id, role="user", content=request.jd_text))
                db.add(ChatMessage(session_id=new_session.id, role="assistant", content=report.model_dump_json()))
                db.commit()

                report.session_id = new_session.id
                
                background_tasks.add_task(update_long_term_memory, db, user.id, f"User上传了JD: {request.jd_text}")
                
                from app.core.stream_manager import send_done
                await send_done(thread_id)
                return report
            except Exception as e:
                logger.error(f"Generate Report Error: {e}")
                error_payload = json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)
                await message_queue.put(f"data: {error_payload}\n\n")
                # 确保发送结束信号，让 process_stream_queue 能够退出
                from app.core.stream_manager import get_stream_queue
                queue = get_stream_queue(thread_id)
                if queue:
                    await queue.put(None)
                return None

        report_task = asyncio.create_task(generate_report())
        queue_task = asyncio.create_task(process_stream_queue())

        # 等待两个任务完成，同时处理消息队列
        queue_done = False
        while not report_task.done() or not queue_done:
            try:
                # 如果队列任务已完成，不再等待新消息
                if queue_task.done():
                    queue_done = True
                    # 尝试获取剩余消息，但不阻塞太久
                    try:
                        msg = await asyncio.wait_for(message_queue.get(), timeout=0.1)
                        if msg:
                            yield msg
                    except asyncio.TimeoutError:
                        pass
                else:
                    # 队列任务还在运行，正常读取消息
                    msg = await asyncio.wait_for(message_queue.get(), timeout=0.1)
                    if msg:
                        yield msg
            except asyncio.TimeoutError:
                # 检查任务是否出错
                if report_task.done() and report_task.exception():
                    error = report_task.exception()
                    logger.error(f"Report generation failed: {error}")
                    error_payload = json.dumps({"type": "error", "content": str(error)}, ensure_ascii=False)
                    yield f"data: {error_payload}\n\n"
                    yield "data: [DONE]\n\n"
                    clear_queue(thread_id)
                    return
                # 如果队列任务已完成，检查报告任务状态
                if queue_task.done() and not report_task.done():
                    # 等待报告任务完成
                    await asyncio.sleep(0.1)
                    continue
        
        # 确保所有队列消息都已发送（处理队列任务完成后剩余的消息）
        if not queue_done:
            try:
                while True:
                    msg = await asyncio.wait_for(message_queue.get(), timeout=0.1)
                    if msg:
                        yield msg
            except asyncio.TimeoutError:
                pass  # 队列已空
        
        # 获取报告结果
        try:
            report = await report_task
        except Exception as e:
            logger.error(f"Failed to get report: {e}")
            error_payload = json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)
            yield f"data: {error_payload}\n\n"
            yield "data: [DONE]\n\n"
            clear_queue(thread_id)
            return
        
        if report:
            def format_report_to_markdown(report):
                meta = report.meta
                tech_questions = report.tech_questions
                hr_questions = report.hr_questions
                company_analysis = report.company_analysis
                markdown = f"## 📊 {meta.company_name or '岗位'} 分析\n\n**技术栈**: `{', '.join(meta.tech_stack)}`\n\n"
                if company_analysis:
                    markdown += f"> 🏢 **公司**: {company_analysis}\n\n"
                markdown += "### 🛠️ 推荐技术题\n"
                for i, q in enumerate(tech_questions, 1):
                    markdown += f"**Q{i}: {q.question}**\n> {q.reference_answer}\n\n"
                if hr_questions:
                    markdown += "### 🧑💼 推荐HR题\n"
                    for i, q in enumerate(hr_questions, 1):
                        markdown += f"**Q{i}: {q.question}**\n> {q.reference_answer}\n\n"
                return markdown

            markdown_content = format_report_to_markdown(report)
            for char in markdown_content:
                await asyncio.sleep(0.015)
                token_payload = json.dumps({"type": "token", "content": char}, ensure_ascii=False)
                yield f"data: {token_payload}\n\n"

            meta_payload = json.dumps({"type": "data", "key": "report_meta", "value": report.model_dump()}, ensure_ascii=False)
            yield f"data: {meta_payload}\n\n"
            
            result_payload = json.dumps({"type": "result", "content": report.model_dump()}, ensure_ascii=False)
            yield f"data: {result_payload}\n\n"
        else:
            # 如果 report 为 None，说明生成失败，但错误应该已经在上面处理了
            logger.warning("Report is None, but no error was caught")

        # 确保发送结束信号
        yield "data: [DONE]\n\n"
        clear_queue(thread_id)

    return StreamingResponse(
        generate_and_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.post("/stream/system-design")
async def stream_system_design(
    tech_stack: str,
    topic: str,
    user: User = Depends(get_current_user),
    llm: ChatOpenAI = Depends(get_llm),  # 使用依赖注入获取 LLM
):
    """
    流式生成系统设计题答案 (打字机效果)
    """
    prompt = ChatPromptTemplate.from_template(
        "请基于 {tech_stack} 技术栈，详细设计一个 {topic} 系统。请包含架构图描述、数据库选型和核心难点。"
    )
    chain = prompt | llm | StrOutputParser()

    async def generate_stream():
        async for chunk in chain.astream({"tech_stack": tech_stack, "topic": topic}):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.post("/crawl-jobs")
async def crawl_related_jobs(
    request: CrawlJobsRequest,
    user: User = Depends(get_current_user),
):
    """
    爬取相关岗位数据
    根据关键词搜索相关岗位信息
    """
    import os
    from langchain_community.tools.tavily_search import TavilySearchResults
    
    try:
        # 检查是否有 Tavily API Key
        tavily_key = os.environ.get("TAVILY_API_KEY")
        if not tavily_key:
            return {
                "status": "error",
                "message": "未配置搜索服务，无法爬取岗位数据",
                "data": []
            }
        
        # 初始化搜索工具
        search_tool = TavilySearchResults(max_results=request.max_results, timeout=10)
        
        # 构建搜索查询
        search_query = f"{request.keywords} 招聘 岗位 JD 职位描述"
        
        logger.info(f"🔍 开始搜索相关岗位: {search_query}")
        
        # 执行搜索
        try:
            results = await search_tool.ainvoke(search_query)
        except:
            results = search_tool.invoke(search_query)
        
        # 处理搜索结果
        jobs = []
        if isinstance(results, list):
            for item in results:
                if isinstance(item, dict):
                    jobs.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", "")[:500],  # 限制内容长度
                        "score": item.get("score", 0)
                    })
        
        logger.info(f"✅ 成功爬取 {len(jobs)} 个相关岗位")
        
        return {
            "status": "success",
            "message": f"成功爬取 {len(jobs)} 个相关岗位",
            "data": jobs
        }
        
    except Exception as e:
        logger.error(f"❌ 爬取岗位数据失败: {e}")
        return {
            "status": "error",
            "message": f"爬取失败: {str(e)}",
            "data": []
        }
