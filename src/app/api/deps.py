# app/api/deps.py
from __future__ import annotations
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from app.core.db_auth import get_session, SECRET_KEY, ALGORITHM
from app.core.models import User
from app.core.llm_factory import get_llm as get_llm_instance_from_factory, CachedLLM
from langchain_openai import ChatOpenAI

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)
):
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


# 依赖函数：提供 LLM 实例
def get_llm(
    temperature: float = 0.5,
    max_tokens: int = 1000,
    streaming: bool = False,
    use_cache: bool = True,
) -> ChatOpenAI | CachedLLM:
    """
    FastAPI 依赖项，用于提供一个配置好的 LLM 实例。
    """
    return get_llm_instance_from_factory(
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=streaming,
        use_cache=use_cache,
    )
