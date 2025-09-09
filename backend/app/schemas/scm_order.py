"""
SCM Order schemas
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class SCMOrderCreate(BaseModel):
    """创建SCM订单的 schema"""
    source_order_id: int
    target_system_type: str
    target_system_id: Optional[str] = None
    routing_strategy: Optional[str] = "auto"
    line_items: List[Dict[str, Any]]
    total_amount: float
    currency: str = "USD"
    customer_email: str
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    shipping_address: Dict[str, Any]
    billing_address: Optional[Dict[str, Any]] = None
    routing_metadata: Optional[Dict[str, Any]] = None


class SCMOrderResponse(BaseModel):
    """SCM订单响应 schema"""
    id: int
    tenant_id: int
    source_order_id: int
    target_system_type: str
    target_system_id: Optional[str] = None
    scm_order_number: Optional[str] = None
    status: str
    fulfillment_status: Optional[str] = None
    routing_strategy: Optional[str] = None
    line_items: List[Dict[str, Any]]
    total_amount: float
    currency: str
    customer_email: str
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    shipping_address: Dict[str, Any]
    billing_address: Optional[Dict[str, Any]] = None
    routing_metadata: Optional[Dict[str, Any]] = None
    tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    shopify_fulfillment_order_id: Optional[str] = None
    shopify_fulfillment_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    fulfilled_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class SCMOrderListResponse(BaseModel):
    """SCM订单列表响应 schema"""
    scm_orders: List[SCMOrderResponse]
    total: int
    skip: int
    limit: int


class RoutingRuleCreate(BaseModel):
    """创建路由规则的 schema"""
    name: str
    description: Optional[str] = None
    conditions: Dict[str, Any]
    target_system_type: str
    target_system_id: Optional[str] = None
    priority: int = 1
    is_active: bool = True


class RoutingRuleResponse(BaseModel):
    """路由规则响应 schema"""
    id: int
    tenant_id: int
    name: str
    description: Optional[str] = None
    conditions: Dict[str, Any]
    target_system_type: str
    target_system_id: Optional[str] = None
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class RoutingRuleListResponse(BaseModel):
    """路由规则列表响应 schema"""
    routing_rules: List[RoutingRuleResponse]
    total: int
    skip: int
    limit: int


class OrderRoutingConfig(BaseModel):
    """订单路由配置 schema"""
    routing_strategy: str = "auto"  # auto, manual, hybrid
    target_systems: List[Dict[str, Any]] = []
    routing_rules: Dict[str, Any] = {}
    custom_metadata: Dict[str, Any] = {}


class OrderRoutingResponse(BaseModel):
    """订单路由响应 schema"""
    success: bool
    original_order_id: int
    scm_orders: List[Dict[str, Any]]
    routing_summary: Dict[str, Any]
    errors: List[str] = []


class BatchOrderRoutingConfig(BaseModel):
    """批量订单路由配置 schema"""
    order_ids: List[int]
    routing_strategy: str = "auto"
    batch_processing: Dict[str, Any] = {}


class BatchOrderRoutingResponse(BaseModel):
    """批量订单路由响应 schema"""
    success: bool
    processed_orders: int
    total_orders: int
    scm_orders_created: int
    errors: List[str] = []
    results: List[Dict[str, Any]] = []
