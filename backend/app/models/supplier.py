"""
Supplier model - represents the vendor/supplier for a User+Tenant combination
"""

from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    
    # Supplier identification
    supplier_id = Column(String, unique=True, index=True, nullable=False)  # External supplier ID
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    
    # Supplier type
    supplier_type = Column(String, nullable=False, default="print")  # "print", "logistics", etc.
    
    # Business information
    business_name = Column(String, nullable=True)
    contact_person = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    
    # External system integration
    external_data = Column(JSON, nullable=True)  # Store external system data (Printify, etc.)
    
    # API credentials (encrypted)
    api_credentials = Column(JSON, nullable=True)  # Store encrypted API credentials
    
    # Status and configuration
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Foreign keys - Supplier belongs to a specific User+Tenant combination
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)

    # Relationships
    user = relationship("User", back_populates="suppliers")
    tenant = relationship("Tenant", back_populates="suppliers")
