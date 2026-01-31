"""
重试服务API端点
提供重试服务的REST API接口
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum

from app.schemas.base import BaseResponse

from app.core.database import get_async_db
from app.core.tenant_auth_dependency import verify_tenant_auth
from app.core.logging import get_logger
from app.models.tenant import Tenant
from app.models.user import User
from app.services.retry_service import (
    RetryService,
    RetryConfig,
    RetryStrategy,
    RetryStatus,
    retry_service
)

logger = get_logger(__name__)
router = APIRouter()


class RetryStrategyEnum(str, Enum):
    """重试策略枚举"""
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    RANDOM = "random"


class RetryStatusEnum(str, Enum):
    """重试状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RetryConfigRequest(BaseModel):
    """重试配置请求"""
    max_retries: int = Field(3, ge=1, le=10, description="最大重试次数")
    base_delay: float = Field(1.0, ge=0.1, le=60.0, description="基础延迟时间（秒）")
    max_delay: float = Field(60.0, ge=1.0, le=300.0, description="最大延迟时间（秒）")
    strategy: RetryStrategyEnum = Field(RetryStrategy.EXPONENTIAL.value, description="重试策略")
    jitter: bool = Field(True, description="是否添加抖动")
    backoff_multiplier: float = Field(2.0, ge=1.0, le=5.0, description="退避乘数")


class RetryTaskResponse(BaseResponse):
    """重试任务响应"""
    task_id: str
    operation_name: str
    status: str
    current_attempt: int
    total_attempts: int
    last_error: Optional[str] = None
    result: Optional[Any] = None


class RetryStatisticsResponse(BaseModel):
    """重试统计响应"""
    total_tasks: int
    success_tasks: int
    failed_tasks: int
    pending_tasks: int
    success_rate: float
    failure_rate: float


@router.get("/retry/statistics", response_model=RetryStatisticsResponse)
async def get_retry_statistics(
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    获取重试统计信息
    """
    tenant, user = auth
    
    logger.info(
        "🔍 获取重试统计信息",
        tenant_id=tenant.id,
        user_id=user.id
    )
    
    try:
        # 获取重试统计信息
        statistics = retry_service.get_retry_statistics()
        
        return RetryStatisticsResponse(
            total_tasks=statistics["total_tasks"],
            success_tasks=statistics["success_tasks"],
            failed_tasks=statistics["failed_tasks"],
            pending_tasks=statistics["pending_tasks"],
            success_rate=statistics["success_rate"],
            failure_rate=statistics["failure_rate"]
        )
        
    except Exception as e:
        logger.error(
            "❌ 获取重试统计信息异常",
            error=str(e)
        )
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取重试统计信息失败: {str(e)}"
        )


@router.get("/retry/tasks")
async def get_retry_tasks(
    status: Optional[RetryStatusEnum] = Query(None, description="任务状态"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    获取重试任务列表
    """
    tenant, user = auth
    
    logger.info(
        "🔍 获取重试任务列表",
        status=status.value if status else None,
        limit=limit,
        tenant_id=tenant.id,
        user_id=user.id
    )
    
    try:
        # 获取重试任务
        tasks = list(retry_service.retry_tasks.values())
        
        # 过滤任务
        if status:
            tasks = [t for t in tasks if t.status.value == status.value]
        
        # 限制数量
        tasks = tasks[:limit]
        
        # 转换为响应格式
        task_data = []
        for task in tasks:
            task_data.append(RetryTaskResponse(
                task_id=task.task_id,
                operation_name=task.operation_name,
                status=task.status.value,
                current_attempt=task.current_attempt,
                total_attempts=task.total_attempts,
                created_at=task.created_at.isoformat(),
                updated_at=task.updated_at.isoformat(),
                last_error=str(task.last_error) if task.last_error else None,
                result=task.result
            ))
        
        return {
            "success": True,
            "tasks": task_data,
            "total_count": len(task_data),
            "message": "获取重试任务列表成功"
        }
        
    except Exception as e:
        logger.error(
            "❌ 获取重试任务列表异常",
            error=str(e)
        )
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取重试任务列表失败: {str(e)}"
        )


