"""
Product schemas for API requests and responses
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


# ==================== 新的商品系统 Schema ====================

class ProductDimensionResponse(BaseModel):
    """商品维度响应"""
    id_hashid: str
    dimension_name: str
    dimension_type: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    options: Optional[List[str]] = None
    is_required: bool = True
    display_order: int = 0
    is_active: bool = True
    
    class Config:
        from_attributes = True


class ProductVariantResponse(BaseModel):
    """商品变体响应"""
    id_hashid: str
    sku: Optional[str] = None
    barcode: Optional[str] = None
    attributes: Dict[str, Any] = {}
    price: Optional[float] = None
    compare_at_price: Optional[float] = None
    cost_price: Optional[float] = None
    inventory_quantity: int = 0
    inventory_policy: str = "deny"
    tracks_inventory: bool = True
    is_active: bool = True
    is_available: bool = True
    image_url: Optional[str] = None
    weight: Optional[float] = None
    dimensions: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class ProductTagResponse(BaseModel):
    """商品标签响应"""
    id_hashid: str
    name: str
    display_name: Optional[str] = None
    color: Optional[str] = None
    category: Optional[str] = None
    is_primary: bool = False
    sort_order: int = 0
    
    class Config:
        from_attributes = True


class ProductMappingResponse(BaseModel):
    """商品映射响应"""
    id_hashid: str
    external_system_name: str
    external_product_id: str
    external_variant_id: Optional[str] = None
    mapping_type: str
    sync_direction: str
    sync_status: str
    last_synced_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ProductResponse(BaseModel):
    """商品响应 - 新的完整商品信息"""
    id_hashid: str
    title: str
    description: Optional[str] = None
    handle: Optional[str] = None
    product_type: Optional[str] = None
    vendor: Optional[str] = None
    status: str
    is_active: bool
    is_available: bool
    images: Optional[List[Dict[str, Any]]] = None
    seo: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # 关联数据
    dimensions: List[ProductDimensionResponse] = []
    variants: List[ProductVariantResponse] = []
    tags: List[ProductTagResponse] = []
    mappings: List[ProductMappingResponse] = []
    # 列表/筛选用：是否已绑定 Printify（仅当 include_mappings 时可靠）
    has_printify_mapping: Optional[bool] = None

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    """商品列表响应"""
    products: List[ProductResponse]
    total: int
    skip: int
    limit: int
    has_more: bool = False


# ==================== 创建和更新 Schema ====================

class ProductCreateRequest(BaseModel):
    """创建商品请求"""
    title: str
    description: Optional[str] = None
    handle: Optional[str] = None
    product_type: Optional[str] = None
    vendor: Optional[str] = None
    status: str = "draft"
    is_active: bool = True
    is_available: bool = True
    images: Optional[List[Dict[str, Any]]] = None
    seo: Optional[Dict[str, Any]] = None


class ProductUpdateRequest(BaseModel):
    """更新商品请求"""
    title: Optional[str] = None
    description: Optional[str] = None
    handle: Optional[str] = None
    product_type: Optional[str] = None
    vendor: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None
    is_available: Optional[bool] = None
    images: Optional[List[Dict[str, Any]]] = None
    seo: Optional[Dict[str, Any]] = None


class ProductVariantCreateRequest(BaseModel):
    """创建变体请求"""
    sku: Optional[str] = None
    barcode: Optional[str] = None
    attributes: Dict[str, Any] = {}
    price: Optional[float] = None
    compare_at_price: Optional[float] = None
    cost_price: Optional[float] = None
    inventory_quantity: int = 0
    inventory_policy: str = "deny"
    tracks_inventory: bool = True
    is_active: bool = True
    is_available: bool = True
    image_url: Optional[str] = None
    weight: Optional[float] = None
    dimensions: Optional[Dict[str, Any]] = None


class ProductVariantUpdateRequest(BaseModel):
    """更新变体请求"""
    sku: Optional[str] = None
    barcode: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    price: Optional[float] = None
    compare_at_price: Optional[float] = None
    cost_price: Optional[float] = None
    inventory_quantity: Optional[int] = None
    inventory_policy: Optional[str] = None
    tracks_inventory: Optional[bool] = None
    is_active: Optional[bool] = None
    is_available: Optional[bool] = None
    image_url: Optional[str] = None
    weight: Optional[float] = None
    dimensions: Optional[Dict[str, Any]] = None


# ==================== 同步相关 Schema ====================

class ProductSyncResponse(BaseModel):
    """商品同步响应"""
    success: bool
    products_fetched: int = 0
    products_saved: int = 0
    products_updated: int = 0
    errors: List[str] = []
    error: Optional[str] = None


# ==================== 兼容性 Schema (保留旧版本) ====================

class ProductBase(BaseModel):
    """基础商品模型 - 兼容性"""
    title: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    images: Optional[List[Dict[str, Any]]] = None
    variants: Optional[List[Dict[str, Any]]] = None
    price: Optional[float] = None
    compare_at_price: Optional[float] = None
    is_active: bool = True
    is_available: bool = True
    status: Optional[str] = "active"
    external_data: Optional[Dict[str, Any]] = None


class ProductCreate(ProductBase):
    """创建商品 - 兼容性"""
    external_product_id: str


class ProductUpdate(BaseModel):
    """更新商品 - 兼容性"""
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
