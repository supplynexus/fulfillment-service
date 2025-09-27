"""
Shopify Order Model
专门存储 Shopify 订单数据，贴近 Shopify GraphQL API 结构
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, Numeric, DateTime, ForeignKey, JSON, Index, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class ShopifyOrder(Base):
    """
    Shopify 订单表
    专门存储 Shopify 订单数据，贴近 Shopify GraphQL API 结构
    参考: https://shopify.dev/docs/api/admin-graphql/latest/objects/Order
    """
    __tablename__ = "shopify_orders"

    # 主键和租户
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Shopify 订单标识
    shopify_order_id = Column(String(100), nullable=False, index=True)  # Shopify GraphQL ID
    name = Column(String(50), nullable=True)  # 订单名称，如 #1021
    confirmation_number = Column(String(50), nullable=True)  # 客户可见的订单号
    
    # 订单状态
    financial_status = Column(String(50), nullable=True)  # 财务状态 (paid, pending, etc.)
    fulfillment_status = Column(String(50), nullable=True)  # 履行状态 (fulfilled, partial, etc.)
    confirmed = Column(Boolean, nullable=False, default=False)  # 是否确认
    closed = Column(Boolean, nullable=False, default=False)  # 是否关闭
    cancelled = Column(Boolean, nullable=False, default=False)  # 是否取消
    
    # 货币和价格
    currency_code = Column(String(10), nullable=True)  # 货币代码 (USD, CAD, etc.)
    total_price = Column(Numeric(10, 2), nullable=True)  # 总价
    subtotal_price = Column(Numeric(10, 2), nullable=True)  # 小计
    total_tax = Column(Numeric(10, 2), nullable=True)  # 税费
    total_shipping = Column(Numeric(10, 2), nullable=True)  # 运费
    
    # 订单信息
    tags = Column(JSON, nullable=True)  # 标签数组
    note = Column(Text, nullable=True)  # 备注
    
    # 客户和地址信息 (JSON 存储)
    customer_data = Column(JSON, nullable=True)  # 客户信息
    billing_address = Column(JSON, nullable=True)  # 账单地址
    shipping_address = Column(JSON, nullable=True)  # 配送地址
    
    # 订单详情 (JSON 存储)
    line_items = Column(JSON, nullable=True)  # 订单项
    fulfillments = Column(JSON, nullable=True)  # 履行信息
    refunds = Column(JSON, nullable=True)  # 退款信息
    
    # 原始数据
    raw_data = Column(JSON, nullable=True)  # 完整的 Shopify 原始数据
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)  # 最后同步时间
    
    # 关系
    tenant = relationship("Tenant")
    
    # 索引和约束
    __table_args__ = (
        # 唯一约束：租户 + Shopify 订单 ID
        UniqueConstraint('tenant_id', 'shopify_order_id', name='uq_shopify_orders_tenant_shopify_id'),
        
        # 索引
        Index('idx_shopify_orders_tenant_id', 'tenant_id'),
        Index('idx_shopify_orders_shopify_order_id', 'shopify_order_id'),
        Index('idx_shopify_orders_financial_status', 'financial_status'),
        Index('idx_shopify_orders_fulfillment_status', 'fulfillment_status'),
        Index('idx_shopify_orders_created_at', 'created_at'),
        Index('idx_shopify_orders_tenant_shopify_id', 'tenant_id', 'shopify_order_id'),
    )
    
    def __repr__(self):
        return f"<ShopifyOrder(id={self.id}, shopify_order_id='{self.shopify_order_id}', name='{self.name}')>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'shopify_order_id': self.shopify_order_id,
            'name': self.name,
            'confirmation_number': self.confirmation_number,
            'financial_status': self.financial_status,
            'fulfillment_status': self.fulfillment_status,
            'confirmed': self.confirmed,
            'closed': self.closed,
            'cancelled': self.cancelled,
            'currency_code': self.currency_code,
            'total_price': float(self.total_price) if self.total_price else None,
            'subtotal_price': float(self.subtotal_price) if self.subtotal_price else None,
            'total_tax': float(self.total_tax) if self.total_tax else None,
            'total_shipping': float(self.total_shipping) if self.total_shipping else None,
            'tags': self.tags,
            'note': self.note,
            'customer_data': self.customer_data,
            'billing_address': self.billing_address,
            'shipping_address': self.shipping_address,
            'line_items': self.line_items,
            'fulfillments': self.fulfillments,
            'refunds': self.refunds,
            'raw_data': self.raw_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_synced_at': self.last_synced_at.isoformat() if self.last_synced_at else None,
        }
