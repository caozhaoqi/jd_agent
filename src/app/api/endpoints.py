from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 导入内部模块
from app.schemas.interview import JDRequest, InterviewReport
from app.services.interview_service import generate_interview_guide
from app.core.llm_factory import get_llm

# 1. 核心修复：实例化 APIRouter
router = APIRouter()


# --- 原有的普通接口 ---
@router.post("/generate-guide", response_model=InterviewReport)
async def create_guide(request: JDRequest):
    """
    接收 JD 文本，返回完整的面试准备指南 (JSON 格式)
    """
    # 调用业务逻辑层
    report = await generate_interview_guide(request)
    return report


# --- 新增的流式接口 ---
@router.post("/stream/system-design")
async def stream_system_design(tech_stack: str, topic: str):
    """
    流式生成系统设计题答案
    前端可以通过 SSE (Server-Sent Events) 接收，实现打字机效果

    请求示例: POST /api/v1/stream/system-design?tech_stack=Python&topic=秒杀系统
    """
    # 获取支持流式的 LLM 实例
    # 注意：这里我们直接传参给 ChatOpenAI，它支持 streaming=True
    llm = get_llm(temperature=0.7)

    prompt = ChatPromptTemplate.from_template(
        "请基于 {tech_stack} 技术栈，详细设计一个 {topic} 系统。请包含架构图描述、数据库选型和核心难点。"
    )

    # 构建链
    chain = prompt | llm | StrOutputParser()

    # 定义异步生成器函数
    async def generate_stream():
        # astream 是 LangChain 的流式异步方法
        async for chunk in chain.astream({"tech_stack": tech_stack, "topic": topic}):
            # SSE 格式要求: data: <content>\n\n
            # 替换换行符以防止 SSE 格式错误 (视前端解析方式而定，通常直接发即可)
            yield f"data: {chunk}\n\n"

        # 结束信号
        yield "data: [DONE]\n\n"

    # 返回流式响应
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream"
    )