from fastapi import APIRouter, HTTPException, Depends, Response
from typing import Optional, List, Any
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import json

from core.db_auth import get_db_dependency
from models.interview_report import InterviewReportExport, InterviewReportExportCreate
from core.models import ChatSession, ChatMessage
from services.report_export_service import export_service
from api.deps import get_current_user

router = APIRouter()


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[Any] = None


class InterviewSessionResponse(BaseModel):
    id: int
    title: str
    job_position: str
    created_at: datetime
    message_count: int


class SessionListResponse(BaseModel):
    sessions: List[InterviewSessionResponse]
    total: int


class ExportRequest(BaseModel):
    """导出请求"""
    company_name: Optional[str] = None
    position: Optional[str] = None
    export_format: str = "markdown"
    report_title: str = "面试报告"
    
    meta_info: Optional[dict] = None
    tech_questions: Optional[list] = None
    hr_questions: Optional[list] = None
    company_analysis: Optional[str] = None
    
    overall_score: Optional[int] = None
    key_strengths: Optional[list] = None
    areas_for_improvement: Optional[list] = None
    
    team_id: Optional[int] = None
    session_id: Optional[int] = None  # 添加session_id字段


class ExportListResponse(BaseModel):
    """导出列表响应"""
    id: int
    report_title: str
    company_name: Optional[str]
    position: Optional[str]
    export_format: str
    created_at: datetime


@router.get("/sessions", response_model=ApiResponse)
async def list_sessions(
    db: AsyncSession = Depends(get_db_dependency),
    user=Depends(get_current_user)
):
    print(f"[DEBUG] Current user: {user.id}, {user.username}")
    """获取面试记录列表"""
    sessions_result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user.id)
        .order_by(ChatSession.created_at.desc())
    )
    sessions = sessions_result.scalars().all()
    
    session_responses = []
    for session in sessions:
        count_result = await db.execute(
            select(func.count())
            .select_from(ChatMessage)
            .where(ChatMessage.session_id == session.id)
        )
        message_count = count_result.scalar() or 0
        
        session_responses.append({
            "id": session.id,
            "title": session.title or "未命名会话",
            "job_position": getattr(session, 'job_position', None) or "未指定职位",
            "created_at": session.created_at.isoformat(),
            "message_count": message_count
        })
    
    return ApiResponse(
        code=0,
        message="success",
        data={
            "sessions": session_responses,
            "total": len(session_responses)
        }
    )


@router.get("/exports", response_model=list[ExportListResponse])
async def list_exports(
    team_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db_dependency),
    user=Depends(get_current_user)
):
    """获取导出记录列表"""
    query = select(InterviewReportExport).where(InterviewReportExport.user_id == user.id)
    
    if team_id:
        query = query.where(InterviewReportExport.team_id == team_id)
    
    query = query.order_by(InterviewReportExport.created_at.desc())
    
    result = await db.execute(query)
    exports = result.scalars().all()
    
    return [
        ExportListResponse(
            id=e.id,
            report_title=e.report_title,
            company_name=e.company_name,
            position=e.position,
            export_format=e.export_format,
            created_at=e.created_at
        )
        for e in exports
    ]


@router.get("/history")
async def get_history(
    team_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db_dependency),
    user=Depends(get_current_user)
):
    """获取导出历史记录"""
    query = select(InterviewReportExport).where(InterviewReportExport.user_id == user.id)
    
    if team_id:
        query = query.where(InterviewReportExport.team_id == team_id)
    
    query = query.order_by(InterviewReportExport.created_at.desc())
    
    result = await db.execute(query)
    exports = result.scalars().all()
    
    return {
        "code": 0,
        "message": "success",
        "data": {
            "records": [
                {
                    "id": e.id,
                    "report_title": e.report_title,
                    "company_name": e.company_name,
                    "position": e.position,
                    "format": e.export_format,
                    "created_at": e.created_at
                }
                for e in exports
            ]
        }
    }


