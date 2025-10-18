"""
Printify Order model
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class PrintifyOrder(Base):
    __tablename__ = "printify_orders"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    external_system_id = Column(Integer, ForeignKey("external_systems.id"), nullable=False, index=True)
    external_order_id = Column(String(255), nullable=False, index=True)
    scm_order_id = Column(Integer, ForeignKey("scm_orders.id"), nullable=True, index=True)
    
    # Order information
    status = Column(String(50), nullable=False, default="pending")
    total_price = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(10), nullable=True, default="USD")
    
    # Customer information
    customer_email = Column(String(255), nullable=True)
    customer_name = Column(String(255), nullable=True)
    
    # Address information
    shipping_address = Column(JSON, nullable=True)
    billing_address = Column(JSON, nullable=True)
    
    # Printify specific data
    printify_data = Column(JSON, nullable=True)
    external_data = Column(JSON, nullable=True)
    
    # Tracking information
    tracking_number = Column(String(255), nullable=True)
    tracking_url = Column(String(500), nullable=True)
    carrier = Column(String(100), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    shipped_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="printify_orders")
    external_system = relationship("ExternalSystem")
    scm_order = relationship("SCMOrder", back_populates="printify_orders")







