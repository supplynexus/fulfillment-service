"""
SCM Order model
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


class SCMOrderStatus(PyEnum):
    CREATED = "created"
    PROCESSING = "processing"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"
    FAILED = "failed"
    REFUNDED = "refunded"


class SCMOrder(Base):
    __tablename__ = "scm_orders"

    id = Column(Integer, primary_key=True, index=True)

    # Tenant identification
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)

    # Source order reference
    source_order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)

    # SCM system information
    target_system_type = Column(
        String, nullable=False
    )  # printify, custom_fulfillment, warehouse
    target_system_id = Column(String, nullable=True)  # Order ID in target system
    scm_order_number = Column(String, unique=True, nullable=True)

    # Order status
    status = Column(String, default=SCMOrderStatus.CREATED.value, index=True)
    fulfillment_status = Column(String, nullable=True)

    # Routing information
    routing_metadata = Column(JSON, nullable=True)  # Routing decision metadata
    routing_strategy = Column(String, nullable=True)  # auto, manual, hybrid

    # Order items and details
    line_items = Column(JSON, nullable=False)  # Items routed to this SCM
    total_amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")

    # Customer information (copied from source order)
    customer_email = Column(String, nullable=False)
    customer_name = Column(String, nullable=True)
    customer_phone = Column(String, nullable=True)

    # Shipping information
    shipping_address = Column(JSON, nullable=False)
    billing_address = Column(JSON, nullable=True)

    # Processing information
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    last_retry_at = Column(DateTime(timezone=True), nullable=True)

    # Fulfillment tracking
    tracking_number = Column(String, nullable=True)
    tracking_url = Column(String, nullable=True)

    # Shopify integration
    shopify_fulfillment_order_id = Column(String, nullable=True)
    shopify_fulfillment_id = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    fulfilled_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="scm_orders")
    source_order = relationship("Order", back_populates="scm_orders")


class RoutingRule(Base):
    __tablename__ = "routing_rules"

    id = Column(Integer, primary_key=True, index=True)

    # Tenant identification
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)

    # Rule information
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # Routing conditions
    conditions = Column(
        JSON, nullable=False
    )  # Product types, quantities, regions, etc.

    # Routing actions
    target_system_type = Column(String, nullable=False)
    target_system_id = Column(String, nullable=True)
    priority = Column(Integer, default=1)

    # Rule status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="routing_rules")


class RoutingStatus(Base):
    __tablename__ = "routing_status"

    id = Column(Integer, primary_key=True, index=True)

    # Tenant identification
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)

    # Order references
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    scm_order_id = Column(Integer, ForeignKey("scm_orders.id"), nullable=True)

    # Status information
    status = Column(String, nullable=False)  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # Routing metadata
    routing_metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant")
    order = relationship("Order")
    scm_order = relationship("SCMOrder")
