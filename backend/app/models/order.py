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

    # Order items relationship (moved to order_items table)
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

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


class OrderItem(Base):
    """Order line items - individual SKUs in an order"""
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    
    # Tenant and order reference
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Core system SKU mapping (nullable for unmatched items)
    core_product_id = Column(Integer, ForeignKey("products.id"), nullable=True, index=True)
    core_variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True, index=True)
    
    # External system SKU tracking
    external_product_id = Column(String(100), nullable=True, index=True)
    external_variant_id = Column(String(100), nullable=True, index=True)
    
    # Item details
    sku = Column(String(100), nullable=True, index=True)
    title = Column(String(255), nullable=True)
    variant_title = Column(String(255), nullable=True)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=True)
    total_price = Column(Numeric(10, 2), nullable=True)
    discount = Column(Numeric(10, 2), nullable=True)
    tax = Column(Numeric(10, 2), nullable=True)
    fulfillment_status = Column(String(50), nullable=True)
    item_metadata = Column(JSON, nullable=True)  # Additional item attributes
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    order = relationship("Order", back_populates="items")
    core_product = relationship("Product")
    core_variant = relationship("ProductVariant")
