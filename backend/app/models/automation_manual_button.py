"""
Automation manual button model - 手动按钮配置表
"""

from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class AutomationManualButton(Base):
    """手动按钮配置表 - 存储每个步骤支持的手动按钮"""
    __tablename__ = "automation_manual_buttons"

    id = Column(Integer, primary_key=True, index=True)
    step_key = Column(String(100), nullable=False, index=True)  # 关联到 automation_steps.step_key
    button_key = Column(String(100), nullable=False)  # 如: "sync_to_core"
    button_label = Column(String(100), nullable=False)  # 显示文本，如: "同步到核心订单"
    button_action = Column(String(200), nullable=False)  # API路径，如: "/api/v1/shopify-orders/{id}/sync-to-core"
    http_method = Column(String(10), default="POST")
    is_recommended = Column(Boolean, default=False)  # 是否推荐使用
    is_deprecated = Column(Boolean, default=False)  # 是否已废弃
    deprecated_reason = Column(Text, nullable=True)  # 废弃原因
    page_path = Column(String(200), nullable=True)  # 前端页面路径，如: "/external-systems/shopify/synced-orders"
    order = Column(Integer, default=0)  # 按钮显示顺序
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('step_key', 'button_key', name='uq_step_button'),
    )















