"""
审计字段基类
提供统一的审计字段定义
"""

from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, declared_attr
from app.core.database import Base


class AuditMixin:
    """
    审计字段混入类
    提供统一的审计字段定义，包括时间、用户和状态审计
    """
    
    # 时间审计字段
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False,
        comment="创建时间"
    )
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )
    
    # 用户审计字段
    created_by = Column(
        Integer, 
        ForeignKey("users.id"), 
        nullable=True,
        comment="创建用户ID"
    )
    updated_by = Column(
        Integer, 
        ForeignKey("users.id"), 
        nullable=True,
        comment="更新用户ID"
    )
    
    # 状态审计字段
    is_active = Column(
        Boolean, 
        default=True, 
        nullable=False,
        comment="是否激活"
    )
    is_deleted = Column(
        Boolean, 
        default=False, 
        nullable=False,
        comment="是否软删除"
    )
    
    # 关系映射 - 移除backref避免冲突
    @declared_attr
    def creator(cls):
        return relationship(
            "User", 
            foreign_keys=[cls.created_by], 
            lazy="select"
        )
    
    @declared_attr
    def updater(cls):
        return relationship(
            "User", 
            foreign_keys=[cls.updated_by], 
            lazy="select"
        )


class TenantMixin:
    """
    租户隔离混入类
    提供租户隔离字段
    """
    
    tenant_id = Column(
        Integer, 
        ForeignKey("tenants.id"), 
        nullable=False, 
        index=True,
        comment="租户ID"
    )
    
    # 关系映射 - 移除backref避免冲突
    @declared_attr
    def tenant(cls):
        return relationship(
            "Tenant", 
            lazy="select"
        )


class VersionMixin:
    """
    版本控制混入类
    提供版本控制字段
    """
    
    version = Column(
        Integer, 
        default=1, 
        nullable=False,
        comment="版本号"
    )


class FullAuditMixin(AuditMixin, TenantMixin):
    """
    完整审计混入类
    包含所有审计字段：时间、用户、状态、租户
    """
    pass


class FullAuditWithVersionMixin(AuditMixin, TenantMixin, VersionMixin):
    """
    完整审计+版本控制混入类
    包含所有审计字段和版本控制
    """
    pass
