"""
External data model - stores data from external systems
"""

from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Text, JSON, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class ExternalDataType(enum.Enum):
    """Types of external data"""
    PRODUCT = "product"
    ORDER = "order"
    INVENTORY = "inventory"
    CUSTOMER = "customer"
    SHIPPING = "shipping"
    PAYMENT = "payment"
    WEBHOOK = "webhook"
    # Add more as needed


class ExternalData(Base):
    __tablename__ = "external_data"

    id = Column(Integer, primary_key=True, index=True)
    
    # External system identification
    external_system_id = Column(Integer, ForeignKey("external_systems.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    
    # Data identification
    data_type = Column(Enum(ExternalDataType), nullable=False)
    external_id = Column(String, nullable=False)  # ID in external system
    external_reference = Column(String, nullable=True)  # Additional reference (e.g., order number)
    
    # Data content
    raw_data = Column(JSON, nullable=False)  # Raw data from external system
    processed_data = Column(JSON, nullable=True)  # Processed/normalized data
    
    # Status and processing
    is_active = Column(Boolean, default=True)
    is_processed = Column(Boolean, default=False)
    processing_status = Column(String, default="pending")  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)
    
    # Sync information
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    sync_version = Column(Integer, default=1)  # Version for conflict resolution
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    external_system = relationship("ExternalSystem")
    tenant = relationship("Tenant")
    
    # Ensure unique external_system + external_id + data_type combination
    # This will be handled by Alembic migration
