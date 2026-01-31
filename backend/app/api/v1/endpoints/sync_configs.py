"""
同步配置管理 API 端点
用于管理租户的批处理服务配置
"""

from typing import Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc, func, case
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from app.core.database import get_async_db
from app.core.tenant_auth_dependency import verify_tenant_auth
from app.models.tenant import Tenant
from app.models.user import User
from app.models.sync_config import SyncConfig, SyncJob, SyncType, SyncFrequency, SyncJobStatus
from app.models.external_system import ExternalSystem, ExternalSystemType

router = APIRouter()


# Pydantic 模型
class SyncConfigCreate(BaseModel):
    """创建同步配置"""
    external_system_id: int = Field(..., description="外部系统ID")
    name: str = Field(..., description="配置名称")
    sync_type: SyncType = Field(..., description="同步类型")
    is_active: bool = Field(True, description="是否启用")
    frequency: SyncFrequency = Field(SyncFrequency.MANUAL, description="同步频率")
    custom_interval_minutes: Optional[int] = Field(None, description="自定义间隔（分钟）")
    sync_params: dict = Field(default_factory=dict, description="同步参数")
    start_time: Optional[datetime] = Field(None, description="开始时间")


class SyncConfigUpdate(BaseModel):
    """更新同步配置"""
    name: Optional[str] = Field(None, description="配置名称")
    is_active: Optional[bool] = Field(None, description="是否启用")
    frequency: Optional[SyncFrequency] = Field(None, description="同步频率")
    custom_interval_minutes: Optional[int] = Field(None, description="自定义间隔（分钟）")
    sync_params: Optional[dict] = Field(None, description="同步参数")
    start_time: Optional[datetime] = Field(None, description="开始时间")


class SyncConfigResponse(BaseModel):
    """同步配置响应"""
    id: int
    tenant_id: int
    external_system_id: int
    name: str
    sync_type: SyncType
    is_active: bool
    frequency: SyncFrequency
    custom_interval_minutes: Optional[int]
    sync_params: dict
    start_time: Optional[datetime]
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    total_runs: int
    successful_runs: int
    failed_runs: int
    total_items_processed: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    # 外部系统信息
    external_system_name: Optional[str] = None
    external_system_type: Optional[str] = None
    
    class Config:
        from_attributes = True


class SyncJobResponse(BaseModel):
    """同步任务响应"""
    id: int
    sync_config_id: int
    tenant_id: int
    job_id: Optional[str]
    status: SyncJobStatus
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    items_processed: int
    items_created: int
    items_updated: int
    items_failed: int
    error_message: Optional[str]
    progress_percentage: int
    progress_message: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class SyncStatsResponse(BaseModel):
    """同步统计响应"""
    total_configs: int
    active_configs: int
    total_jobs: int
    successful_jobs: int
    failed_jobs: int
    running_jobs: int
    total_items_processed: int
    last_sync_time: Optional[datetime]


