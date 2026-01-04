from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select
from core.db_auth import (
    get_session,
    get_password_hash,
    verify_password,
    create_access_token,
    verify_token,
)
from core.models import User, AuthRequest
from core.error_handler import raise_bad_request, raise_unauthorized
from loguru import logger

# 定义Bearer认证方案
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
            raise_unauthorized("无效的令牌")

        user = session.exec(select(User).where(User.username == username)).first()
        if user is None:
            raise_unauthorized("用户不存在")

        return user
    except ValueError as e:
        raise_unauthorized(str(e))
    except Exception as e:
        logger.error(f"认证失败: {e}")
        raise_unauthorized("认证失败")


router = APIRouter()


@router.post("/register")
def register(req: AuthRequest, session: Session = Depends(get_session)):
    if session.exec(select(User).where(User.username == req.username)).first():
        raise_bad_request("用户名已存在")

    truncated_password = req.password[:72]
    user = User(
        username=req.username, hashed_password=get_password_hash(truncated_password)
    )
    session.add(user)
    session.commit()
    return {"status": "success", "message": "注册成功"}


@router.post("/login")
def login(req: AuthRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == req.username)).first()
    truncated_password = req.password[:72]
    if not user or not verify_password(truncated_password, user.hashed_password):
        raise_unauthorized("用户名或密码错误")

    token = create_access_token({"sub": user.username})
    return {
        "status": "success",
        "data": {"access_token": token, "token_type": "bearer"},
    }
