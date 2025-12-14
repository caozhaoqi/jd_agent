from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.core.db_auth import get_session, get_password_hash, verify_password, create_access_token
from app.core.models import User, AuthRequest
from app.schemas import APIException, ErrorCode

router = APIRouter()

@router.post("/register")
def register(req: AuthRequest, session: Session = Depends(get_session)):
    if session.exec(select(User).where(User.username == req.username)).first():
        raise APIException(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message="用户名已存在"
        )
    # 直接在这里截断密码，确保不会超过bcrypt的72字节限制
    truncated_password = req.password[:72]
    user = User(username=req.username, hashed_password=get_password_hash(truncated_password))
    session.add(user)
    session.commit()
    return {"status": "success", "message": "注册成功"}

@router.post("/login")
def login(req: AuthRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == req.username)).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise APIException(
            status_code=401,
            code=ErrorCode.UNAUTHORIZED,
            message="用户名或密码错误"
        )
    token = create_access_token({"sub": user.username})
    return {"status": "success", "data": {"access_token": token, "token_type": "bearer"}}