"""
Product schemas for API requests and responses
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class ProductBase(BaseModel):
    shopify_product_id: str
    title: str
    handle: str
    product_type: Optional[str] = None
    vendor: Optional[str] = None
    status: str = "active"
    tags: Optional[str] = None
    
    
class ProductCreate(ProductBase):
    raw_data: Dict[str, Any]


class ProductUpdate(BaseModel):
    title: Optional[str] = None
    handle: Optional[str] = None
    product_type: Optional[str] = None
    vendor: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[str] = None
    updated_at: Optional[datetime] = None


class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    raw_data: Dict[str, Any]
    
    class Config:
        from_attributes = True


class ProductSyncResponse(BaseModel):
    total_products: int
    new_products: int
    updated_products: int
    skipped_products: int
    success: bool
    message: str
