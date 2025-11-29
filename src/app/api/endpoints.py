import jwt
import json
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlmodel import Session, select
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- 内部模块导入 ---
# 1. 数据库与鉴权
from app.core.db_auth import get_session, get_password_hash, verify_password, create_access_token, SECRET_KEY, ALGORITHM
from app.core.models import User, ChatSession, ChatMessage, UserProfile

# 2. Schema 数据模型
from app.schemas.interview import JDRequest, InterviewReport

# 3. 业务服务逻辑
from app.services.interview_service import generate_interview_guide
from app.services.memory_service import update_long_term_memory
from app.services.mock_service import run_mock_interview_stream

# 4. 核心工具与链
from app.core.llm_factory import get_llm
from app.utils.file_parser import parse_resume_file
from app.chains.resume_extractor import extract_resume_features

# ==========================================
# 初始化 Router 与 Security
# ==========================================
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")


# ==========================================
# 依赖函数 (Dependencies)
# ==========================================
async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    """
    解析 Token 获取当前登录用户
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token无效")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="凭证无效")

    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


# ==========================================
# 1. 认证接口 (Auth)
# ==========================================
class AuthRequest(BaseModel):
    username: str
    password: str


@router.post("/register")
def register(req: AuthRequest, session: Session = Depends(get_session)):
    if session.exec(select(User).where(User.username == req.username)).first():
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = User(username=req.username, hashed_password=get_password_hash(req.password))
    session.add(user)
    session.commit()
    return {"msg": "注册成功"}


@router.post("/login")
def login(req: AuthRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == req.username)).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="用户名或密码错误")

    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


# ==========================================
# 2. 简历上传接口 (Resume)
# ==========================================
@router.post("/upload-resume")
async def upload_resume(
        file: UploadFile = File(...),
        user: User = Depends(get_current_user),
        db: Session = Depends(get_session)
):
    """
    上传简历 -> 解析文本 -> LLM提取画像 -> 存入长期记忆
    """
    # 1. 解析文件 (支持 PDF/DOCX/TXT)
    resume_text = await parse_resume_file(file)

    # 2. 调用 LLM 提取关键信息
    facts = await extract_resume_features(resume_text)

    if not facts:
        return {"msg": "简历解析完成，但未提取到有效信息", "count": 0}

    # 3. 存入数据库 (UserProfile)
    count = 0
    for fact in facts:
        # 查重：避免重复写入完全一样的信息
        exists = db.exec(
            select(UserProfile)
            .where(UserProfile.user_id == user.id)
            .where(UserProfile.content == fact.content)
        ).first()

        if not exists:
            new_profile = UserProfile(
                user_id=user.id,
                category=f"resume_{fact.category}",  # 标记来源为简历
                content=fact.content
            )
            db.add(new_profile)
            count += 1

    db.commit()

    return {
        "msg": "简历解析成功！已更新个人画像。",
        "extracted_facts": [f.content for f in facts],
        "new_entries": count
    }


# ==========================================
# 3. 历史记录接口 (History)
# ==========================================
@router.get("/history/sessions")
def get_sessions(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """获取当前用户的所有会话列表 (倒序)"""
    statement = select(ChatSession).where(ChatSession.user_id == user.id).order_by(ChatSession.id.desc())
    return session.exec(statement).all()


@router.get("/history/messages/{session_id}")
def get_messages(session_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """获取指定会话的详细消息"""
    # 验证 session 是否属于该用户
    chat = session.get(ChatSession, session_id)
    if not chat or chat.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    return chat.messages


# ==========================================
# 4. 核心生成接口 (Core Logic)
# ==========================================
@router.post("/generate-guide", response_model=InterviewReport)
async def create_guide(
        request: JDRequest,
        background_tasks: BackgroundTasks,
        user: User = Depends(get_current_user),  # 必须登录
        db: Session = Depends(get_session),
):
    """
    接收 JD 文本，返回完整的面试准备指南，并自动保存到历史记录。
    """
    # A. 调用业务逻辑生成报告
    report = await generate_interview_guide(request, db, user.id)

    # B. --- 数据库存盘逻辑 ---
    try:
        # 1. 创建新的会话 (ChatSession)
        title = f"{report.meta.company_name} 面试准备" if report.meta.company_name else "岗位 JD 分析"

        new_session = ChatSession(
            title=title,
            user_id=user.id
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)

        # 2. 保存用户的提问
        user_msg = ChatMessage(
            session_id=new_session.id,
            role="user",
            content=request.jd_text
        )
        db.add(user_msg)

        # 3. 保存 AI 的回答
        ai_msg = ChatMessage(
            session_id=new_session.id,
            role="assistant",
            content=report.model_dump_json()
        )
        db.add(ai_msg)

        db.commit()
        print(f"✅ [DB] 会话已保存: ID={new_session.id}, Title={title}")

    except Exception as e:
        print(f"❌ [DB Error] 保存历史记录失败: {e}")
        # 不抛出异常，保证前端能收到报告

    # C. 后台更新长期记忆
    chat_content = f"User上传了JD: {request.jd_text}"
    background_tasks.add_task(update_long_term_memory, db, user.id, chat_content)

    return report


# ==========================================
# 5. 流式响应接口 (Streaming)
# ==========================================
@router.post("/stream/system-design")
async def stream_system_design(tech_stack: str, topic: str):
    """
    流式生成系统设计题答案 (打字机效果)
    """
    llm = get_llm(temperature=0.7)

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
        media_type="text/event-stream"
    )


@router.post("/stream/mock-interview")
async def stream_mock_interview(request: JDRequest):
    """
    开启一场 AI 互博的模拟面试 (流式返回)
    """
    return StreamingResponse(
        run_mock_interview_stream(request.jd_text, rounds=3),
        media_type="text/event-stream"
    )


class ChatRequest(BaseModel):
    session_id: int
    content: str


@router.post("/chat/stream")
async def stream_chat(
        req: ChatRequest,
        db: Session = Depends(get_session)
):
    """
    通用多轮对话流式接口 (支持模拟面试后续的追问)
    """
    # 1. 验证会话
    session = db.get(ChatSession, req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 2. 保存用户的新回复到数据库
    user_msg = ChatMessage(session_id=req.session_id, role="user", content=req.content)
    db.add(user_msg)
    db.commit()

    # 3. 准备历史上下文 (Context)
    # 取最近 10 条记录，防止 Token 爆炸
    recent_msgs = session.messages[-10:]

    # 4. 构建 Prompt
    # 如果是模拟面试模式，系统提示词需要保持“面试官”人设
    # 这里做一个简单的判断：如果标题包含"面试"，就加强面试官人设
    system_prompt = "你是一个很有帮助的 AI 助手。"
    if "面试" in session.title:
        system_prompt = "你是一名严厉但专业的面试官。请根据求职者的回答进行追问，考察其技术深度。每次只问一个问题。"

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

    # 6. 流式生成并(暂存)用于后续保存
    # 注意：在流式响应中保存 AI 回复到数据库比较复杂，
    # 简单做法是前端接收完后再调个 API 保存，或者由 BackgroundTask 聚合。
    # 这里为了演示流畅性，我们先只做流式输出，AI 回复的“入库”逻辑略过，
    # 或者你可以使用一个回调函数在生成结束后保存。

    async def generate_and_stream():
        full_response = ""
        async for chunk in chain.astream(lc_messages):
            full_response += chunk
            yield f"data: {chunk}\n\n"

        # 流结束后，保存 AI 回复到数据库 (补全记录)
        # 注意：这里在生成器里操作 DB 需要小心 Session 作用域，简单场景下直接用即可
        try:
            ai_msg = ChatMessage(session_id=req.session_id, role="assistant", content=full_response)
            db.add(ai_msg)
            db.commit()
        except Exception as e:
            print(f"Error saving AI response: {e}")

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate_and_stream(),
        media_type="text/event-stream"
    )



# ==========================================
# 6. 语音交互接口 (ASR & TTS)
# ==========================================

from fastapi.responses import Response


@router.post("/audio/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    from app.core.config import settings
    from openai import OpenAI

    # 使用 Audio 专用配置
    client = OpenAI(
        api_key=settings.effective_audio_key,
        base_url=settings.effective_audio_base
    )

    file_content = await file.read()

    try:
        transcript = client.audio.transcriptions.create(
            model=settings.ASR_MODEL,  # 使用配置的模型名
            file=(file.filename, file_content, file.content_type)
        )
        return {"text": transcript.text}
    except Exception as e:
        print(f"ASR Error: {e}")
        # 兜底：如果 API 失败，返回空
        return {"text": "", "error": str(e)}


@router.post("/audio/tts")
async def text_to_speech(text: str):
    """
    TTS: 文字转语音
    """
    from openai import OpenAI
    from app.core.config import settings

    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_API_BASE
    )

    try:
        # 调用 TTS 模型 (tts-1 或 tts-1-hd)
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",  # 可选: alloy, echo, fable, onyx, nova, shimmer
            input=text
        )

        # 直接返回二进制音频流
        return Response(
            content=response.content,
            media_type="audio/mpeg"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))