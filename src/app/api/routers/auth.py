from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select
from app.core.db_auth import (
    get_session,
    get_password_hash,
    verify_password,
    create_access_token,
    verify_token,
)
from app.core.models import User, AuthRequest
from app.schemas import APIException, ErrorCode

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
            raise APIException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code=ErrorCode.UNAUTHORIZED,
                message="无效的令牌",
            )

        # 从数据库获取用户信息
        user = session.exec(select(User).where(User.username == username)).first()
        if user is None:
            raise APIException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code=ErrorCode.UNAUTHORIZED,
                message="用户不存在",
            )

        return user
    except ValueError as e:
        raise APIException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=ErrorCode.UNAUTHORIZED,
            message=str(e),
        )
    except Exception as e:
        raise APIException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=ErrorCode.UNAUTHORIZED,
            message="认证失败",
        )


router = APIRouter()


@router.post("/register")
def register(req: AuthRequest, session: Session = Depends(get_session)):
    if session.exec(select(User).where(User.username == req.username)).first():
        raise APIException(
            status_code=400, code=ErrorCode.BAD_REQUEST, message="用户名已存在"
        )
    # 直接在这里截断密码，确保不会超过bcrypt的72字节限制
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
    if not user or not verify_password(req.password, user.hashed_password):
        raise APIException(
            status_code=401, code=ErrorCode.UNAUTHORIZED, message="用户名或密码错误"
        )
    token = create_access_token({"sub": user.username})
    return {
        "status": "success",
        "data": {"access_token": token, "token_type": "bearer"},
    }