@router.get("/retry/tasks/{task_id}")
async def get_retry_task(
    task_id: str = Path(..., description="任务ID"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    获取重试任务详情
    """
    tenant, user = auth
    
    logger.info(
        "🔍 获取重试任务详情",
        task_id=task_id,
        tenant_id=tenant.id,
        user_id=user.id
    )
    
    try:
        # 获取重试任务
        task = retry_service.retry_tasks.get(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"重试任务不存在: {task_id}"
            )
        
        return {
            "success": True,
            "task": RetryTaskResponse(
                task_id=task.task_id,
                operation_name=task.operation_name,
                status=task.status.value,
                current_attempt=task.current_attempt,
                total_attempts=task.total_attempts,
                created_at=task.created_at.isoformat(),
                updated_at=task.updated_at.isoformat(),
                last_error=str(task.last_error) if task.last_error else None,
                result=task.result
            ),
            "message": "获取重试任务详情成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "❌ 获取重试任务详情异常",
            task_id=task_id,
            error=str(e)
        )
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取重试任务详情失败: {str(e)}"
        )


@router.post("/retry/retry-failed")
async def retry_failed_tasks(
    max_tasks: int = Query(10, ge=1, le=50, description="最大重试任务数量"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    重试失败的任务
    """
    tenant, user = auth
    
    logger.info(
        "🔍 开始重试失败的任务",
        max_tasks=max_tasks,
        tenant_id=tenant.id,
        user_id=user.id
    )
    
    try:
        # 重试失败的任务
        result = await retry_service.retry_failed_tasks(max_tasks)
        
        if result.get("success"):
            logger.info(
                "✅ 重试失败任务成功",
                retried_count=result.get("retried_count", 0),
                success_count=result.get("success_count", 0),
                error_count=result.get("error_count", 0)
            )
            return {
                "success": True,
                "message": result.get("message", "重试失败任务成功"),
                "data": result
            }
        else:
            logger.warning(
                "⚠️ 重试失败任务失败",
                error=result.get("message")
            )
            return {
                "success": False,
                "message": result.get("message", "重试失败任务失败"),
                "error": result.get("error")
            }
            
    except Exception as e:
        logger.error(
            "❌ 重试失败任务异常",
            error=str(e)
        )
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重试失败任务失败: {str(e)}"
        )


@router.get("/retry/history")
async def get_retry_history(
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    获取重试历史记录
    """
    tenant, user = auth
    
    logger.info(
        "🔍 获取重试历史记录",
        limit=limit,
        tenant_id=tenant.id,
        user_id=user.id
    )
    
    try:
        # 获取重试历史
        history = retry_service.get_retry_history(limit)
        
        return {
            "success": True,
            "history": history,
            "total_count": len(history),
            "message": "获取重试历史记录成功"
        }
        
    except Exception as e:
        logger.error(
            "❌ 获取重试历史记录异常",
            error=str(e)
        )
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取重试历史记录失败: {str(e)}"
        )


@router.delete("/retry/history")
async def clear_retry_history(
    older_than_days: int = Query(7, ge=1, le=30, description="清理多少天前的历史记录"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    清理重试历史记录
    """
    tenant, user = auth
    
    logger.info(
        "🔍 清理重试历史记录",
        older_than_days=older_than_days,
        tenant_id=tenant.id,
        user_id=user.id
    )
    
    try:
        # 清理重试历史
        retry_service.clear_retry_history(older_than_days)
        
        return {
            "success": True,
            "message": f"清理 {older_than_days} 天前的重试历史记录成功"
        }
        
    except Exception as e:
        logger.error(
            "❌ 清理重试历史记录异常",
            error=str(e)
        )
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清理重试历史记录失败: {str(e)}"
        )


@router.get("/retry/config")
async def get_retry_config(
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    获取重试配置
    """
    tenant, user = auth
    
    logger.info(
        "🔍 获取重试配置",
        tenant_id=tenant.id,
        user_id=user.id
    )
    
    try:
        # 获取默认重试配置
        config = retry_service.default_config
        
        return {
            "success": True,
            "config": {
                "max_retries": config.max_retries,
                "base_delay": config.base_delay,
                "max_delay": config.max_delay,
                "strategy": config.strategy.value,
                "jitter": config.jitter,
                "backoff_multiplier": config.backoff_multiplier
            },
            "message": "获取重试配置成功"
        }
        
    except Exception as e:
        logger.error(
            "❌ 获取重试配置异常",
            error=str(e)
        )
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取重试配置失败: {str(e)}"
        )


@router.put("/retry/config")
async def update_retry_config(
    config: RetryConfigRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    更新重试配置
    """
    tenant, user = auth
    
    logger.info(
        "🔍 更新重试配置",
        config=config.dict(),
        tenant_id=tenant.id,
        user_id=user.id
    )
    
    try:
        # 创建新的重试配置
        new_config = RetryConfig(
            max_retries=config.max_retries,
            base_delay=config.base_delay,
            max_delay=config.max_delay,
            strategy=RetryStrategy(config.strategy.value),
            jitter=config.jitter,
            backoff_multiplier=config.backoff_multiplier
        )
        
        # 更新默认配置
        retry_service.default_config = new_config
        
        return {
            "success": True,
            "message": "更新重试配置成功",
            "config": {
                "max_retries": new_config.max_retries,
                "base_delay": new_config.base_delay,
                "max_delay": new_config.max_delay,
                "strategy": new_config.strategy.value,
                "jitter": new_config.jitter,
                "backoff_multiplier": new_config.backoff_multiplier
            }
        }
        
    except Exception as e:
        logger.error(
            "❌ 更新重试配置异常",
            error=str(e)
        )
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新重试配置失败: {str(e)}"
        )
