from fastapi import APIRouter, Depends, UploadFile, File
from sqlmodel import Session, select
from api.deps import get_current_user, get_session
from core.models import User, UserProfile, ResumeJDMatchRequest
from utils.file_parser import parse_resume_file, analyze_resume_multimodal
from chains.resume_extractor import extract_resume_features
from chains.resume_jd_matcher import match_resume_with_jd
from core.error_handler import raise_internal_error, raise_bad_request
from loguru import logger

router = APIRouter()


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    try:
        logger.info(f"用户 {user.id} 上传简历: {file.filename}")
        resume_text = await parse_resume_file(file)
        if not resume_text:
            raise_bad_request("无法解析简历文件或文件内容为空")

        logger.info(f"简历解析成功，开始提取特征...")
        facts = await extract_resume_features(resume_text)
        logger.info(f"提取到 {len(facts) if facts else 0} 条特征")

        if not facts:
            return {"msg": "简历解析完成，但未提取到有效信息", "new_entries": 0}

        count = 0
        for fact in facts:
            if not fact.content:
                continue
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
        logger.info(f"简历处理完成，新增 {count} 条记录")
        return {"msg": "简历解析成功", "new_entries": count}
    except Exception as e:
        logger.error(f"简历上传处理失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise_internal_error(message="简历处理失败", exc=e)


@router.post("/multimodal")
async def analyze_resume_multimodal_api(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """
    多模态简历分析
    支持图片、PDF中的图表识别
    """
    try:
        logger.info(f"用户 {user.id} 上传简历进行多模态分析: {file.filename}")
        analysis_result = await analyze_resume_multimodal(file)
        logger.info(f"多模态分析完成")
        
        # 提取文本内容进行特征提取
        if analysis_result.get("text"):
            facts = await extract_resume_features(analysis_result["text"])
            analysis_result["extracted_features"] = len(facts) if facts else 0
        
        return {
            "msg": "多模态分析成功",
            "result": analysis_result
        }
    except Exception as e:
        logger.error(f"多模态分析处理失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise_internal_error(message="多模态分析处理失败", exc=e)


@router.post("/match")
async def match_resume_jd(
    request: ResumeJDMatchRequest, user: User = Depends(get_current_user)
):
    """
    匹配简历与JD的API接口
    """
    try:
        if not request.resume_text or not request.jd_text:
            raise_bad_request("简历和JD文本均不能为空")

        match_result = await match_resume_with_jd(
            resume_text=request.resume_text, jd_text=request.jd_text
        )
        return {"msg": "匹配成功", "result": match_result}
    except Exception as e:
        logger.error(f"简历与JD匹配失败: {e}")
        raise_internal_error(message="简历与JD匹配失败", exc=e)
