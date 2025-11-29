from sqlmodel import Session, select
from app.core.models import ChatMessage, ChatSession


def get_recent_chat_history(db: Session, user_id: int, limit: int = 5) -> list[str]:
    """
    获取指定用户的最近几条对话记录 (跨会话或当前会话)
    这里为了简单，我们获取该用户最近一次会话的消息
    """
    # 1. 找到用户最近的一个会话 ID
    last_session = db.exec(
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(ChatSession.created_at.desc())
    ).first()

    if not last_session:
        return []

    # 2. 获取该会话的消息
    messages = db.exec(
        select(ChatMessage)
        .where(ChatMessage.session_id == last_session.id)
        .order_by(ChatMessage.id.asc())  # 按时间正序
    ).all()

    # 3. 格式化为 LangChain 易读的字符串列表
    # 格式: "User: xxx", "Assistant: xxx"
    history = []
    for msg in messages[-limit:]:  # 只取最后 N 条
        role_label = "User" if msg.role == "user" else "Assistant"
        # 简单清洗内容，防止过长
        content_preview = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
        history.append(f"{role_label}: {content_preview}")

    return history