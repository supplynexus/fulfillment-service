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
    line_items: List[Dict[str, Any]]
    order_date: datetime
    fulfillment_status: Optional[str] = None
    external_data: Optional[Dict[str, Any]] = None


class OrderResponse(BaseModel):
    """订单响应 schema"""

    id: int
    tenant_id: int
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
    line_items: List[Dict[str, Any]]
    order_date: datetime
    fulfillment_status: Optional[str] = None
    tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
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