# API 端点
@router.get("/", response_model=List[SyncConfigResponse])
async def get_sync_configs(
    tenant_id: int = Query(..., description="租户ID"),
    sync_type: Optional[SyncType] = Query(None, description="同步类型过滤"),
    is_active: Optional[bool] = Query(None, description="是否启用过滤"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(10, ge=1, le=100, description="返回数量"),
    db: Session = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> Any:
    """
    获取租户的同步配置列表
    """
    try:
        tenant, user = auth
        if tenant.id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
        
        # 构建查询条件
        conditions = [SyncConfig.tenant_id == tenant_id]
        if sync_type:
            conditions.append(SyncConfig.sync_type == sync_type)
        if is_active is not None:
            conditions.append(SyncConfig.is_active == is_active)
        
        # 查询同步配置
        result = await db.execute(
            select(SyncConfig, ExternalSystem.name.label("external_system_name"), 
                   ExternalSystem.system_type.label("external_system_type"))
            .join(ExternalSystem, SyncConfig.external_system_id == ExternalSystem.id)
            .where(and_(*conditions))
            .order_by(desc(SyncConfig.updated_at))
            .offset(skip)
            .limit(limit)
        )
        
        configs = []
        for row in result:
            config_dict = {
                **row[0].__dict__,
                "external_system_name": row[1],
                "external_system_type": row[2].value if row[2] else None
            }
            configs.append(SyncConfigResponse(**config_dict))
        
        return configs
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving sync configs: {str(e)}"
        )


@router.post("/", response_model=SyncConfigResponse)
async def create_sync_config(
    tenant_id: int = Query(..., description="租户ID"),
    config: SyncConfigCreate = None,
    db: Session = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> Any:
    """
    创建新的同步配置
    """
    try:
        tenant, user = auth
        if tenant.id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
        
        # 验证外部系统是否存在且属于该租户
        external_system = await db.execute(
            select(ExternalSystem).where(
                ExternalSystem.id == config.external_system_id,
                ExternalSystem.tenant_id == tenant_id
            )
        )
        external_system = external_system.scalar_one_or_none()
        
        if not external_system:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="External system not found"
            )
        
        # 检查是否已存在相同类型的配置
        existing_config = await db.execute(
            select(SyncConfig).where(
                SyncConfig.tenant_id == tenant_id,
                SyncConfig.external_system_id == config.external_system_id,
                SyncConfig.sync_type == config.sync_type
            )
        )
        existing_config = existing_config.scalar_one_or_none()
        
        if existing_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sync config for {config.sync_type.value} already exists for this external system"
            )
        
        # 计算下次运行时间
        next_run_at = None
        if config.frequency != SyncFrequency.MANUAL and config.start_time:
            if config.frequency == SyncFrequency.HOURLY:
                next_run_at = config.start_time
            elif config.frequency == SyncFrequency.DAILY:
                next_run_at = config.start_time
            elif config.frequency == SyncFrequency.CUSTOM and config.custom_interval_minutes:
                next_run_at = datetime.utcnow() + timedelta(minutes=config.custom_interval_minutes)
        
        # 创建同步配置
        sync_config = SyncConfig(
            tenant_id=tenant_id,
            external_system_id=config.external_system_id,
            name=config.name,
            sync_type=config.sync_type,
            is_active=config.is_active,
            frequency=config.frequency,
            custom_interval_minutes=config.custom_interval_minutes,
            sync_params=config.sync_params,
            start_time=config.start_time,
            next_run_at=next_run_at
        )
        
        db.add(sync_config)
        await db.commit()
        await db.refresh(sync_config)
        
        # 返回响应
        result = await db.execute(
            select(SyncConfig, ExternalSystem.name.label("external_system_name"), 
                   ExternalSystem.system_type.label("external_system_type"))
            .join(ExternalSystem, SyncConfig.external_system_id == ExternalSystem.id)
            .where(SyncConfig.id == sync_config.id)
        )
        
        row = result.first()
        config_dict = {
            **row[0].__dict__,
            "external_system_name": row[1],
            "external_system_type": row[2].value if row[2] else None
        }
        
        return SyncConfigResponse(**config_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating sync config: {str(e)}"
        )


@router.put("/{config_id}", response_model=SyncConfigResponse)
async def update_sync_config(
    config_id: int,
    tenant_id: int = Query(..., description="租户ID"),
    config: SyncConfigUpdate = None,
    db: Session = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> Any:
    """
    更新同步配置
    """
    try:
        tenant, user = auth
        if tenant.id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
        
        # 获取现有配置
        sync_config = await db.execute(
            select(SyncConfig).where(
                SyncConfig.id == config_id,
                SyncConfig.tenant_id == tenant_id
            )
        )
        sync_config = sync_config.scalar_one_or_none()
        
        if not sync_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sync config not found"
            )
        
        # 更新配置
        update_data = config.dict(exclude_unset=True)
        
        # 计算下次运行时间
        if "frequency" in update_data or "start_time" in update_data or "custom_interval_minutes" in update_data:
            frequency = update_data.get("frequency", sync_config.frequency)
            start_time = update_data.get("start_time", sync_config.start_time)
            custom_interval = update_data.get("custom_interval_minutes", sync_config.custom_interval_minutes)
            
            next_run_at = None
            if frequency != SyncFrequency.MANUAL and start_time:
                if frequency == SyncFrequency.HOURLY:
                    next_run_at = start_time
                elif frequency == SyncFrequency.DAILY:
                    next_run_at = start_time
                elif frequency == SyncFrequency.CUSTOM and custom_interval:
                    next_run_at = datetime.utcnow() + timedelta(minutes=custom_interval)
            
            update_data["next_run_at"] = next_run_at
        
        # 应用更新
        for field, value in update_data.items():
            setattr(sync_config, field, value)
        
        await db.commit()
        await db.refresh(sync_config)
        
        # 返回响应
        result = await db.execute(
            select(SyncConfig, ExternalSystem.name.label("external_system_name"), 
                   ExternalSystem.system_type.label("external_system_type"))
            .join(ExternalSystem, SyncConfig.external_system_id == ExternalSystem.id)
            .where(SyncConfig.id == sync_config.id)
        )
        
        row = result.first()
        config_dict = {
            **row[0].__dict__,
            "external_system_name": row[1],
            "external_system_type": row[2].value if row[2] else None
        }
        
        return SyncConfigResponse(**config_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating sync config: {str(e)}"
        )


@router.delete("/{config_id}")
async def delete_sync_config(
    config_id: int,
    tenant_id: int = Query(..., description="租户ID"),
    db: Session = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> Any:
    """
    删除同步配置
    """
    try:
        tenant, user = auth
        if tenant.id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
        
        # 获取配置
        sync_config = await db.execute(
            select(SyncConfig).where(
                SyncConfig.id == config_id,
                SyncConfig.tenant_id == tenant_id
            )
        )
        sync_config = sync_config.scalar_one_or_none()
        
        if not sync_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sync config not found"
            )
        
        # 删除配置（会级联删除相关的任务记录）
        await db.delete(sync_config)
        await db.commit()
        
        return {"message": "Sync config deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting sync config: {str(e)}"
        )


