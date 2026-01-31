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
    
    # Authentication keys for service-to-service communication
    public_key = Column(Text, nullable=True)  # Public key for asymmetric authentication
    key_id = Column(String(255), nullable=True, unique=True)  # Hashid for API protection
    key_type = Column(String(50), nullable=True, default="rsa")  # Key type (rsa, ed25519, etc.)
    key_size = Column(Integer, nullable=True, default=2048)  # Key size in bits
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user_tenants = relationship("UserTenant", back_populates="tenant")

    external_systems = relationship("ExternalSystem", back_populates="tenant")
    external_data = relationship("ExternalData", back_populates="tenant")
    products = relationship("Product", back_populates="tenant")
    orders = relationship("Order", back_populates="tenant")
    scm_orders = relationship("SCMOrder", back_populates="tenant")
    printify_orders = relationship("PrintifyOrder", back_populates="tenant")
    routing_rules = relationship("RoutingRule", back_populates="tenant")
    sync_configs = relationship("SyncConfig", back_populates="tenant")
    sync_jobs = relationship("SyncJob", back_populates="tenant")
    automation_configs = relationship("TenantAutomationConfig", back_populates="tenant")
    
    # New Product System Relationships
    products_new = relationship("Product", back_populates="tenant", foreign_keys="Product.tenant_id")
    product_dimensions = relationship("ProductDimension", back_populates="tenant")
    product_variants = relationship("ProductVariant", back_populates="tenant")
    variant_attributes = relationship("VariantAttribute", back_populates="tenant")
    barcode_types = relationship("BarcodeType", back_populates="tenant")
    variant_barcodes = relationship("VariantBarcode", back_populates="tenant")
    tags = relationship("Tag", back_populates="tenant")
    product_tags = relationship("ProductTag", back_populates="tenant")
    product_combinations = relationship("ProductCombination", back_populates="tenant")
    product_combination_items = relationship("ProductCombinationItem", back_populates="tenant")
    product_mappings = relationship("ProductMapping", back_populates="tenant")
    external_products = relationship("ExternalProduct", back_populates="tenant")