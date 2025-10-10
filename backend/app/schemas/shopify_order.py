"""
Shopify Order schemas for API requests and responses
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ShopifyOrderBase(BaseModel):
    """Shopify 订单基础 schema"""
    shopify_order_id: str = Field(..., description="Shopify 订单 ID")
    name: Optional[str] = Field(None, description="订单名称")
    confirmation_number: Optional[str] = Field(None, description="确认号")
    financial_status: Optional[str] = Field(None, description="财务状态")
    fulfillment_status: Optional[str] = Field(None, description="履行状态")
    confirmed: bool = Field(False, description="是否确认")
    closed: bool = Field(False, description="是否关闭")
    cancelled: bool = Field(False, description="是否取消")
    currency_code: Optional[str] = Field(None, description="货币代码")
    total_price: Optional[float] = Field(None, description="总价")
    subtotal_price: Optional[float] = Field(None, description="小计")
    total_tax: Optional[float] = Field(None, description="税费")
    total_shipping: Optional[float] = Field(None, description="运费")
    tags: Optional[List[str]] = Field(None, description="标签")
    note: Optional[str] = Field(None, description="备注")
    customer_data: Optional[Dict[str, Any]] = Field(None, description="客户数据")
    billing_address: Optional[Dict[str, Any]] = Field(None, description="账单地址")
    shipping_address: Optional[Dict[str, Any]] = Field(None, description="配送地址")
    line_items: Optional[List[Dict[str, Any]]] = Field(None, description="订单项")
    fulfillments: Optional[List[Dict[str, Any]]] = Field(None, description="履行信息")
    refunds: Optional[List[Dict[str, Any]]] = Field(None, description="退款信息")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="原始数据")


class ShopifyOrderCreate(ShopifyOrderBase):
    """创建 Shopify 订单请求"""
    pass


class ShopifyOrderUpdate(BaseModel):
    """更新 Shopify 订单请求"""
    name: Optional[str] = Field(None, description="订单名称")
    confirmation_number: Optional[str] = Field(None, description="确认号")
    financial_status: Optional[str] = Field(None, description="财务状态")
    fulfillment_status: Optional[str] = Field(None, description="履行状态")
    confirmed: Optional[bool] = Field(None, description="是否确认")
    closed: Optional[bool] = Field(None, description="是否关闭")
    cancelled: Optional[bool] = Field(None, description="是否取消")
    currency_code: Optional[str] = Field(None, description="货币代码")
    total_price: Optional[float] = Field(None, description="总价")
    subtotal_price: Optional[float] = Field(None, description="小计")
    total_tax: Optional[float] = Field(None, description="税费")
    total_shipping: Optional[float] = Field(None, description="运费")
    tags: Optional[List[str]] = Field(None, description="标签")
    note: Optional[str] = Field(None, description="备注")
    customer_data: Optional[Dict[str, Any]] = Field(None, description="客户数据")
    billing_address: Optional[Dict[str, Any]] = Field(None, description="账单地址")
    shipping_address: Optional[Dict[str, Any]] = Field(None, description="配送地址")
    line_items: Optional[List[Dict[str, Any]]] = Field(None, description="订单项")
    fulfillments: Optional[List[Dict[str, Any]]] = Field(None, description="履行信息")
    refunds: Optional[List[Dict[str, Any]]] = Field(None, description="退款信息")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="原始数据")


class ShopifyOrderResponse(ShopifyOrderBase):
    """Shopify 订单响应"""
    id: int
    id_hashid: str  # 添加 hashid 字段
    tenant_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ShopifyOrderListResponse(BaseModel):
    """Shopify 订单列表响应"""
    orders: List[ShopifyOrderResponse]
    total: int
    skip: int
    limit: int
    
    class Config:
        from_attributes = True


class ShopifyOrderSyncResponse(BaseModel):
    """Shopify 订单同步响应"""
    success: bool
    message: str
    orders_processed: int = 0
    orders_created: int = 0
    orders_updated: int = 0
    errors: List[str] = []
    
    class Config:
        from_attributes = True


class ShopifyOrderStatisticsResponse(BaseModel):
    """Shopify 订单统计响应"""
    total_orders: int
    orders_by_status: Dict[str, int]
    orders_by_financial_status: Dict[str, int]
    orders_by_fulfillment_status: Dict[str, int]
    total_revenue: float
    average_order_value: float
    orders_this_month: int
    orders_last_month: int
    
    class Config:
        from_attributes = True
