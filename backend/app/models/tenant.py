"""
Tenant model for data isolation
"""

from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    display_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Configuration
    settings = Column(JSON, nullable=False, default=dict)  # Tenant-specific settings
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user_tenants = relationship("UserTenant", back_populates="tenant")
    api_keys = relationship("ApiKey", back_populates="tenant")
    external_systems = relationship("ExternalSystem", back_populates="tenant")
    external_data = relationship("ExternalData", back_populates="tenant")
    products = relationship("Product", back_populates="tenant")
    orders = relationship("Order", back_populates="tenant")
    sync_configs = relationship("SyncConfig", back_populates="tenant")
    sync_jobs = relationship("SyncJob", back_populates="tenant")
