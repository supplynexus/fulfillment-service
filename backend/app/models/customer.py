"""
Customer model
"""

from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    
    # Shopify store details
    shopify_store_url = Column(String, nullable=False)
    shopify_access_token = Column(String, nullable=False)
    shopify_api_key = Column(String, nullable=True)
    shopify_api_secret = Column(String, nullable=True)
    
    # Printify details
    printify_api_token = Column(String, nullable=False)
    printify_shop_id = Column(String, nullable=True)
    
    # Business information
    business_name = Column(String, nullable=True)
    contact_person = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    
    # Status and configuration
    is_active = Column(Boolean, default=True)
    webhook_enabled = Column(Boolean, default=True)
    auto_fulfillment = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Foreign keys
    owner_id = Column(Integer, ForeignKey("users.id"))

    # Relationships
    owner = relationship("User", back_populates="customers")
    orders = relationship("Order", back_populates="customer")
