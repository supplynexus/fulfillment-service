"""
Automation step model - 系统预定义的自动化步骤模板
"""

from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func

from app.core.database import Base


class AutomationStep(Base):
    """自动化步骤定义表 - 存储系统预定义的步骤模板"""
    __tablename__ = "automation_steps"

    id = Column(Integer, primary_key=True, index=True)
    step_key = Column(String(100), unique=True, nullable=False, index=True)  # 如: "sync_shopify_to_core"
    name = Column(String(200), nullable=False)  # 显示名称，如: "Shopify订单同步到核心订单表"
    description = Column(Text, nullable=True)  # 步骤描述
    category = Column(String(50), nullable=False, index=True)  # "order_sync", "order_processing", "status_sync"
    
    # 所需外部系统（JSON数组，如 ["SHOPIFY"] 或 ["SHOPIFY", "PRINTIFY"]）
    required_external_systems = Column(JSON, nullable=True)
    
    # Celery任务配置
    celery_task_name = Column(String(200), nullable=True)  # 对应的Celery任务名，如 "app.tasks.order_automation_tasks.sync_shopify_orders_to_core"
    default_schedule = Column(String(50), nullable=True)  # 默认cron表达式，如 "*/30 * * * *"
    default_enabled = Column(Boolean, default=False)  # 默认是否启用
    is_manual_only = Column(Boolean, default=False)  # 是否仅支持手动触发（不支持自动化）
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())




