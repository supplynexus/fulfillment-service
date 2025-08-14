"""
同步状态和任务进度管理端点
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_async_db
from app.core.api_key_auth import require_permission
from app.models.api_key import ApiKey
from app.models.tenant import Tenant
from app.models.external_system import ExternalSystem, ExternalSystemType
from app.tasks.celery_app import celery_app
from sqlalchemy import select

router = APIRouter()


class TaskStatus(BaseModel):
    task_id: str
    status: str
    progress: Optional[int] = None
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SyncStatus(BaseModel):
    tenant_id: int
    system_type: str
    last_sync_at: Optional[datetime] = None
    is_active: bool
    sync_enabled: bool


class SyncSummary(BaseModel):
    total_tenants: int
    active_tenants: int
    last_sync_orders: Optional[datetime] = None
    last_sync_products: Optional[datetime] = None
    running_tasks: int
    failed_tasks: int


@router.get("/tasks/{task_id}", response_model=TaskStatus)
async def get_task_status(
    task_id: str,
    auth: tuple[ApiKey, Tenant] = Depends(require_permission("sync:read"))
):
    """
    获取任务状态
    """
    api_key, tenant = auth
    
    try:
        task = celery_app.AsyncResult(task_id)
        
        return TaskStatus(
            task_id=task_id,
            status=task.status,
            progress=task.info.get('progress') if task.info else None,
            result=task.result if task.ready() else None,
            error=str(task.info.get('error')) if task.info and 'error' in task.info else None,
            created_at=task.date_done if task.ready() else None,
            updated_at=task.date_done if task.ready() else None
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"任务不存在或无法获取状态: {str(e)}")


@router.get("/tasks", response_model=List[TaskStatus])
async def get_recent_tasks(
    limit: int = 20,
    auth: tuple[ApiKey, Tenant] = Depends(require_permission("sync:read"))
):
    """
    获取最近的任务列表
    """
    api_key, tenant = auth
    
    try:
        # 这里需要根据你的Celery配置来获取任务列表
        # 由于Celery没有直接提供获取所有任务的API，这里返回空列表
        # 实际实现可能需要使用Redis或其他存储来跟踪任务
        return []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


@router.get("/status", response_model=List[SyncStatus])
async def get_sync_status(
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[ApiKey, Tenant] = Depends(require_permission("sync:read"))
):
    """
    获取所有租户的同步状态
    """
    api_key, tenant = auth
    
    try:
        # 获取所有外部系统
        result = await db.execute(
            select(ExternalSystem).where(
                ExternalSystem.system_type == ExternalSystemType.SHOPIFY
            )
        )
        external_systems = result.scalars().all()
        
        sync_statuses = []
        for system in external_systems:
            sync_statuses.append(SyncStatus(
                tenant_id=system.tenant_id,
                system_type=system.system_type.value,
                last_sync_at=system.last_sync_at,
                is_active=system.is_active,
                sync_enabled=system.is_active  # 简化逻辑
            ))
        
        return sync_statuses
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取同步状态失败: {str(e)}")


@router.get("/summary", response_model=SyncSummary)
async def get_sync_summary(
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[ApiKey, Tenant] = Depends(require_permission("sync:read"))
):
    """
    获取同步摘要信息
    """
    api_key, tenant = auth
    
    try:
        # 获取所有外部系统
        result = await db.execute(
            select(ExternalSystem).where(
                ExternalSystem.system_type == ExternalSystemType.SHOPIFY
            )
        )
        external_systems = result.scalars().all()
        
        total_tenants = len(external_systems)
        active_tenants = len([s for s in external_systems if s.is_active])
        
        # 获取最新的同步时间
        last_sync_orders = None
        last_sync_products = None
        
        for system in external_systems:
            if system.last_sync_at:
                if last_sync_orders is None or system.last_sync_at > last_sync_orders:
                    last_sync_orders = system.last_sync_at
                if last_sync_products is None or system.last_sync_at > last_sync_products:
                    last_sync_products = system.last_sync_at
        
        # 这里可以添加获取运行中和失败任务数量的逻辑
        # 由于Celery的限制，这里使用占位符
        running_tasks = 0
        failed_tasks = 0
        
        return SyncSummary(
            total_tenants=total_tenants,
            active_tenants=active_tenants,
            last_sync_orders=last_sync_orders,
            last_sync_products=last_sync_products,
            running_tasks=running_tasks,
            failed_tasks=failed_tasks
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取同步摘要失败: {str(e)}")


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    auth: tuple[ApiKey, Tenant] = Depends(require_permission("sync:write"))
):
    """
    取消正在运行的任务
    """
    api_key, tenant = auth
    
    try:
        task = celery_app.AsyncResult(task_id)
        
        if task.status in ['PENDING', 'STARTED']:
            task.revoke(terminate=True)
            return {"message": "任务已取消", "task_id": task_id}
        else:
            raise HTTPException(status_code=400, detail="任务无法取消（已完成或失败）")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")


@router.post("/reset-sync-timestamp")
async def reset_sync_timestamp(
    tenant_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[ApiKey, Tenant] = Depends(require_permission("sync:write"))
):
    """
    重置同步时间戳（强制下次同步为完全重新同步）
    """
    api_key, tenant = auth
    
    try:
        from sqlalchemy import update
        
        # 构建更新条件
        update_condition = (
            ExternalSystem.system_type == ExternalSystemType.SHOPIFY,
            ExternalSystem.is_active == True
        )
        
        if tenant_id:
            update_condition = update_condition + (ExternalSystem.tenant_id == tenant_id,)
        
        # 重置同步时间戳
        await db.execute(
            update(ExternalSystem)
            .where(*update_condition)
            .values(last_sync_at=None)
        )
        await db.commit()
        
        return {
            "message": "同步时间戳已重置",
            "tenant_id": tenant_id or "all"
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"重置同步时间戳失败: {str(e)}")
