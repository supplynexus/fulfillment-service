"""
Order schemas for API requests and responses
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class OrderBase(BaseModel):
    shopify_order_id: str
    order_number: str
    customer_id: Optional[int] = None
    email: Optional[str] = None
    total_price: float
    subtotal_price: float
    total_tax: float
    currency: str = "USD"
    financial_status: str
    fulfillment_status: Optional[str] = None
    order_status_url: Optional[str] = None
    note: Optional[str] = None
    tags: Optional[str] = None
    processed_at: datetime
    created_at: datetime
    updated_at: datetime


class OrderCreate(OrderBase):
    raw_data: Dict[str, Any]


class OrderUpdate(BaseModel):
    financial_status: Optional[str] = None
    fulfillment_status: Optional[str] = None
    note: Optional[str] = None
    tags: Optional[str] = None
    updated_at: Optional[datetime] = None


class Order(OrderBase):
    id: int
    raw_data: Dict[str, Any]
    
    class Config:
        from_attributes = True


class OrderSyncResponse(BaseModel):
    total_orders: int
    new_orders: int
    updated_orders: int
    skipped_orders: int
    success: bool
    message: str


class OrderBatchResponse(BaseModel):
    task_id: str
    status: str
    message: str