@router.post("/{config_id}/trigger")
async def trigger_sync(
    config_id: int,
    tenant_id: int = Query(..., description="租户ID"),
    db: Session = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> Any:
    """
    手动触发同步任务
    """
    try:
        tenant, user = auth
        if tenant.id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
        
        # 获取配置
        sync_config = await db.execute(
            select(SyncConfig).where(
                SyncConfig.id == config_id,
                SyncConfig.tenant_id == tenant_id
            )
        )
        sync_config = sync_config.scalar_one_or_none()
        
        if not sync_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sync config not found"
            )
        
        if not sync_config.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sync config is not active"
            )
        
        # 创建同步任务记录
        sync_job = SyncJob(
            sync_config_id=config_id,
            tenant_id=tenant_id,
            status=SyncJobStatus.PENDING
        )
        
        db.add(sync_job)
        await db.commit()
        await db.refresh(sync_job)
        
        # TODO: 这里应该启动实际的 Celery 任务
        # 暂时返回模拟的任务ID
        sync_job.job_id = f"task_{sync_job.id}"
        sync_job.status = SyncJobStatus.RUNNING
        sync_job.started_at = datetime.utcnow()
        await db.commit()
        
        return {
            "message": "Sync job triggered successfully",
            "job_id": sync_job.job_id,
            "sync_job_id": sync_job.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering sync: {str(e)}"
        )


@router.get("/{config_id}/jobs", response_model=List[SyncJobResponse])
async def get_sync_jobs(
    config_id: int,
    tenant_id: int = Query(..., description="租户ID"),
    status: Optional[SyncJobStatus] = Query(None, description="任务状态过滤"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(10, ge=1, le=100, description="返回数量"),
    db: Session = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> Any:
    """
    获取同步任务的执行历史
    """
    try:
        tenant, user = auth
        if tenant.id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
        
        # 验证配置存在
        sync_config = await db.execute(
            select(SyncConfig).where(
                SyncConfig.id == config_id,
                SyncConfig.tenant_id == tenant_id
            )
        )
        sync_config = sync_config.scalar_one_or_none()
        
        if not sync_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sync config not found"
            )
        
        # 构建查询条件
        conditions = [SyncJob.sync_config_id == config_id]
        if status:
            conditions.append(SyncJob.status == status)
        
        # 查询任务记录
        result = await db.execute(
            select(SyncJob)
            .where(and_(*conditions))
            .order_by(desc(SyncJob.created_at))
            .offset(skip)
            .limit(limit)
        )
        
        jobs = result.scalars().all()
        return [SyncJobResponse.from_orm(job) for job in jobs]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving sync jobs: {str(e)}"
        )


@router.get("/stats", response_model=SyncStatsResponse)
async def get_sync_stats(
    tenant_id: int = Query(..., description="租户ID"),
    db: Session = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> Any:
    """
    获取同步统计信息
    """
    try:
        tenant, user = auth
        if tenant.id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
        
        # 统计配置
        config_stats = await db.execute(
            select(
                func.count(SyncConfig.id).label("total_configs"),
                func.sum(case(SyncConfig.is_active, 1, 0)).label("active_configs")
            ).where(SyncConfig.tenant_id == tenant_id)
        )
        config_row = config_stats.first()
        
        # 统计任务
        job_stats = await db.execute(
            select(
                func.count(SyncJob.id).label("total_jobs"),
                func.sum(case(SyncJob.status == SyncJobStatus.SUCCESS, 1, 0)).label("successful_jobs"),
                func.sum(case(SyncJob.status == SyncJobStatus.FAILED, 1, 0)).label("failed_jobs"),
                func.sum(case(SyncJob.status == SyncJobStatus.RUNNING, 1, 0)).label("running_jobs"),
                func.sum(SyncJob.items_processed).label("total_items_processed")
            ).where(SyncJob.tenant_id == tenant_id)
        )
        job_row = job_stats.first()
        
        # 获取最后同步时间
        last_sync = await db.execute(
            select(SyncJob.completed_at)
            .where(
                SyncJob.tenant_id == tenant_id,
                SyncJob.status == SyncJobStatus.SUCCESS
            )
            .order_by(desc(SyncJob.completed_at))
            .limit(1)
        )
        last_sync_time = last_sync.scalar()
        
        return SyncStatsResponse(
            total_configs=config_row[0] or 0,
            active_configs=config_row[1] or 0,
            total_jobs=job_row[0] or 0,
            successful_jobs=job_row[1] or 0,
            failed_jobs=job_row[2] or 0,
            running_jobs=job_row[3] or 0,
            total_items_processed=job_row[4] or 0,
            last_sync_time=last_sync_time
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving sync stats: {str(e)}"
        )