@router.post("/export")
async def create_export(
    request: ExportRequest,
    db: AsyncSession = Depends(get_db_dependency),
    user=Depends(get_current_user)
):
    """创建并下载面试报告导出"""
    
    # 从session_id获取会话数据
    if request.session_id:
        # 获取会话
        session_result = await db.execute(
            select(ChatSession)
            .where(
                ChatSession.id == request.session_id,
                ChatSession.user_id == user.id
            )
        )
        session = session_result.scalar_one_or_none()
        
        if session:
            # 获取会话消息
            messages_result = await db.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == request.session_id)
                .order_by(ChatMessage.created_at)
            )
            messages = messages_result.scalars().all()
            
            # 解析消息内容，提取面试报告数据
            for message in messages:
                if message.role == "assistant":
                    try:
                        content_json = json.loads(message.content)
                        # 更新请求数据
                        if "meta" in content_json:
                            request.meta_info = content_json["meta"]
                            if not request.company_name and content_json["meta"].get("company_name"):
                                request.company_name = content_json["meta"]["company_name"]
                            if not request.position and content_json["meta"].get("job_position"):
                                request.position = content_json["meta"]["job_position"]
                        if "tech_questions" in content_json:
                            request.tech_questions = content_json["tech_questions"]
                        if "hr_questions" in content_json:
                            request.hr_questions = content_json["hr_questions"]
                        if "company_analysis" in content_json:
                            request.company_analysis = content_json["company_analysis"]
                    except:
                        continue
    
    format_lower = request.export_format.lower()
    
    if format_lower == "markdown":
        content = export_service.generate_markdown(
            report_title=request.report_title,
            company_name=request.company_name,
            position=request.position,
            meta_info=request.meta_info,
            tech_questions=request.tech_questions,
            hr_questions=request.hr_questions,
            company_analysis=request.company_analysis,
            overall_score=request.overall_score,
            key_strengths=request.key_strengths,
            areas_for_improvement=request.areas_for_improvement
        )
        
        export_record = InterviewReportExport(
            user_id=user.id,
            team_id=request.team_id,
            company_name=request.company_name,
            position=request.position,
            export_format="markdown",
            report_title=request.report_title,
            meta_info=json.dumps(request.meta_info) if request.meta_info else None,
            tech_questions=json.dumps(request.tech_questions) if request.tech_questions else None,
            hr_questions=json.dumps(request.hr_questions) if request.hr_questions else None,
            company_analysis=request.company_analysis,
            overall_score=request.overall_score,
            key_strengths=json.dumps(request.key_strengths) if request.key_strengths else None,
            areas_for_improvement=json.dumps(request.areas_for_improvement) if request.areas_for_improvement else None,
        )
        db.add(export_record)
        await db.commit()
        await db.refresh(export_record)
        
        import unicodedata
        ascii_filename = unicodedata.normalize('NFKD', request.report_title).encode('ascii', 'ignore').decode('ascii')
        if not ascii_filename.strip():
            ascii_filename = f"interview_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        url_encoded = request.report_title.encode('utf-8').decode('latin-1')

        return Response(
            content=content,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{ascii_filename}.md"; filename*=utf-8\'\'{url_encoded}.md'
            }
        )
    
    elif format_lower == "html":
        content = export_service.generate_html(
            report_title=request.report_title,
            company_name=request.company_name,
            position=request.position,
            meta_info=request.meta_info,
            tech_questions=request.tech_questions,
            hr_questions=request.hr_questions,
            company_analysis=request.company_analysis,
            overall_score=request.overall_score,
            key_strengths=request.key_strengths,
            areas_for_improvement=request.areas_for_improvement
        )
        
        export_record = InterviewReportExport(
            user_id=user.id,
            team_id=request.team_id,
            company_name=request.company_name,
            position=request.position,
            export_format="html",
            report_title=request.report_title,
            meta_info=json.dumps(request.meta_info) if request.meta_info else None,
            tech_questions=json.dumps(request.tech_questions) if request.tech_questions else None,
            hr_questions=json.dumps(request.hr_questions) if request.hr_questions else None,
            company_analysis=request.company_analysis,
            overall_score=request.overall_score,
            key_strengths=json.dumps(request.key_strengths) if request.key_strengths else None,
            areas_for_improvement=json.dumps(request.areas_for_improvement) if request.areas_for_improvement else None,
        )
        db.add(export_record)
        await db.commit()
        await db.refresh(export_record)
        
        import unicodedata
        ascii_filename = unicodedata.normalize('NFKD', request.report_title).encode('ascii', 'ignore').decode('ascii')
        if not ascii_filename.strip():
            ascii_filename = f"interview_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        url_encoded = request.report_title.encode('utf-8').decode('latin-1')

        return Response(
            content=content,
            media_type="text/html; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{ascii_filename}.html"; filename*=utf-8\'\'{url_encoded}.html'
            }
        )
    
    elif format_lower == "text":
        content = export_service.generate_text(
            report_title=request.report_title,
            company_name=request.company_name,
            position=request.position,
            meta_info=request.meta_info,
            tech_questions=request.tech_questions,
            hr_questions=request.hr_questions,
            company_analysis=request.company_analysis,
            overall_score=request.overall_score,
            key_strengths=request.key_strengths,
            areas_for_improvement=request.areas_for_improvement
        )
        
        export_record = InterviewReportExport(
            user_id=user.id,
            team_id=request.team_id,
            company_name=request.company_name,
            position=request.position,
            export_format="text",
            report_title=request.report_title,
            meta_info=json.dumps(request.meta_info) if request.meta_info else None,
            tech_questions=json.dumps(request.tech_questions) if request.tech_questions else None,
            hr_questions=json.dumps(request.hr_questions) if request.hr_questions else None,
            company_analysis=request.company_analysis,
            overall_score=request.overall_score,
            key_strengths=json.dumps(request.key_strengths) if request.key_strengths else None,
            areas_for_improvement=json.dumps(request.areas_for_improvement) if request.areas_for_improvement else None,
        )
        db.add(export_record)
        await db.commit()
        await db.refresh(export_record)
        
        import unicodedata
        ascii_filename = unicodedata.normalize('NFKD', request.report_title).encode('ascii', 'ignore').decode('ascii')
        if not ascii_filename.strip():
            ascii_filename = f"interview_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        url_encoded = request.report_title.encode('utf-8').decode('latin-1')

        return Response(
            content=content,
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{ascii_filename}.txt"; filename*=utf-8\'\'{url_encoded}.txt'
            }
        )
    
    else:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的导出格式: {format_lower}。支持的格式: markdown, html, text"
        )


