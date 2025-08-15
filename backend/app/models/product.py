"""
Product model - represents products from external systems
"""

from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text, JSON, Numeric, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    
    # Tenant identification
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    
    # External system identification (optional - not all products come from external systems)
    external_system_id = Column(Integer, ForeignKey("external_systems.id"), nullable=True)
    external_product_id = Column(String, nullable=True)  # Product ID in external system
    
    # Product identifiers
    title = Column(String, nullable=False)
    handle = Column(String(255), nullable=True)  # URL handle for Shopify products
    description = Column(Text, nullable=True)
    
    # Product details
    product_type = Column(String(100), nullable=True)  # Product type/category
    vendor = Column(String(100), nullable=True)  # Brand/vendor
    tags = Column(JSON, nullable=True)  # List of tags
    images = Column(JSON, nullable=True)  # List of image URLs
    variants = Column(JSON, nullable=True)  # Product variants
    
    # Pricing
    price = Column(Numeric(10, 2), nullable=True)
    compare_at_price = Column(Numeric(10, 2), nullable=True)
    
    # Product status
    is_active = Column(Boolean, default=True)
    is_available = Column(Boolean, default=True)
    status = Column(String, nullable=True)  # Product status (active, draft, archived, etc.)
    
    # Inventory tracking
    tracks_inventory = Column(Boolean, default=True)
    has_out_of_stock_variants = Column(Boolean, default=False)
    has_only_default_variant = Column(Boolean, default=True)
    total_inventory = Column(Integer, nullable=True)
    
    # Product metadata
    seo = Column(JSON, nullable=True)
    online_store_url = Column(String(500), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    
    # External system specific data
    external_data = Column(JSON, nullable=True)  # Store system-specific data
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Sync information
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="products")
    external_system = relationship("ExternalSystem")
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_products_tenant_status', 'tenant_id', 'status'),
        Index('idx_products_handle', 'handle'),
        Index('idx_products_vendor', 'vendor'),
        Index('idx_products_type', 'product_type'),
        Index('idx_products_inventory', 'total_inventory'),
        Index('idx_products_published', 'published_at'),
    )
