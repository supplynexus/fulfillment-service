"""
User-Tenant relationship model (many-to-many)
"""

from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class UserRole(enum.Enum):
    """User roles within a tenant"""
    OWNER = "owner"  # Tenant owner with full access
    ADMIN = "admin"  # Tenant administrator
    USER = "user"    # Regular user
    VIEWER = "viewer"  # Read-only access


class UserTenant(Base):
    __tablename__ = "user_tenants"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    
    # User role within this tenant
    role = Column(Enum(UserRole), nullable=False, default=UserRole.USER)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="user_tenants")
    tenant = relationship("Tenant", back_populates="user_tenants")
    
    class Config:
        # Ensure unique user-tenant combination
        __table_args__ = (
            # This will be handled by Alembic migration
        )
