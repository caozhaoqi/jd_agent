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