"""
Product schemas for API requests and responses
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class ProductBase(BaseModel):
    title: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    images: Optional[List[Dict[str, Any]]] = None
    variants: Optional[List[Dict[str, Any]]] = None
    price: Optional[float] = None
    compare_at_price: Optional[float] = None
    is_active: bool = True
    is_available: bool = True
    status: Optional[str] = "active"  # 添加 status 字段
    external_data: Optional[Dict[str, Any]] = None


class ProductCreate(ProductBase):
    external_product_id: str


class ProductUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    images: Optional[List[Dict[str, Any]]] = None
    variants: Optional[List[Dict[str, Any]]] = None
    price: Optional[float] = None
    compare_at_price: Optional[float] = None
    is_active: Optional[bool] = None
    is_available: Optional[bool] = None
    updated_at: Optional[datetime] = None


class ProductResponse(ProductBase):
    id: int
    tenant_id: int
    external_product_id: Optional[str] = None
    external_system_id: Optional[int] = None
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    products: List[ProductResponse]
    total: int
    skip: int
    limit: int


class ProductSyncResponse(BaseModel):
    success: bool
    products_fetched: int
    products_saved: int
    products_updated: int
    errors: List[str]
    error: Optional[str] = None
