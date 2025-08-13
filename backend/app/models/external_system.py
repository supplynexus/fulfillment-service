"""
External system integration model
"""

from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Text, JSON, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class ExternalSystemType(enum.Enum):
    """External system types"""
    SHOPIFY = "shopify"
    PRINTIFY = "printify"
    AMAZON = "amazon"
    YAHOO = "yahoo"
    RAKUTEN = "rakuten"
    # Add more as needed


class ExternalSystem(Base):
    __tablename__ = "external_systems"

    id = Column(Integer, primary_key=True, index=True)
    
    # System identification
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    system_type = Column(Enum(ExternalSystemType), nullable=False)
    name = Column(String, nullable=False)  # Human readable name (e.g., "Main Shopify Store", "Printify Production")
    
    # External system configuration
    external_id = Column(String, nullable=True)  # External system's ID for this connection
    base_url = Column(String, nullable=True)  # API base URL
    webhook_url = Column(String, nullable=True)  # Webhook endpoint URL
    
    # Authentication credentials (encrypted)
    # Format: {
    #   "api_key": "encrypted_value",
    #   "api_secret": "encrypted_value", 
    #   "access_token": "encrypted_value",
    #   "refresh_token": "encrypted_value",
    #   "shop_id": "shop_id",
    #   "store_url": "store_url"
    # }
    credentials = Column(JSON, nullable=False, default=dict)
    
    # Configuration and settings
    settings = Column(JSON, nullable=False, default=dict)  # System-specific settings
    is_active = Column(Boolean, default=True)
    sync_enabled = Column(Boolean, default=True)
    webhook_enabled = Column(Boolean, default=True)
    
    # Sync configuration
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_product_sync_at = Column(DateTime(timezone=True), nullable=True)  # Last product sync time
    sync_interval_minutes = Column(Integer, default=60)  # How often to sync
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="external_systems")
    external_data = relationship("ExternalData", back_populates="external_system")
    customers = relationship("Customer", back_populates="external_system")
    suppliers = relationship("Supplier", back_populates="external_system")
