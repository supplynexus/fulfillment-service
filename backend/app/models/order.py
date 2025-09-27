"""
Order model
"""

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Numeric,
)
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

    # Tenant identification
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)

    # External system identification (optional - not all orders come from external systems)
    external_system_id = Column(
        Integer, ForeignKey("external_systems.id"), nullable=True
    )
    external_order_id = Column(String, nullable=True)  # Order ID in external system

    # External system specific identifiers
    external_order_number = Column(String, nullable=True)
    external_order_name = Column(String, nullable=True)

    # Order information
    order_number = Column(String, nullable=True)  # Human readable order number
    status = Column(String, default=OrderStatus.PENDING.value, index=True)
    total_amount = Column(Numeric(10, 2), nullable=False)
    subtotal_amount = Column(Numeric(10, 2), nullable=True)
    tax_amount = Column(Numeric(10, 2), nullable=True)
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

    # Shopify specific data (mixed model approach)
    shopify_raw_data = Column(JSON, nullable=True)  # Raw Shopify API response
    shopify_processed = Column(JSON, nullable=True)  # Processed Shopify data
    external_data = Column(JSON, nullable=True)  # Generic external system data

    # Shopify integration fields
    shopify_order_id = Column(
        String, nullable=True
    )  # Shopify order ID (gid://shopify/Order/xxx)
    shopify_fulfillment_order_id = Column(
        String, nullable=True
    )  # Shopify fulfillment order ID
    shopify_fulfillment_id = Column(String, nullable=True)  # Shopify fulfillment ID

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

    # Relationships
    tenant = relationship("Tenant", back_populates="orders")
    external_system = relationship("ExternalSystem")
    scm_orders = relationship("SCMOrder", back_populates="source_order")
