"""
同步配置和任务记录模型
用于管理租户的批处理服务配置和状态跟踪
"""

from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Text, JSON, Enum, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class SyncType(enum.Enum):
    """同步类型"""
    PRODUCTS = "PRODUCTS"
    ORDERS = "ORDERS"
    CUSTOMERS = "CUSTOMERS"
    INVENTORY = "INVENTORY"


class SyncFrequency(enum.Enum):
    """同步频率"""
    MANUAL = "MANUAL"           # 手动触发
    HOURLY = "HOURLY"          # 每小时
    DAILY = "DAILY"            # 每天
    WEEKLY = "WEEKLY"          # 每周
    CUSTOM = "CUSTOM"          # 自定义间隔


class SyncJobStatus(enum.Enum):
    """同步任务状态"""
    PENDING = "PENDING"         # 等待中
    RUNNING = "RUNNING"         # 执行中
    SUCCESS = "SUCCESS"         # 成功
    FAILED = "FAILED"           # 失败
    CANCELLED = "CANCELLED"     # 已取消


class SyncConfig(Base):
    """同步配置模型"""
    __tablename__ = "sync_configs"

    id = Column(Integer, primary_key=True, index=True)
    
    # 关联信息
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    external_system_id = Column(Integer, ForeignKey("external_systems.id"), nullable=False)
    
    # 配置信息
    name = Column(String(255), nullable=False)  # 配置名称，如 "产品同步配置"
    sync_type = Column(Enum(SyncType), nullable=False)  # 同步类型
    is_active = Column(Boolean, default=True, nullable=False)  # 是否启用
    
    # 同步频率配置
    frequency = Column(Enum(SyncFrequency), nullable=False, default=SyncFrequency.MANUAL)
    custom_interval_minutes = Column(Integer, nullable=True)  # 自定义间隔（分钟）
    
    # 同步参数
    sync_params = Column(JSON, nullable=False, default=dict)  # 同步参数，如增量同步、最大数量等
    
    # 时间配置
    start_time = Column(DateTime(timezone=True), nullable=True)  # 开始时间（用于定时任务）
    last_run_at = Column(DateTime(timezone=True), nullable=True)  # 上次运行时间
    next_run_at = Column(DateTime(timezone=True), nullable=True)  # 下次运行时间
    
    # 统计信息
    total_runs = Column(Integer, default=0, nullable=False)  # 总运行次数
    successful_runs = Column(Integer, default=0, nullable=False)  # 成功次数
    failed_runs = Column(Integer, default=0, nullable=False)  # 失败次数
    total_items_processed = Column(Integer, default=0, nullable=False)  # 总处理项目数
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    tenant = relationship("Tenant", back_populates="sync_configs")
    external_system = relationship("ExternalSystem", back_populates="sync_configs")
    sync_jobs = relationship("SyncJob", back_populates="sync_config", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_sync_configs_tenant_type', 'tenant_id', 'sync_type'),
        Index('idx_sync_configs_active', 'is_active'),
        Index('idx_sync_configs_next_run', 'next_run_at'),
    )


class SyncJob(Base):
    """同步任务执行记录"""
    __tablename__ = "sync_jobs"

    id = Column(Integer, primary_key=True, index=True)
    
    # 关联信息
    sync_config_id = Column(Integer, ForeignKey("sync_configs.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    
    # 任务信息
    job_id = Column(String(255), nullable=True)  # Celery 任务ID
    status = Column(Enum(SyncJobStatus), nullable=False, default=SyncJobStatus.PENDING)
    
    # 执行信息
    started_at = Column(DateTime(timezone=True), nullable=True)  # 开始时间
    completed_at = Column(DateTime(timezone=True), nullable=True)  # 完成时间
    duration_seconds = Column(Integer, nullable=True)  # 执行时长（秒）
    
    # 结果信息
    items_processed = Column(Integer, default=0, nullable=False)  # 处理项目数
    items_created = Column(Integer, default=0, nullable=False)  # 创建项目数
    items_updated = Column(Integer, default=0, nullable=False)  # 更新项目数
    items_failed = Column(Integer, default=0, nullable=False)  # 失败项目数
    
    # 错误信息
    error_message = Column(Text, nullable=True)  # 错误信息
    error_details = Column(JSON, nullable=True)  # 详细错误信息
    
    # 进度信息
    progress_percentage = Column(Integer, default=0, nullable=False)  # 进度百分比
    progress_message = Column(String(500), nullable=True)  # 进度消息
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    sync_config = relationship("SyncConfig", back_populates="sync_jobs")
    tenant = relationship("Tenant", back_populates="sync_jobs")
    
    # 索引
    __table_args__ = (
        Index('idx_sync_jobs_tenant_status', 'tenant_id', 'status'),
        Index('idx_sync_jobs_config_status', 'sync_config_id', 'status'),
        Index('idx_sync_jobs_created', 'created_at'),
    )
