from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.db_auth import get_session, get_password_hash, verify_password, create_access_token
from app.core.models import User, AuthRequest

router = APIRouter()

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