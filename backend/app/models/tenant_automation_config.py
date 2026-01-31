"""
Tenant automation config model - 租户自动化配置表
"""

from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class TenantAutomationConfig(Base):
    """租户自动化配置表 - 存储每个租户对每个步骤的自动化配置"""
    __tablename__ = "tenant_automation_configs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    step_key = Column(String(100), nullable=False, index=True)  # 关联到 automation_steps.step_key
    
    # 自动化配置
    is_enabled = Column(Boolean, default=False)  # 是否启用自动化
    schedule = Column(String(50), nullable=True)  # Cron表达式，如 "*/30 * * * *"
    schedule_seconds = Column(Integer, nullable=True)  # 或使用秒数（兼容现有，如 1800 表示30分钟）
    
    # 任务参数（JSON对象，传递给Celery任务的参数）
    task_params = Column(JSON, nullable=True, default=dict)
    
    # 外部系统过滤（可选，用于多外部系统场景）
    external_system_types = Column(JSON, nullable=True)  # ["SHOPIFY"] 或 ["SHOPIFY", "PRINTIFY"]
    external_system_ids = Column(JSON, nullable=True)  # 特定外部系统ID列表（hashids）
    
    # 状态
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    last_run_status = Column(String(20), nullable=True)  # "success", "failed", "running"
    last_run_error = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    tenant = relationship("Tenant", back_populates="automation_configs")
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'step_key', name='uq_tenant_step'),
    )




