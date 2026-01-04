# app/api/deps.py
from __future__ import annotations
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select
from core.db_auth import get_session, SECRET_KEY, ALGORITHM, verify_token
from core.models import User
from core.llm_factory import get_llm as get_llm_instance_from_factory, CachedLLM
from langchain_openai import ChatOpenAI

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
):
    """
    获取当前认证用户
    - 验证JWT令牌
    - 从数据库中获取用户信息
    - 令牌无效或用户不存在时抛出异常
    """
    token = credentials.credentials
    try:
        payload = verify_token(token)
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="无效的令牌")

        user = session.exec(select(User).where(User.username == username)).first()
        if user is None:
            raise HTTPException(status_code=401, detail="用户不存在")

        return user
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=401, detail="认证失败")


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
