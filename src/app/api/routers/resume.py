from fastapi import APIRouter, Depends, UploadFile, File
from sqlmodel import Session, select
from app.api.deps import get_current_user, get_session
from app.core.models import User, UserProfile
from app.utils.file_parser import parse_resume_file
from app.chains.resume_extractor import extract_resume_features

router = APIRouter()


@router.post("/upload")  # URL 建议简化为 /upload，挂载时加前缀 /resume
async def upload_resume(
        file: UploadFile = File(...),
        user: User = Depends(get_current_user),
        db: Session = Depends(get_session)
):
    resume_text = await parse_resume_file(file)
    facts = await extract_resume_features(resume_text)

    if not facts:
        return {"msg": "简历解析完成，但未提取到有效信息", "count": 0}

    count = 0
    for fact in facts:
        exists = db.exec(
            select(UserProfile).where(UserProfile.user_id == user.id, UserProfile.content == fact.content)).first()
        if not exists:
            db.add(UserProfile(user_id=user.id, category=f"resume_{fact.category}", content=fact.content))
            count += 1
    db.commit()
    return {"msg": "简历解析成功", "new_entries": count}