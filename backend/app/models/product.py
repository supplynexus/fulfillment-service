"""
Product model
"""

from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text, JSON, Numeric
from sqlalchemy.sql import func

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    
    # Product identifiers
    printify_product_id = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Product details
    tags = Column(JSON, nullable=True)  # List of tags
    images = Column(JSON, nullable=True)  # List of image URLs
    variants = Column(JSON, nullable=True)  # Product variants
    
    # Pricing
    price = Column(Numeric(10, 2), nullable=True)
    compare_at_price = Column(Numeric(10, 2), nullable=True)
    
    # Product status
    is_active = Column(Boolean, default=True)
    is_available = Column(Boolean, default=True)
    
    # Print provider information
    print_provider_id = Column(String, nullable=True)
    print_areas = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Sync information
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
