"""
Product Variants API - SKU 管理 API

实现功能：
1. SKU 的 CRUD 操作
2. 批量创建 SKU（笛卡尔积生成）
3. SKU 搜索和筛选
4. SKU 维度值管理
5. SKU 属性管理
"""

from typing import List, Optional, Dict, Any, Tuple
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from app.schemas.base import BaseResponse

from app.core.database import get_async_db
from app.core.jwt_auth_dependency import verify_jwt_auth
from app.services.product_variant_service import ProductVariantService
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# Pydantic Models
class VariantCreateRequest(BaseModel):
    product_id: int = Field(..., description="产品ID")
    sku: str = Field(..., description="SKU编码")
    name: Optional[str] = Field(None, description="SKU名称")
    description: Optional[str] = Field(None, description="描述")
    price: Optional[float] = Field(None, description="售价")
    cost_price: Optional[float] = Field(None, description="成本价")
    weight: Optional[float] = Field(None, description="重量")
    dimensions: Optional[Dict[str, Any]] = Field(None, description="维度值字典")
    attributes: Optional[Dict[str, Any]] = Field(None, description="属性字典")
    is_active: bool = Field(True, description="是否激活")


class VariantUpdateRequest(BaseModel):
    sku: Optional[str] = Field(None, description="SKU编码")
    name: Optional[str] = Field(None, description="SKU名称")
    description: Optional[str] = Field(None, description="描述")
    price: Optional[float] = Field(None, description="售价")
    cost_price: Optional[float] = Field(None, description="成本价")
    weight: Optional[float] = Field(None, description="重量")
    is_active: Optional[bool] = Field(None, description="是否激活")


class VariantResponse(BaseResponse):
    id: int
    product_id: int
    sku: Optional[str]
    price: Optional[float]
    cost_price: Optional[float]
    weight: Optional[float]
    is_active: bool


class VariantSearchRequest(BaseModel):
    sku: Optional[str] = Field(None, description="SKU编码")
    name: Optional[str] = Field(None, description="SKU名称")
    is_active: Optional[bool] = Field(None, description="是否激活")
    product_id: Optional[int] = Field(None, description="产品ID")
    price_min: Optional[float] = Field(None, description="最低价格")
    price_max: Optional[float] = Field(None, description="最高价格")


class VariantSearchResponse(BaseModel):
    variants: List[VariantResponse]
    total: int
    page: int
    page_size: int


class CartesianProductRequest(BaseModel):
    product_id: int = Field(..., description="产品ID")
    dimension_combinations: Dict[str, List[int]] = Field(..., description="维度组合")
    base_sku_prefix: str = Field("", description="SKU前缀")
    base_name_prefix: str = Field("", description="名称前缀")
    base_price: Optional[float] = Field(None, description="基础价格")
    base_cost_price: Optional[float] = Field(None, description="基础成本价")
    base_weight: Optional[float] = Field(None, description="基础重量")
    additional_attributes: Optional[Dict[str, Any]] = Field(None, description="额外属性")


class CartesianProductPreviewRequest(BaseModel):
    dimension_combinations: Dict[str, List[int]] = Field(..., description="维度组合")


class CartesianProductPreviewResponse(BaseModel):
    combinations: List[Dict[str, Any]]
    total_combinations: int


class VariantDimensionRequest(BaseModel):
    variant_id: int = Field(..., description="SKU ID")
    dimension_template_id: int = Field(..., description="维度模板ID")
    dimension_value_id: int = Field(..., description="维度值ID")


class VariantStatisticsResponse(BaseModel):
    total_variants: int
    active_variants: int
    inactive_variants: int
    variants_by_product: List[Dict[str, Any]]


# API Endpoints
@router.post("/", response_model=VariantResponse)
async def create_variant(
    request: VariantCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> VariantResponse:
    """创建SKU"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始创建SKU", 
                   product_id=request.product_id,
                   sku=request.sku)
        
        service = ProductVariantService(db)
        variant = await service.create_variant(
            product_id=request.product_id,
            sku=request.sku,
            name=request.name,
            description=request.description,
            price=request.price,
            cost_price=request.cost_price,
            weight=request.weight,
            dimensions=request.dimensions,
            attributes=request.attributes,
            is_active=request.is_active
        )
        
        logger.info("✅ SKU创建成功", 
                   variant_id=variant.id,
                   sku=variant.sku)
        
        return VariantResponse.from_orm(variant)
        
    except ValueError as e:
        logger.error("❌ SKU创建失败", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("❌ SKU创建异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"创建SKU失败: {str(e)}")


@router.get("/{variant_id}", response_model=VariantResponse)
async def get_variant(
    variant_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> VariantResponse:
    """获取单个SKU"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始获取SKU", variant_id=variant_id)
        
        service = ProductVariantService(db)
        variant = await service.get_variant_by_id(variant_id)
        
        if not variant:
            raise HTTPException(status_code=404, detail="SKU不存在")
        
        logger.info("✅ SKU获取成功", variant_id=variant_id)
        
        return VariantResponse.from_orm(variant)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ SKU获取异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取SKU失败: {str(e)}")


