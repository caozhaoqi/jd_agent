from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from core.ab_test import ab_test_manager
from core.db_auth import get_db_dependency
from api.deps import get_current_user

router = APIRouter()


class TestResult(BaseModel):
    test_name: str = Field(..., description="测试名称")
    user_id: str = Field(..., description="用户ID")
    variant_name: str = Field(..., description="变体名称")
    result: str = Field(..., description="结果类型（如：success, failure, error_encountered）")
    metrics: Optional[Dict[str, Any]] = Field(default=None, description="相关指标")


class TestConfig(BaseModel):
    enabled: bool = Field(..., description="是否启用")
    variants: Dict[str, Dict[str, Any]] = Field(..., description="变体配置")
    description: Optional[str] = Field(default=None, description="测试描述")


@router.post("/test", response_model=Dict[str, Any])
async def create_ab_test(
    test_name: str = Query(..., description="测试名称"),
    config: TestConfig = ...,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_dependency)
):
    """创建新的A/B测试"""
    try:
        success = ab_test_manager.create_test(test_name, config.model_dump())
        if not success:
            raise HTTPException(status_code=400, detail="创建测试失败")
        return {"message": "测试创建成功", "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test/{test_name}/variant/{user_id}", response_model=Optional[Dict[str, Any]])
async def get_ab_test_variant(
    test_name: str,
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_dependency)
):
    """获取用户的测试变体"""
    try:
        variant = ab_test_manager.get_variant(test_name, user_id)
        if not variant:
            raise HTTPException(status_code=404, detail="未找到变体或测试已禁用")
        return variant
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/result", response_model=Dict[str, Any])
async def record_ab_test_result(
    result: TestResult,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_dependency)
):
    """记录测试结果"""
    try:
        success = ab_test_manager.record_result(
            test_name=result.test_name,
            user_id=result.user_id,
            variant_name=result.variant_name,
            result=result.result,
            metrics=result.metrics
        )
        if not success:
            raise HTTPException(status_code=400, detail="记录结果失败")
        return {"message": "结果记录成功", "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test/{test_name}/results", response_model=Dict[str, Any])
async def get_ab_test_results(
    test_name: str,
    variant_name: Optional[str] = Query(None, description="特定变体名称"),
    time_range: int = Query(86400, description="时间范围（秒）"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_dependency)
):
    """获取测试结果统计"""
    try:
        results = ab_test_manager.get_test_results(
            test_name=test_name,
            variant_name=variant_name,
            time_range=time_range
        )
        if "error" in results:
            raise HTTPException(status_code=404, detail=results["error"])
        return results
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tests", response_model=Dict[str, Any])
async def list_ab_tests(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_dependency)
):
    """列出所有A/B测试"""
    try:
        tests = ab_test_manager.list_tests()
        return tests
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/test/{test_name}", response_model=Dict[str, Any])
async def update_ab_test(
    test_name: str,
    updates: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_dependency)
):
    """更新测试配置"""
    try:
        success = ab_test_manager.update_test(test_name, updates)
        if not success:
            raise HTTPException(status_code=404, detail="测试不存在")
        return {"message": "测试更新成功", "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/test/{test_name}", response_model=Dict[str, Any])
async def delete_ab_test(
    test_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_dependency)
):
    """删除测试"""
    try:
        success = ab_test_manager.delete_test(test_name)
        if not success:
            raise HTTPException(status_code=404, detail="测试不存在")
        return {"message": "测试删除成功", "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
