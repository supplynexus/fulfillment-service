"""
错误监控API端点

提供错误统计、错误上报和错误分析功能
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_async_db
from app.core.auth import verify_jwt_auth
from app.core.error_handler import error_handler, ErrorInfo
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class ErrorReportRequest(BaseModel):
    """错误上报请求"""
    type: str
    severity: str
    message: str
    user_message: str
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    url: str
    user_agent: Optional[str] = None
    viewport: Optional[Dict[str, int]] = None


class ErrorStatsResponse(BaseModel):
    """错误统计响应"""
    total_errors: int
    error_types: Dict[str, Any]
    recent_errors: List[Dict[str, Any]]
    error_trends: Dict[str, Any]


@router.post("/errors/report")
async def report_error(
    error_report: ErrorReportRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> Dict[str, str]:
    """
    上报前端错误
    
    Args:
        error_report: 错误报告数据
        db: 数据库会话
        auth: 认证信息
        
    Returns:
        上报结果
    """
    try:
        tenant, user = auth
        
        logger.info(
            "收到错误报告",
            error_type=error_report.type,
            severity=error_report.severity,
            message=error_report.message,
            tenant_id=tenant.id,
            user_id=user.id
        )
        
        # 这里可以将错误信息存储到数据库或发送到监控服务
        # 例如：存储到错误日志表、发送到Sentry等
        
        return {"message": "错误报告已接收"}
        
    except Exception as e:
        logger.error("处理错误报告失败", error=str(e))
        raise HTTPException(status_code=500, detail="处理错误报告失败")


@router.get("/errors/stats", response_model=ErrorStatsResponse)
async def get_error_stats(
    hours: int = Query(24, description="统计时间范围（小时）"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> ErrorStatsResponse:
    """
    获取错误统计信息
    
    Args:
        hours: 统计时间范围
        db: 数据库会话
        auth: 认证信息
        
    Returns:
        错误统计信息
    """
    try:
        tenant, user = auth
        
        # 获取错误统计
        stats = error_handler.get_error_stats()
        
        # 计算错误趋势（这里简化处理）
        error_trends = {
            "hourly": [],
            "daily": [],
            "weekly": []
        }
        
        # 模拟趋势数据（实际应该从数据库查询）
        current_time = datetime.utcnow()
        for i in range(24):
            hour_time = current_time - timedelta(hours=i)
            error_trends["hourly"].append({
                "time": hour_time.isoformat(),
                "count": 0  # 实际应该查询数据库
            })
        
        return ErrorStatsResponse(
            total_errors=stats["total_errors"],
            error_types=stats["error_types"],
            recent_errors=stats["recent_errors"],
            error_trends=error_trends
        )
        
    except Exception as e:
        logger.error("获取错误统计失败", error=str(e))
        raise HTTPException(status_code=500, detail="获取错误统计失败")


@router.get("/errors/recent")
async def get_recent_errors(
    limit: int = Query(10, description="返回数量限制"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> List[Dict[str, Any]]:
    """
    获取最近的错误信息
    
    Args:
        limit: 返回数量限制
        db: 数据库会话
        auth: 认证信息
        
    Returns:
        最近的错误列表
    """
    try:
        tenant, user = auth
        
        # 获取最近的错误
        stats = error_handler.get_error_stats()
        recent_errors = stats["recent_errors"][:limit]
        
        return recent_errors
        
    except Exception as e:
        logger.error("获取最近错误失败", error=str(e))
        raise HTTPException(status_code=500, detail="获取最近错误失败")


@router.delete("/errors/clear")
async def clear_error_queue(
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> Dict[str, str]:
    """
    清理错误队列
    
    Args:
        db: 数据库会话
        auth: 认证信息
        
    Returns:
        清理结果
    """
    try:
        tenant, user = auth
        
        # 清理错误队列
        error_handler.clear_error_queue()
        
        logger.info("错误队列已清理", tenant_id=tenant.id, user_id=user.id)
        
        return {"message": "错误队列已清理"}
        
    except Exception as e:
        logger.error("清理错误队列失败", error=str(e))
        raise HTTPException(status_code=500, detail="清理错误队列失败")


@router.get("/errors/health")
async def get_error_health(
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> Dict[str, Any]:
    """
    获取错误健康状态
    
    Args:
        db: 数据库会话
        auth: 认证信息
        
    Returns:
        错误健康状态
    """
    try:
        tenant, user = auth
        
        stats = error_handler.get_error_stats()
        
        # 计算健康分数
        total_errors = stats["total_errors"]
        critical_errors = sum(
            count for error_type, data in stats["error_types"].items()
            for severity, count in data["severities"].items()
            if severity == "CRITICAL"
        )
        
        # 简单的健康分数计算
        health_score = max(0, 100 - (total_errors * 2) - (critical_errors * 10))
        
        health_status = "healthy" if health_score >= 80 else "warning" if health_score >= 60 else "critical"
        
        return {
            "health_score": health_score,
            "health_status": health_status,
            "total_errors": total_errors,
            "critical_errors": critical_errors,
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("获取错误健康状态失败", error=str(e))
        raise HTTPException(status_code=500, detail="获取错误健康状态失败")
