"""
多平台状态同步API端点
提供跨平台状态同步的REST API接口
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum

from app.core.database import get_async_db
from app.core.tenant_auth_dependency import verify_tenant_auth
from app.core.logging import get_logger
from app.models.tenant import Tenant
from app.models.user import User
from app.services.multi_platform_sync_service import (
    MultiPlatformSyncService,
    OrderSystemType,
    SyncPriority,
    SyncStatus
)

logger = get_logger(__name__)
router = APIRouter()


class OrderSystemTypeEnum(str, Enum):
    """订单系统类型枚举"""
    CORE = "core"
    SCM = "scm"
    SHOPIFY = "shopify"
    PRINTIFY = "printify"


class SyncPriorityEnum(str, Enum):
    """同步优先级枚举"""
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class MultiPlatformSyncRequest(BaseModel):
    """多平台同步请求"""
    order_id: int = Field(..., description="订单ID")
    source_system: OrderSystemTypeEnum = Field(..., description="源系统")
    target_systems: List[OrderSystemTypeEnum] = Field(..., description="目标系统列表")
    force_sync: bool = Field(False, description="是否强制同步")


class AutoSyncRequest(BaseModel):
    """自动同步请求"""
    order_id: int = Field(..., description="订单ID")
    system_type: OrderSystemTypeEnum = Field(..., description="系统类型")
    new_status: str = Field(..., description="新状态")


class BatchSyncRequest(BaseModel):
    """批量同步请求"""
    system_type: OrderSystemTypeEnum = Field(..., description="系统类型")
    limit: int = Field(100, ge=1, le=1000, description="最大处理数量")
    status_filter: Optional[List[str]] = Field(None, description="状态过滤器")


class SyncResponse(BaseModel):
    """同步响应"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/sync/multi-platform", response_model=SyncResponse)
async def sync_order_across_platforms(
    request: MultiPlatformSyncRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    跨平台同步订单状态
    """
    tenant, user = auth
    
    logger.info(
        "🔍 开始跨平台同步订单状态",
        order_id=request.order_id,
        source_system=request.source_system.value,
        target_systems=[t.value for t in request.target_systems],
        tenant_id=tenant.id,
        user_id=user.id,
        force_sync=request.force_sync
    )
    
    try:
        # 创建多平台同步服务
        sync_service = MultiPlatformSyncService(db)
        
        # 转换系统类型
        source_system = OrderSystemType(request.source_system.value)
        target_systems = [OrderSystemType(t.value) for t in request.target_systems]
        
        # 执行跨平台同步
        result = await sync_service.sync_order_across_platforms(
            order_id=request.order_id,
            source_system=source_system,
            target_systems=target_systems,
            tenant_id=tenant.id,
            force_sync=request.force_sync
        )
        
        if result.get("success"):
            logger.info(
                "✅ 跨平台同步订单状态成功",
                order_id=request.order_id,
                success_count=result.get("success_count", 0),
                error_count=result.get("error_count", 0)
            )
            return SyncResponse(
                success=True,
                message=result.get("message", "跨平台同步成功"),
                data=result
            )
        else:
            logger.warning(
                "⚠️ 跨平台同步订单状态失败",
                order_id=request.order_id,
                error=result.get("message")
            )
            return SyncResponse(
                success=False,
                message=result.get("message", "跨平台同步失败"),
                error=result.get("error")
            )
            
    except Exception as e:
        logger.error(
            "❌ 跨平台同步订单状态异常",
            order_id=request.order_id,
            source_system=request.source_system.value,
            target_systems=[t.value for t in request.target_systems],
            error=str(e)
        )
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"跨平台同步订单状态失败: {str(e)}"
        )


@router.post("/sync/auto", response_model=SyncResponse)
async def auto_sync_order_status(
    request: AutoSyncRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    自动同步订单状态变更
    """
    tenant, user = auth
    
    logger.info(
        "🔍 开始自动同步订单状态变更",
        order_id=request.order_id,
        system_type=request.system_type.value,
        new_status=request.new_status,
        tenant_id=tenant.id,
        user_id=user.id
    )
    
    try:
        # 创建多平台同步服务
        sync_service = MultiPlatformSyncService(db)
        
        # 转换系统类型
        system_type = OrderSystemType(request.system_type.value)
        
        # 执行自动同步
        result = await sync_service.auto_sync_order_status(
            order_id=request.order_id,
            system_type=system_type,
            new_status=request.new_status,
            tenant_id=tenant.id
        )
        
        if result.get("success"):
            logger.info(
                "✅ 自动同步订单状态变更成功",
                order_id=request.order_id,
                synced_count=result.get("synced_count", 0)
            )
            return SyncResponse(
                success=True,
                message=result.get("message", "自动同步成功"),
                data=result
            )
        else:
            logger.warning(
                "⚠️ 自动同步订单状态变更失败",
                order_id=request.order_id,
                error=result.get("message")
            )
            return SyncResponse(
                success=False,
                message=result.get("message", "自动同步失败"),
                error=result.get("error")
            )
            
    except Exception as e:
        logger.error(
            "❌ 自动同步订单状态变更异常",
            order_id=request.order_id,
            system_type=request.system_type.value,
            new_status=request.new_status,
            error=str(e)
        )
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"自动同步订单状态变更失败: {str(e)}"
        )