@router.get("/exports/{export_id}")
async def get_export(
    export_id: int,
    db: AsyncSession = Depends(get_db_dependency),
    user=Depends(get_current_user)
):
    """获取导出记录详情"""
    result = await db.execute(
        select(InterviewReportExport).where(
            InterviewReportExport.id == export_id,
            InterviewReportExport.user_id == user.id
        )
    )
    export = result.scalar_one_or_none()
    
    if not export:
        raise HTTPException(status_code=404, detail="导出记录不存在")
    
    return {
        "id": export.id,
        "report_title": export.report_title,
        "company_name": export.company_name,
        "position": export.position,
        "export_format": export.export_format,
        "created_at": export.created_at,
        "meta_info": json.loads(export.meta_info) if export.meta_info else None,
        "tech_questions": json.loads(export.tech_questions) if export.tech_questions else None,
        "hr_questions": json.loads(export.hr_questions) if export.hr_questions else None,
        "company_analysis": export.company_analysis,
        "overall_score": export.overall_score,
        "key_strengths": json.loads(export.key_strengths) if export.key_strengths else None,
        "areas_for_improvement": json.loads(export.areas_for_improvement) if export.areas_for_improvement else None,
    }


@router.get("/exports/{export_id}/download")
async def download_export(
    export_id: int,
    format: str = "markdown",
    db: AsyncSession = Depends(get_db_dependency),
    user=Depends(get_current_user)
):
    """重新下载导出文件"""
    result = await db.execute(
        select(InterviewReportExport).where(
            InterviewReportExport.id == export_id,
            InterviewReportExport.user_id == user.id
        )
    )
    export = result.scalar_one_or_none()
    
    if not export:
        raise HTTPException(status_code=404, detail="导出记录不存在")
    
    meta_info = json.loads(export.meta_info) if export.meta_info else None
    tech_questions = json.loads(export.tech_questions) if export.tech_questions else None
    hr_questions = json.loads(export.hr_questions) if export.hr_questions else None
    key_strengths = json.loads(export.key_strengths) if export.key_strengths else None
    areas_for_improvement = json.loads(export.areas_for_improvement) if export.areas_for_improvement else None
    
    format_lower = format.lower()
    
    if format_lower == "markdown":
        content = export_service.generate_markdown(
            report_title=export.report_title,
            company_name=export.company_name,
            position=export.position,
            meta_info=meta_info,
            tech_questions=tech_questions,
            hr_questions=hr_questions,
            company_analysis=export.company_analysis,
            overall_score=export.overall_score,
            key_strengths=key_strengths,
            areas_for_improvement=areas_for_improvement
        )
        
        return Response(
            content=content,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{export.report_title}.md"'
            }
        )
    
    elif format_lower == "html":
        content = export_service.generate_html(
            report_title=export.report_title,
            company_name=export.company_name,
            position=export.position,
            meta_info=meta_info,
            tech_questions=tech_questions,
            hr_questions=hr_questions,
            company_analysis=export.company_analysis,
            overall_score=export.overall_score,
            key_strengths=key_strengths,
            areas_for_improvement=areas_for_improvement
        )
        
        return Response(
            content=content,
            media_type="text/html; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{export.report_title}.html"'
            }
        )
    
    elif format_lower == "text":
        content = export_service.generate_text(
            report_title=export.report_title,
            company_name=export.company_name,
            position=export.position,
            meta_info=meta_info,
            tech_questions=tech_questions,
            hr_questions=hr_questions,
            company_analysis=export.company_analysis,
            overall_score=export.overall_score,
            key_strengths=key_strengths,
            areas_for_improvement=areas_for_improvement
        )
        
        return Response(
            content=content,
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{export.report_title}.txt"'
            }
        )
    
    else:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的导出格式: {format_lower}。支持的格式: markdown, html, text"
        )


@router.delete("/exports/{export_id}")
async def delete_export(
    export_id: int,
    db: AsyncSession = Depends(get_db_dependency),
    user=Depends(get_current_user)
):
    """删除导出记录"""
    result = await db.execute(
        select(InterviewReportExport).where(
            InterviewReportExport.id == export_id,
            InterviewReportExport.user_id == user.id
        )
    )
    export = result.scalar_one_or_none()
    
    if not export:
        raise HTTPException(status_code=404, detail="导出记录不存在")
    
    await db.delete(export)
    await db.commit()
    
    return {"message": "导出记录已删除"}
