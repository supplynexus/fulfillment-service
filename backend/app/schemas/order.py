"""
Order schemas
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class OrderCreate(BaseModel):
    """创建订单的 schema"""

    external_order_id: str
    external_order_number: Optional[str] = None
    external_order_name: Optional[str] = None
    status: str = "pending"
    total_amount: float
    currency: str = "USD"
    customer_email: str
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    shipping_address: Optional[Dict[str, Any]] = None
    billing_address: Optional[Dict[str, Any]] = None
    line_items: Optional[List[Dict[str, Any]]] = None
    order_date: datetime
    fulfillment_status: Optional[str] = None
    external_data: Optional[Dict[str, Any]] = None
    address_validation_status: Optional[str] = None
    address_validation_reason_code: Optional[str] = None
    address_validation_message: Optional[str] = None
    address_last_validated_at: Optional[datetime] = None


class OrderResponse(BaseModel):
    """订单响应 schema"""

    id_hashid: str  # 使用 hashids 替代原始 ID
    # 移除 tenant_id，前端不需要
    order_number: str  # 人类可读的订单编号，如 ORD-2025-001
    external_order_id: Optional[str] = None
    external_order_number: Optional[str] = None
    external_order_name: Optional[str] = None
    status: str
    total_amount: float
    currency: str
    customer_email: str
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    shipping_address: Optional[Dict[str, Any]] = None
    billing_address: Optional[Dict[str, Any]] = None
    line_items: Optional[List[Dict[str, Any]]] = None
    order_date: datetime
    fulfillment_status: Optional[str] = None
    tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None
    external_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    address_validation_status: Optional[str] = None
    address_validation_reason_code: Optional[str] = None
    address_validation_message: Optional[str] = None
    address_last_validated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    """订单列表响应 schema"""

    orders: List[OrderResponse]
    total: int
    total_pages: int
    current_page: int
    skip: int
    limit: int


class OrderSyncResponse(BaseModel):
    """订单同步响应 schema"""

    success: bool
    orders_fetched: int
    orders_saved: int
    orders_updated: int
    errors: List[str]
    error: Optional[str] = None


class BatchUpdateShopifyStatusRequest(BaseModel):
    """批量更新 Shopify 订单状态请求 schema"""

    order_ids: List[str]  # 订单 hashids 列表
