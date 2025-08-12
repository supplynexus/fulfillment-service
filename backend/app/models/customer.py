"""
Customer model - represents the client (buyer) for a User+Tenant combination
"""

from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    
    # Customer identification
    customer_id = Column(String, unique=True, index=True, nullable=False)  # External customer ID
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    
    # Customer type
    customer_type = Column(String, nullable=False, default="b2c")  # "b2c" or "b2b"
    
    # Business information
    business_name = Column(String, nullable=True)
    contact_person = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    
    # External system integration
    external_data = Column(JSON, nullable=True)  # Store external system data (Shopify, etc.)
    
    # Status and configuration
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Foreign keys - Customer belongs to a specific ExternalSystem
    external_system_id = Column(Integer, ForeignKey("external_systems.id"), nullable=False)

    # Relationships
    external_system = relationship("ExternalSystem", back_populates="customers")
