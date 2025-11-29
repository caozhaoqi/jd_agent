from sqlmodel import Session, select, delete
from app.core.models import UserProfile
from app.chains.memory_extractor import extract_user_profile, UserFact


async def update_long_term_memory(db: Session, user_id: int, chat_history_str: str):
    """
    【写】后台任务：提取对话中的事实并存入数据库
    """
    # 1. 调用 LLM 提取事实
    facts = await extract_user_profile(chat_history_str)

    if not facts:
        return

    # 2. 存入数据库 (简单的追加模式，高级做法是做去重/更新)
    for fact in facts:
        # 简单查重：如果数据库里已经有了完全一样的内容，就不存了
        existing = db.exec(
            select(UserProfile)
            .where(UserProfile.user_id == user_id)
            .where(UserProfile.content == fact.content)
        ).first()

        if not existing:
            new_profile = UserProfile(
                user_id=user_id,
                category=fact.category,
                content=fact.content
            )
            db.add(new_profile)

    db.commit()
    print(f"🧠 [LTM] Updated {len(facts)} new facts for User {user_id}")


def get_user_profile_str(db: Session, user_id: int) -> str:
    """
    【读】获取格式化的用户画像字符串，用于注入 Prompt
    """
    profiles = db.exec(
        select(UserProfile).where(UserProfile.user_id == user_id)
    ).all()

    if not profiles:
        return "用户画像为空 (这是新用户)"

    # 格式化输出
    # Tech Stack: Python, Docker
    # Experience: 5年
    grouped = {}
    for p in profiles:
        if p.category not in grouped:
            grouped[p.category] = []
        grouped[p.category].append(p.content)

    result_str = "【已知用户信息 (长期记忆)】：\n"
    for cat, contents in grouped.items():
        result_str += f"- {cat}: {', '.join(contents)}\n"

    return result_str