"""
Order model
"""

from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Text, JSON, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

from app.core.database import Base


class OrderStatus(PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"
    FAILED = "failed"
    REFUNDED = "refunded"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    
    # External system identification (optional - not all orders come from external systems)
    external_system_id = Column(Integer, ForeignKey("external_systems.id"), nullable=True)
    external_order_id = Column(String, nullable=True)  # Order ID in external system
    
    # External system specific identifiers
    external_order_number = Column(String, nullable=True)
    external_order_name = Column(String, nullable=True)
    
    # Order information
    status = Column(String, default=OrderStatus.PENDING.value, index=True)
    total_amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    
    # Customer information
    customer_email = Column(String, nullable=False)
    customer_name = Column(String, nullable=True)
    customer_phone = Column(String, nullable=True)
    
    # Shipping information
    shipping_address = Column(JSON, nullable=False)
    billing_address = Column(JSON, nullable=True)
    
    # Order items and details
    line_items = Column(JSON, nullable=False)
    
    # Processing information
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    last_retry_at = Column(DateTime(timezone=True), nullable=True)
    
    # Fulfillment tracking
    tracking_number = Column(String, nullable=True)
    tracking_url = Column(String, nullable=True)
    fulfillment_status = Column(String, nullable=True)
    
    # Timestamps
    order_date = Column(DateTime(timezone=True), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    fulfilled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Foreign keys
    customer_id = Column(Integer, ForeignKey("customers.id"))

    # Relationships
    customer = relationship("Customer", back_populates="orders")
    external_system = relationship("ExternalSystem")