@router.post("/sync/batch", response_model=SyncResponse)
async def batch_sync_orders(
    request: BatchSyncRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    批量同步订单状态
    """
    tenant, user = auth
    
    logger.info(
        "🔍 开始批量同步订单状态",
        system_type=request.system_type.value,
        limit=request.limit,
        status_filter=request.status_filter,
        tenant_id=tenant.id,
        user_id=user.id
    )
    
    try:
        # 创建多平台同步服务
        sync_service = MultiPlatformSyncService(db)
        
        # 转换系统类型
        system_type = OrderSystemType(request.system_type.value)
        
        # 执行批量同步
        result = await sync_service.batch_sync_orders(
            system_type=system_type,
            tenant_id=tenant.id,
            limit=request.limit,
            status_filter=request.status_filter
        )
        
        if result.get("success"):
            logger.info(
                "✅ 批量同步订单状态成功",
                system_type=request.system_type.value,
                success_count=result.get("success_count", 0),
                error_count=result.get("error_count", 0)
            )
            return SyncResponse(
                success=True,
                message=result.get("message", "批量同步成功"),
                data=result
            )
        else:
            logger.warning(
                "⚠️ 批量同步订单状态失败",
                system_type=request.system_type.value,
                error=result.get("message")
            )
            return SyncResponse(
                success=False,
                message=result.get("message", "批量同步失败"),
                error=result.get("error")
            )
            
    except Exception as e:
        logger.error(
            "❌ 批量同步订单状态异常",
            system_type=request.system_type.value,
            error=str(e)
        )
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量同步订单状态失败: {str(e)}"
        )


@router.get("/sync/rules")
async def get_sync_rules(
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    获取同步规则
    """
    tenant, user = auth
    
    logger.info(
        "🔍 获取同步规则",
        tenant_id=tenant.id,
        user_id=user.id
    )
    
    try:
        # 创建多平台同步服务
        sync_service = MultiPlatformSyncService(db)
        
        # 获取同步规则
        sync_rules = sync_service.sync_rules
        
        return {
            "success": True,
            "sync_rules": sync_rules,
            "total_count": len(sync_rules),
            "message": "获取同步规则成功"
        }
        
    except Exception as e:
        logger.error(
            "❌ 获取同步规则异常",
            error=str(e)
        )
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取同步规则失败: {str(e)}"
        )


@router.get("/sync/tasks")
async def get_sync_tasks(
    status: Optional[SyncStatus] = Query(None, description="任务状态"),
    priority: Optional[SyncPriorityEnum] = Query(None, description="优先级"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    获取同步任务列表
    """
    tenant, user = auth
    
    logger.info(
        "🔍 获取同步任务列表",
        status=status.value if status else None,
        priority=priority.value if priority else None,
        limit=limit,
        tenant_id=tenant.id,
        user_id=user.id
    )
    
    try:
        # 创建多平台同步服务
        sync_service = MultiPlatformSyncService(db)
        
        # 获取同步任务
        tasks = list(sync_service.sync_tasks.values())
        
        # 过滤任务
        if status:
            tasks = [t for t in tasks if t.status == status]
        if priority:
            tasks = [t for t in tasks if t.priority.value == priority.value]
        
        # 限制数量
        tasks = tasks[:limit]
        
        # 转换为字典格式
        task_data = []
        for task in tasks:
            task_data.append({
                "task_id": task.task_id,
                "order_id": task.order_id,
                "system_type": task.system_type.value,
                "sync_direction": task.sync_direction.value,
                "priority": task.priority.value,
                "status": task.status.value,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
                "retry_count": task.retry_count,
                "max_retries": task.max_retries,
                "error_message": task.error_message,
                "metadata": task.metadata
            })
        
        return {
            "success": True,
            "tasks": task_data,
            "total_count": len(task_data),
            "message": "获取同步任务列表成功"
        }
        
    except Exception as e:
        logger.error(
            "❌ 获取同步任务列表异常",
            error=str(e)
        )
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取同步任务列表失败: {str(e)}"
        )


@router.get("/sync/tasks/{task_id}")
async def get_sync_task(
    task_id: str = Path(..., description="任务ID"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    获取同步任务详情
    """
    tenant, user = auth
    
    logger.info(
        "🔍 获取同步任务详情",
        task_id=task_id,
        tenant_id=tenant.id,
        user_id=user.id
    )
    
    try:
        # 创建多平台同步服务
        sync_service = MultiPlatformSyncService(db)
        
        # 获取同步任务
        task = sync_service.sync_tasks.get(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"同步任务不存在: {task_id}"
            )
        
        # 转换为字典格式
        task_data = {
            "task_id": task.task_id,
            "order_id": task.order_id,
            "system_type": task.system_type.value,
            "sync_direction": task.sync_direction.value,
            "priority": task.priority.value,
            "status": task.status.value,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "retry_count": task.retry_count,
            "max_retries": task.max_retries,
            "error_message": task.error_message,
            "metadata": task.metadata
        }
        
        return {
            "success": True,
            "task": task_data,
            "message": "获取同步任务详情成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "❌ 获取同步任务详情异常",
            task_id=task_id,
            error=str(e)
        )
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取同步任务详情失败: {str(e)}"
        )
