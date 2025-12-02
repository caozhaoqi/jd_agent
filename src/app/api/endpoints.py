import asyncio

import jwt
import json
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from loguru import logger
from pydantic import BaseModel
from sqlmodel import Session, select
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json  # 记得导入 json
# 确保导入了必要的工具
from app.core.stream_manager import init_stream_queue


# --- 内部模块导入 ---
# 1. 数据库与鉴权
from app.core.db_auth import get_session, get_password_hash, verify_password, create_access_token, SECRET_KEY, ALGORITHM
from app.core.models import User, ChatSession, ChatMessage, UserProfile, ChatRequest, AuthRequest
from app.core.stream_manager import init_stream_queue
from app.graph.workflow import app_graph

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
        user: User = Depends(get_current_user),
        db: Session = Depends(get_session),
):
    # 1. 生成报告
    report = await generate_interview_guide(request, db, user.id)

    # 2. 存库
    try:
        title = f"{report.meta.company_name} 面试准备" if report.meta.company_name else "岗位 JD 分析"
        new_session = ChatSession(title=title, user_id=user.id)
        db.add(new_session)
        db.commit()
        db.refresh(new_session)

        # 保存消息记录
        db.add(ChatMessage(session_id=new_session.id, role="user", content=request.jd_text))
        db.add(ChatMessage(session_id=new_session.id, role="assistant", content=report.model_dump_json()))
        db.commit()

        # ✅ 关键修改：把 ID 塞回报告里，传给前端
        report.session_id = new_session.id

    except Exception as e:
        logger.error(f"❌ [DB Error] {e}")

    # 3. 更新长期记忆
    background_tasks.add_task(update_long_term_memory, db, user.id, f"User上传了JD: {request.jd_text}")

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



@router.post("/chat/stream")
async def stream_chat(
        req: ChatRequest,
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
        raise HTTPException(status_code=404, detail="会话不存在")

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
        # --- A. 发送思考过程 (Thought) ---
        # 即使是普通对话，发送一个思考状态也能让 UI 看起来更高级，且保持格式一致
        thought_payload = json.dumps({
            "type": "thought",
            "content": "正在分析上下文与面试意图..."
        }, ensure_ascii=False)
        yield f"data: {thought_payload}\n\n"

        # 稍微停顿一下让用户看到思考动画 (可选)
        await asyncio.sleep(0.5)

        # --- B. 发送内容流 (Token) ---
        full_response = ""
        try:
            async for chunk in chain.astream(lc_messages):
                full_response += chunk
                # ✅ 关键修改：包装为 JSON 格式，匹配前端 readStream 的解析逻辑
                token_payload = json.dumps({
                    "type": "token",
                    "content": chunk
                }, ensure_ascii=False)
                yield f"data: {token_payload}\n\n"
        except Exception as e:
            # 发送错误信息
            err_payload = json.dumps({"type": "token", "content": f"\n[Error]: {str(e)}"})
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
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate_and_stream(),
        media_type="text/event-stream"
    )


# ==========================================
# 6. 语音交互接口 (ASR & TTS)
# ==========================================

from fastapi.responses import Response


# app/api/endpoints.py