@router.put("/{variant_id}", response_model=VariantResponse)
async def update_variant(
    variant_id: int,
    request: VariantUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> VariantResponse:
    """更新SKU"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始更新SKU", variant_id=variant_id)
        
        service = ProductVariantService(db)
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        
        variant = await service.update_variant(variant_id, **update_data)
        
        if not variant:
            raise HTTPException(status_code=404, detail="SKU不存在")
        
        logger.info("✅ SKU更新成功", variant_id=variant_id)
        
        return VariantResponse.from_orm(variant)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ SKU更新异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"更新SKU失败: {str(e)}")


@router.delete("/{variant_id}")
async def delete_variant(
    variant_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> Dict[str, Any]:
    """删除SKU"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始删除SKU", variant_id=variant_id)
        
        service = ProductVariantService(db)
        success = await service.delete_variant(variant_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="SKU不存在")
        
        logger.info("✅ SKU删除成功", variant_id=variant_id)
        
        return {"success": True, "message": "SKU删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ SKU删除异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"删除SKU失败: {str(e)}")


@router.get("/", response_model=VariantSearchResponse)
async def search_variants(
    sku: Optional[str] = Query(None, description="SKU编码"),
    name: Optional[str] = Query(None, description="SKU名称"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    product_id: Optional[int] = Query(None, description="产品ID"),
    price_min: Optional[float] = Query(None, description="最低价格"),
    price_max: Optional[float] = Query(None, description="最高价格"),
    sort_by: str = Query("sku", description="排序字段"),
    sort_order: str = Query("asc", description="排序方向"),
    page: int = Query(1, description="页码"),
    page_size: int = Query(100, description="每页数量"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> VariantSearchResponse:
    """搜索SKU"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始搜索SKU", 
                   tenant_id=tenant.id,
                   filters={
                       "sku": sku,
                       "name": name,
                       "is_active": is_active,
                       "product_id": product_id,
                       "price_min": price_min,
                       "price_max": price_max
                   })
        
        service = ProductVariantService(db)
        
        # 构建筛选条件
        filters = {}
        if sku:
            filters["sku"] = sku
        if name:
            filters["name"] = name
        if is_active is not None:
            filters["is_active"] = is_active
        if product_id:
            filters["product_id"] = product_id
        if price_min is not None:
            filters["price_min"] = price_min
        if price_max is not None:
            filters["price_max"] = price_max
        
        variants, total = await service.search_variants(
            tenant_id=tenant.id,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=page_size,
            offset=(page - 1) * page_size
        )
        
        logger.info("✅ SKU搜索完成", 
                   found_count=len(variants),
                   total=total)
        
        return VariantSearchResponse(
            variants=[VariantResponse.from_orm(v) for v in variants],
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error("❌ SKU搜索异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"搜索SKU失败: {str(e)}")


@router.get("/products/{product_id}", response_model=List[VariantResponse])
async def get_product_variants(
    product_id: int,
    include_inactive: bool = Query(False, description="是否包含非激活SKU"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> List[VariantResponse]:
    """获取产品的所有SKU"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始获取产品SKU", 
                   product_id=product_id,
                   include_inactive=include_inactive)
        
        service = ProductVariantService(db)
        variants = await service.get_product_variants(product_id, include_inactive)
        
        logger.info("✅ 产品SKU获取成功", 
                   product_id=product_id,
                   variant_count=len(variants))
        
        return [VariantResponse.from_orm(v) for v in variants]
        
    except Exception as e:
        logger.error("❌ 产品SKU获取异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取产品SKU失败: {str(e)}")


@router.post("/cartesian-product/preview", response_model=CartesianProductPreviewResponse)
async def preview_cartesian_product(
    request: CartesianProductPreviewRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> CartesianProductPreviewResponse:
    """预览笛卡尔积组合"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始预览笛卡尔积组合", 
                   dimension_count=len(request.dimension_combinations))
        
        service = ProductVariantService(db)
        combinations = await service.preview_cartesian_product(request.dimension_combinations)
        
        logger.info("✅ 笛卡尔积预览完成", 
                   total_combinations=len(combinations))
        
        return CartesianProductPreviewResponse(
            combinations=combinations,
            total_combinations=len(combinations)
        )
        
    except Exception as e:
        logger.error("❌ 笛卡尔积预览异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"预览笛卡尔积失败: {str(e)}")


@router.post("/cartesian-product", response_model=List[VariantResponse])
async def create_cartesian_product_variants(
    request: CartesianProductRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> List[VariantResponse]:
    """使用笛卡尔积创建多个SKU"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始创建笛卡尔积SKU", 
                   product_id=request.product_id,
                   dimension_count=len(request.dimension_combinations))
        
        service = ProductVariantService(db)
        variants = await service.generate_cartesian_product_variants(
            product_id=request.product_id,
            dimension_combinations=request.dimension_combinations,
            base_sku_prefix=request.base_sku_prefix,
            base_name_prefix=request.base_name_prefix,
            base_price=request.base_price,
            base_cost_price=request.base_cost_price,
            base_weight=request.base_weight,
            additional_attributes=request.additional_attributes
        )
        
        logger.info("✅ 笛卡尔积SKU创建成功", 
                   product_id=request.product_id,
                   created_count=len(variants))
        
        return [VariantResponse.from_orm(v) for v in variants]
        
    except ValueError as e:
        logger.error("❌ 笛卡尔积SKU创建失败", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("❌ 笛卡尔积SKU创建异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"创建笛卡尔积SKU失败: {str(e)}")


@router.post("/dimensions", response_model=Dict[str, Any])
async def create_variant_dimension(
    request: VariantDimensionRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> Dict[str, Any]:
    """为SKU创建维度值"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始创建SKU维度值", 
                   variant_id=request.variant_id,
                   dimension_template_id=request.dimension_template_id)
        
        service = ProductVariantService(db)
        variant_dimension = await service.create_variant_dimension(
            request.variant_id,
            request.dimension_template_id,
            request.dimension_value_id
        )
        
        logger.info("✅ SKU维度值创建成功", 
                   variant_dimension_id=variant_dimension.id)
        
        return {"success": True, "message": "SKU维度值创建成功", "variant_dimension_id": variant_dimension.id}
        
    except ValueError as e:
        logger.error("❌ SKU维度值创建失败", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("❌ SKU维度值创建异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"创建SKU维度值失败: {str(e)}")


@router.get("/{variant_id}/dimensions", response_model=List[Dict[str, Any]])
async def get_variant_dimensions(
    variant_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> List[Dict[str, Any]]:
    """获取SKU的所有维度值"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始获取SKU维度值", variant_id=variant_id)
        
        service = ProductVariantService(db)
        dimensions = await service.get_variant_dimensions(variant_id)
        
        logger.info("✅ SKU维度值获取成功", 
                   variant_id=variant_id,
                   dimension_count=len(dimensions))
        
        return [
            {
                "id": dim.id,
                "dimension_template": {
                    "id": dim.dimension_template.id,
                    "dimension_code": dim.dimension_template.dimension_code,
                    "dimension_name": dim.dimension_template.dimension_name
                },
                "dimension_value": {
                    "id": dim.dimension_value.id,
                    "value_code": dim.dimension_value.value_code,
                    "value_name": dim.dimension_value.value_name
                }
            }
            for dim in dimensions
        ]
        
    except Exception as e:
        logger.error("❌ SKU维度值获取异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取SKU维度值失败: {str(e)}")


@router.get("/statistics", response_model=VariantStatisticsResponse)
async def get_variant_statistics(
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> VariantStatisticsResponse:
    """获取SKU统计信息"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始获取SKU统计信息", tenant_id=tenant.id)
        
        service = ProductVariantService(db)
        stats = await service.get_variant_statistics(tenant.id)
        
        logger.info("✅ SKU统计信息获取成功")
        
        return VariantStatisticsResponse(**stats)
        
    except Exception as e:
        logger.error("❌ SKU统计信息获取异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取SKU统计信息失败: {str(e)}")
