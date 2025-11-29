from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 导入内部模块
from app.schemas.interview import JDRequest, InterviewReport
from app.services.interview_service import generate_interview_guide
from app.core.llm_factory import get_llm
from app.services.memory_service import update_long_term_memory
from app.services.mock_service import run_mock_interview_stream

# 1. 核心修复：实例化 APIRouter
router = APIRouter()


from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from app.core.db_auth import get_session, get_password_hash, verify_password, create_access_token, SECRET_KEY, ALGORITHM
from app.core.models import User, ChatSession, ChatMessage
from pydantic import BaseModel
import jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")

# --- 依赖：获取当前用户 ---
async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="无效的凭证")
    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


from fastapi import UploadFile, File  # 新增
from app.utils.file_parser import parse_resume_file
from app.chains.resume_extractor import extract_resume_features
from app.core.models import UserProfile  # 确保导入模型


# 新增：简历上传与解析接口
@router.post("/upload-resume")
async def upload_resume(
        file: UploadFile = File(...),
        user: User = Depends(get_current_user),
        db: Session = Depends(get_session)
):
    """
    上传简历 -> 解析文本 -> LLM提取画像 -> 存入长期记忆
    """
    # 1. 解析文件
    resume_text = await parse_resume_file(file)

    # 2. 调用 LLM 提取关键信息
    facts = await extract_resume_features(resume_text)

    if not facts:
        return {"msg": "简历解析完成，但未提取到有效信息", "count": 0}

    # 3. 存入数据库 (UserProfile)
    # 策略：先清除该用户旧的简历相关 tag (可选)，或者直接追加
    # 这里我们选择追加，但在前端可以展示
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


# --- Auth 接口 ---
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

# --- History 接口 ---
@router.get("/history/sessions")
def get_sessions(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    # 返回该用户的所有会话列表 (倒序)
    statement = select(ChatSession).where(ChatSession.user_id == user.id).order_by(ChatSession.id.desc())
    return session.exec(statement).all()

@router.get("/history/messages/{session_id}")
def get_messages(session_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    # 验证 session 是否属于该用户
    chat = session.get(ChatSession, session_id)
    if not chat or chat.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    return chat.messages

# --- 原有的普通接口 ---
# 🔴 修改后的核心接口：生成指南 + 自动存库
@router.post("/generate-guide", response_model=InterviewReport)
async def create_guide(
        request: JDRequest,

        background_tasks: BackgroundTasks,

        # 1. 注入当前登录用户 (必须登录才能存历史)
        user: User = Depends(get_current_user),

        # 2. 注入数据库会话
        db: Session = Depends(get_session),
):
    """
    接收 JD 文本，返回完整的面试准备指南，并自动保存到历史记录。
    """
    # A. 调用业务逻辑生成报告
    report = await generate_interview_guide(request, db, user.id)

    # B. --- 数据库存盘逻辑 (新增) ---
    try:
        # 1. 创建新的会话 (ChatSession)
        # 使用公司名作为标题，如果没有识别到公司名，则用默认标题
        title = f"{report.meta.company_name} 面试准备" if report.meta.company_name else "岗位 JD 分析"

        new_session = ChatSession(
            title=title,
            user_id=user.id
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)  # 刷新以获取生成的 ID

        # 2. 保存用户的提问 (User Message)
        user_msg = ChatMessage(
            session_id=new_session.id,
            role="user",
            content=request.jd_text
        )
        db.add(user_msg)

        # 3. 保存 AI 的回答 (Assistant Message)
        # 注意：我们将 Pydantic 对象转为 JSON 字符串存入数据库
        ai_msg = ChatMessage(
            session_id=new_session.id,
            role="assistant",
            content=report.model_dump_json()  # Pydantic v2 写法，如果是 v1 用 .json()
        )
        db.add(ai_msg)

        # 4. 提交保存
        db.commit()

        print(f"✅ [DB] 会话已保存: ID={new_session.id}, Title={title}")

    except Exception as e:
        print(f"❌ [DB Error] 保存历史记录失败: {e}")
        # 注意：这里我们只打印错误，不抛出异常，避免因为存库失败导致前端收不到分析结果
        # db.rollback()

    chat_content = f"User上传了JD: {request.jd_text}"
    background_tasks.add_task(update_long_term_memory, db, user.id, chat_content)

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

# 新增：模拟面试接口
@router.post("/stream/mock-interview")
async def stream_mock_interview(request: JDRequest):
    """
    开启一场 AI 互博的模拟面试
    """
    return StreamingResponse(
        run_mock_interview_stream(request.jd_text, rounds=3),
        media_type="text/event-stream"
    )