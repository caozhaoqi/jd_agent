from fastapi import APIRouter, Depends, UploadFile, File
from sqlmodel import Session, select
from app.api.deps import get_current_user, get_session
from app.core.models import User, UserProfile, ResumeJDMatchRequest
from app.utils.file_parser import parse_resume_file
from app.chains.resume_extractor import extract_resume_features
from app.chains.resume_jd_matcher import match_resume_with_jd
from pydantic import BaseModel

router = APIRouter()


@router.post("/upload")  # URL 建议简化为 /upload，挂载时加前缀 /resume
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    try:
        resume_text = await parse_resume_file(file)
        facts = await extract_resume_features(resume_text)

        if not facts:
            return {"msg": "简历解析完成，但未提取到有效信息", "new_entries": 0}

        count = 0
        for fact in facts:
            exists = db.exec(
                select(UserProfile).where(
                    UserProfile.user_id == user.id, UserProfile.content == fact.content
                )
            ).first()
            if not exists:
                db.add(
                    UserProfile(
                        user_id=user.id,
                        category=f"resume_{fact.category}",
                        content=fact.content,
                    )
                )
                count += 1
        db.commit()
        return {"msg": "简历解析成功", "new_entries": count}
    except Exception as e:
        # 捕获所有异常并返回友好提示
        return {"msg": "简历解析失败", "new_entries": 0}


@router.post("/match")
async def match_resume_jd(
    request: ResumeJDMatchRequest, user: User = Depends(get_current_user)
):
    """
    匹配简历与JD的API接口

    Args:
        request: 包含简历文本和JD文本的请求体
        user: 当前登录用户

    Returns:
        匹配结果包含总体匹配度、优势、不足、建议和详细匹配项
    """
    try:
        match_result = await match_resume_with_jd(
            resume_text=request.resume_text, jd_text=request.jd_text
        )
        return {"msg": "匹配成功", "result": match_result}
    except Exception as e:
        # 捕获所有异常并返回友好提示
        return {
            "msg": "匹配失败",
            "result": {
                "overall_score": 0,
                "strengths": [],
                "weaknesses": [],
                "suggestions": [],
                "detailed_matches": [],
            },
        }