@router.post("/audio/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    ASR: 语音转文字 (适配 SiliconFlow SenseVoiceSmall)
    """
    from openai import OpenAI
    from app.core.config import settings

    # 1. 初始化客户端
    # 确保使用的是支持 Audio 的 API Key (如 SiliconFlow)
    client = OpenAI(
        api_key=settings.AUDIO_API_KEY or settings.OPENAI_API_KEY,
        base_url=settings.AUDIO_API_BASE or settings.OPENAI_API_BASE
    )

    try:
        # 2. 读取文件二进制内容
        file_content = await file.read()

        # 3. 构造 OpenAI SDK 认可的文件元组 (关键修复!)
        # 格式: (文件名, 二进制数据, MIME类型)
        # 如果 file.filename 为空，强制给一个 "audio.wav"
        filename = file.filename or "audio.wav"

        # 强制指定 MIME 类型，SiliconFlow 对此很敏感
        file_tuple = (filename, file_content, "audio/wav")

        # 4. 调用 API
        transcript = client.audio.transcriptions.create(
            model=settings.ASR_MODEL,  # 确保 .env 是 FunAudioLLM/SenseVoiceSmall
            file=file_tuple,  # 传入构造好的元组
            temperature=0.0
        )
        return {"text": transcript.text}

    except Exception as e:
        logger.debug(f"❌ ASR Error: {e}")
        return {"text": "", "error": str(e)}


@router.post("/audio/tts_old")
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
            # model="tts-1",
            # voice="alloy",  # 可选: alloy, echo, fable, onyx, nova, shimmer
            model=settings.TTS_MODEL,
            voice="alex",  # 注意：FishSpeech 的 voice 参数可能不同，参考官方文档
            # input=text
            input=text
        )

        # 直接返回二进制音频流
        return Response(
            content=response.content,
            media_type="audio/mpeg"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# app/api/endpoints.py

@router.post("/agent/feedback")
async def agent_feedback(thread_id: str, feedback: str, action: str = "retry"):
    """
    用户对 AI 暂停的任务进行干预
    action: "approve" (强制通过) | "retry" (带意见重试)
    """
    config = {"configurable": {"thread_id": thread_id}}

    if action == "approve":
        # 强制更新状态：把分数改成 100，这样路由就会通过
        app_graph.update_state(config, {"quality_score": 100, "human_feedback": "强制通过"})
    else:
        # 注入用户的修改意见
        app_graph.update_state(config, {"human_feedback": feedback})

    # 恢复执行 (Resume)
    # 这里的 None 表示继续执行下一步 (即进入 tech_lead 重写)
    async for event in app_graph.astream(None, config=config):
        pass

    return {"status": "Resumed"}


@router.post("/stream/generate-guide")  # 新增一个流式接口
async def stream_generate_guide(
        request: JDRequest,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_session)
):
    """
    L5 级 Agent 流式生成接口 (支持 DeepSeek 思考过程)
    """

    # 1. 初始化队列 (ContextVar 会自动绑定到当前 task)
    queue = init_stream_queue()

    # 2. 定义后台运行任务
    async def run_graph_background():
        try:
            initial_state = {
                "jd_text": request.jd_text,
                "user_id": user.id,
                "iteration_count": 0,
                "tech_stack": [],
                "years_required": "",
                "company_name": ""
            }

            thread_id = f"user_{user.id}_job_{hash(request.jd_text)}"
            config = {"configurable": {"thread_id": thread_id}}

            # 运行 Graph
            final_state = await app_graph.ainvoke(initial_state, config=config)

            # 运行结束，把最终结果构造成 token 类型发出去
            # 注意：这里我们把整个 Report 打包成一个 JSON 字符串发过去
            # 前端收到 type='result' 时，直接渲染最终报告
            from app.schemas.interview import InterviewReport, JDMetaData

            # --- 🟢 核心修复开始 ---
            # 1. 处理 Technical Questions
            raw_tech_qs = final_state.get("tech_questions", [])
            # 如果是 Pydantic 对象，转为 dict；如果是 dict (如解析失败fallback)，保持原样
            tech_qs_dicts = [
                q.model_dump() if hasattr(q, "model_dump") else q
                for q in raw_tech_qs
            ]

            # 2. 处理 HR Questions
            raw_hr_qs = final_state.get("hr_questions", [])
            hr_qs_dicts = [
                q.model_dump() if hasattr(q, "model_dump") else q
                for q in raw_hr_qs
            ]

            # ... 组装 Report 逻辑 (同 interview_service) ...
            # 为了演示，简单组装
            # 简单构造 Meta
            final_meta = {
                "company_name": final_state.get("company_name"),
                "tech_stack": final_state.get("tech_stack"),
                "years_required": final_state.get("years_required"),
                "soft_skills": []  # 暂空
            }

            final_report = {
                "meta": final_meta,
                "tech_questions": tech_qs_dicts,
                "hr_questions": hr_qs_dicts,
                "company_analysis": final_state.get("company_info"),
                "session_id": None
            }

            # --- 存库逻辑 (可选，建议加上) ---
            try:
                title = f"{final_meta['company_name']} 面试准备" if final_meta['company_name'] else "JD 分析"
                new_sess = ChatSession(title=title, user_id=user.id)
                db.add(new_sess)
                db.commit()
                db.refresh(new_sess)
                final_report["session_id"] = new_sess.id
                # 保存消息
                db.add(ChatMessage(session_id=new_sess.id, role="user", content=request.jd_text))
                db.add(ChatMessage(session_id=new_sess.id, role="assistant", content=json.dumps(final_report)))
                db.commit()
            except Exception as db_e:
                logger.error(f"DB Error: {db_e}")

            await queue.put({
                "type": "result",  # 标记为最终结果
                "content": json.dumps(final_report)
            })


        except Exception as e:

            logger.error(f"❌ [Graph Error] {e}")  # 打印错误堆栈

            await queue.put({"type": "error", "content": str(e)})

        finally:
            # 发送结束信号
            await queue.put(None)

            # 3. 启动后台任务

    task = asyncio.create_task(run_graph_background())

    # 4. 定义生成器 (消费队列)
    async def event_generator():
        while True:
            # 等待队列消息
            data = await queue.get()

            if data is None:  # 结束信号
                yield "data: [DONE]\n\n"
                break

            # 发送 SSE
            yield f"data: {json.dumps(data)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


import platform
import subprocess
import tempfile
import os
import uuid
import pyttsx3  # 用于 Windows/Linux
from fastapi.responses import Response

# 预初始化 Windows/Linux 的引擎 (Mac 不用这个)
try:
    if platform.system() != "Darwin":
        engine = pyttsx3.init()
except Exception as e:
    logger.error(f"⚠️ pyttsx3 init failed: {e}")


@router.post("/audio/tts")
async def text_to_speech(text: str):
    """
    跨平台 TTS 接口 (完全离线，零延迟)
    - macOS: 调用 'say' 命令 -> .m4a
    - Windows/Linux: 调用 pyttsx3 -> .wav
    """
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="文本为空")

    # 获取当前操作系统名称 ('Darwin', 'Windows', 'Linux')
    system_os = platform.system()

    # 定义临时文件路径
    unique_id = uuid.uuid4()
    temp_dir = tempfile.gettempdir()

    try:
        audio_data = None
        mime_type = ""
        output_path = ""

        # ============================
        # 🍎 方案 A: macOS (Darwin)
        # ============================
        if system_os == "Darwin":
            output_path = os.path.join(temp_dir, f"tts_{unique_id}.m4a")
            mime_type = "audio/mp4"  # m4a 属于 mp4 容器

            # 使用 macOS 原生 say 命令
            process = subprocess.run(
                ["say", "-o", output_path, text],
                capture_output=True,
                text=True
            )
            if process.returncode != 0:
                raise Exception(f"Mac TTS failed: {process.stderr}")

        # ============================
        # 🪟/🐧 方案 B: Windows / Linux
        # ============================
        else:
            output_path = os.path.join(temp_dir, f"tts_{unique_id}.wav")
            mime_type = "audio/wav"

            # 使用 pyttsx3 (SAPI5 / eSpeak)
            # 注意：pyttsx3 是同步阻塞的，高并发建议放入线程池，单人使用无所谓
            engine.save_to_file(text, output_path)
            engine.runAndWait()

        # ============================
        # 3. 读取并清理
        # ============================
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise Exception("音频文件生成失败")

        with open(output_path, "rb") as f:
            audio_data = f.read()

        # 删除临时文件
        os.remove(output_path)

        return Response(content=audio_data, media_type=mime_type)

    except Exception as e:
        logger.debug(f"❌ [TTS Error] OS: {system_os} | Error: {e}")
        # 尝试清理残余文件
        if 'output_path' in locals() and os.path.exists(output_path):
            os.remove(output_path)
        raise HTTPException(status_code=500, detail=f"TTS生成失败: {str(e)}")


from livekit import api
import os


@router.get("/webrtc/token")
async def get_livekit_token(user: User = Depends(get_current_user)):
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")

    grant = api.VideoGrant(room_join=True, agent=True)
    token = api.AccessToken(api_key, api_secret, identity=f"user_{user.id}")
    token.add_grant(grant)

    return {"token": token.to_jwt(), "url": os.getenv("LIVEKIT_URL")}