"""
Product Dimensions API - 产品维度管理 API

实现功能：
1. 维度模板的 CRUD 操作
2. 维度值的 CRUD 操作
3. 分类维度关联管理
4. 维度继承管理
5. SKU 维度值管理
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import logging

from app.schemas.base import BaseResponse

from app.core.database import get_async_db
from app.core.jwt_auth_dependency import verify_jwt_auth
from app.services.product_dimension_service import ProductDimensionService
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# Pydantic Models
class DimensionTemplateCreateRequest(BaseModel):
    dimension_code: str = Field(..., description="维度编码")
    dimension_name: str = Field(..., description="维度名称")
    dimension_type: str = Field("select", description="维度类型")
    description: Optional[str] = Field(None, description="描述")
    sort_order: int = Field(0, description="排序")


class DimensionTemplateUpdateRequest(BaseModel):
    dimension_name: Optional[str] = Field(None, description="维度名称")
    dimension_type: Optional[str] = Field(None, description="维度类型")
    description: Optional[str] = Field(None, description="描述")
    sort_order: Optional[int] = Field(None, description="排序")
    is_active: Optional[bool] = Field(None, description="是否激活")


class DimensionTemplateResponse(BaseResponse):
    id: int
    dimension_code: str
    dimension_name: str
    dimension_type: str
    description: Optional[str]
    sort_order: int
    is_active: bool

    class Config:
        from_attributes = True


class DimensionValueCreateRequest(BaseModel):
    category_dimension_id: int = Field(..., description="分类维度关联ID")
    dimension_template_id: int = Field(..., description="维度模板ID")
    value_code: str = Field(..., description="值编码")
    value_name: str = Field(..., description="值名称")
    value_type: str = Field("normal", description="值类型")
    is_default: bool = Field(False, description="是否为默认值")
    sort_order: int = Field(0, description="排序")


class DimensionValueUpdateRequest(BaseModel):
    value_name: Optional[str] = Field(None, description="值名称")
    value_type: Optional[str] = Field(None, description="值类型")
    is_default: Optional[bool] = Field(None, description="是否为默认值")
    sort_order: Optional[int] = Field(None, description="排序")
    is_active: Optional[bool] = Field(None, description="是否激活")


class DimensionValueResponse(BaseResponse):
    id: int
    value_code: str
    value_name: str
    value_type: str
    is_default: bool
    sort_order: int
    is_active: bool

    class Config:
        from_attributes = True


class CategoryDimensionInheritRequest(BaseModel):
    child_category_id: int = Field(..., description="子分类ID")
    parent_category_id: int = Field(..., description="父分类ID")
    dimension_template_id: int = Field(..., description="维度模板ID")
    is_required: bool = Field(True, description="是否必填")
    is_overridable: bool = Field(True, description="是否可覆盖")


class CategoryDimensionOverrideRequest(BaseModel):
    category_id: int = Field(..., description="分类ID")
    dimension_template_id: int = Field(..., description="维度模板ID")
    is_required: Optional[bool] = Field(None, description="新的必填设置")
    is_overridable: Optional[bool] = Field(None, description="新的可覆盖设置")


class VariantDimensionCreateRequest(BaseModel):
    variant_id: int = Field(..., description="SKU ID")
    dimension_template_id: int = Field(..., description="维度模板ID")
    dimension_value_id: int = Field(..., description="维度值ID")


class EffectiveDimensionsResponse(BaseModel):
    dimensions: List[Dict[str, Any]]


# API Endpoints
@router.post("/templates", response_model=DimensionTemplateResponse)
async def create_dimension_template(
    request: DimensionTemplateCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> DimensionTemplateResponse:
    """创建维度模板"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始创建维度模板", 
                   tenant_id=tenant.id,
                   dimension_code=request.dimension_code)
        
        service = ProductDimensionService(db)
        template = await service.create_dimension_template(
            tenant_id=tenant.id,
            dimension_code=request.dimension_code,
            dimension_name=request.dimension_name,
            dimension_type=request.dimension_type,
            description=request.description,
            sort_order=request.sort_order
        )
        
        logger.info("✅ 维度模板创建成功", 
                   template_id=template.id,
                   dimension_code=template.dimension_code)
        
        # 手动构建响应对象，转换 datetime 为字符串
        return DimensionTemplateResponse(
            id=template.id,
            dimension_code=template.dimension_code,
            dimension_name=template.dimension_name,
            dimension_type=template.dimension_type,
            description=template.description,
            sort_order=template.sort_order,
            is_active=template.is_active,
            created_at=template.created_at.isoformat() if template.created_at else "",
            updated_at=template.updated_at.isoformat() if template.updated_at else ""
        )
        
    except ValueError as e:
        logger.error("❌ 维度模板创建失败", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("❌ 维度模板创建异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"创建维度模板失败: {str(e)}")


@router.get("/templates", response_model=List[DimensionTemplateResponse])
async def get_dimension_templates(
    include_inactive: bool = Query(False, description="是否包含非激活模板"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> List[DimensionTemplateResponse]:
    """获取维度模板列表"""
    logger.info(f"🔍 开始获取维度模板列表: include_inactive={include_inactive}")
    logger.info(f"🔍 请求到达API端点: 认证依赖已通过")
    tenant, user = auth
    
    try:
        logger.info("🔍 开始获取维度模板列表", 
                   tenant_id=tenant.id,
                   include_inactive=include_inactive)
        
        service = ProductDimensionService(db)
        templates = await service.get_dimension_templates(tenant.id, include_inactive)
        
        logger.info("✅ 维度模板列表获取成功", 
                   tenant_id=tenant.id,
                   template_count=len(templates))
        
        # 手动构造响应对象，处理 datetime 字段
        result = []
        for template in templates:
            template_dict = {
                "id": template.id,
                "dimension_code": template.dimension_code,
                "dimension_name": template.dimension_name,
                "dimension_type": template.dimension_type,
                "description": template.description,
                "sort_order": template.sort_order,
                "is_active": template.is_active,
                "created_at": template.created_at.isoformat() if template.created_at else None,
                "updated_at": template.updated_at.isoformat() if template.updated_at else None,
            }
            result.append(DimensionTemplateResponse(**template_dict))
        
        return result
        
    except Exception as e:
        logger.error("❌ 维度模板列表获取异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取维度模板列表失败: {str(e)}")


@router.get("/templates/{template_id}", response_model=DimensionTemplateResponse)
async def get_dimension_template(
    template_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> DimensionTemplateResponse:
    """获取单个维度模板"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始获取维度模板", 
                   template_id=template_id,
                   tenant_id=tenant.id)
        
        service = ProductDimensionService(db)
        template = await service.get_dimension_template_by_id(template_id, tenant.id)
        
        if not template:
            raise HTTPException(status_code=404, detail="维度模板不存在")
        
        logger.info("✅ 维度模板获取成功", template_id=template_id)
        
        # 手动构造响应对象，处理 datetime 字段
        template_dict = {
            "id": template.id,
            "dimension_code": template.dimension_code,
            "dimension_name": template.dimension_name,
            "dimension_type": template.dimension_type,
            "description": template.description,
            "sort_order": template.sort_order,
            "is_active": template.is_active,
            "created_at": template.created_at.isoformat() if template.created_at else None,
            "updated_at": template.updated_at.isoformat() if template.updated_at else None,
        }
        return DimensionTemplateResponse(**template_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ 维度模板获取异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取维度模板失败: {str(e)}")


@router.put("/templates/{template_id}", response_model=DimensionTemplateResponse)
async def update_dimension_template(
    template_id: int,
    request: DimensionTemplateUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> DimensionTemplateResponse:
    """更新维度模板"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始更新维度模板", 
                   template_id=template_id,
                   tenant_id=tenant.id)
        
        service = ProductDimensionService(db)
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        
        template = await service.update_dimension_template(template_id, tenant.id, **update_data)
        
        if not template:
            raise HTTPException(status_code=404, detail="维度模板不存在")
        
        logger.info("✅ 维度模板更新成功", template_id=template_id)
        
        return DimensionTemplateResponse.model_validate(template)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ 维度模板更新异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"更新维度模板失败: {str(e)}")


@router.delete("/templates/{template_id}")
async def delete_dimension_template(
    template_id: int,
    force: bool = Query(False, description="是否强制删除"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> Dict[str, Any]:
    """删除维度模板"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始删除维度模板", 
                   template_id=template_id,
                   force=force,
                   tenant_id=tenant.id)
        
        service = ProductDimensionService(db)
        success = await service.delete_dimension_template(template_id, tenant.id, force)
        
        if not success:
            raise HTTPException(status_code=404, detail="维度模板不存在")
        
        logger.info("✅ 维度模板删除成功", template_id=template_id)
        
        return {"success": True, "message": "维度模板删除成功"}
        
    except ValueError as e:
        logger.error("❌ 维度模板删除失败", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ 维度模板删除异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"删除维度模板失败: {str(e)}")


@router.post("/values", response_model=DimensionValueResponse)
async def create_dimension_value(
    request: DimensionValueCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> DimensionValueResponse:
    """创建维度值"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始创建维度值", 
                   category_dimension_id=request.category_dimension_id,
                   value_code=request.value_code)
        
        service = ProductDimensionService(db)
        value = await service.create_dimension_value(
            category_dimension_id=request.category_dimension_id,
            dimension_template_id=request.dimension_template_id,
            value_code=request.value_code,
            value_name=request.value_name,
            value_type=request.value_type,
            is_default=request.is_default,
            sort_order=request.sort_order,
            created_by=user.id
        )
        
        logger.info("✅ 维度值创建成功", 
                   value_id=value.id,
                   value_code=value.value_code)
        
        return DimensionValueResponse.model_validate(value)
        
    except ValueError as e:
        logger.error("❌ 维度值创建失败", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("❌ 维度值创建异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"创建维度值失败: {str(e)}")


@router.get("/templates/{template_id}/values", response_model=List[DimensionValueResponse])
async def get_dimension_values(
    template_id: int,
    category_dimension_id: Optional[int] = Query(None, description="分类维度关联ID"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> List[DimensionValueResponse]:
    """获取维度值列表"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始获取维度值列表", 
                   template_id=template_id,
                   category_dimension_id=category_dimension_id)
        
        service = ProductDimensionService(db)
        values = await service.get_dimension_values_by_template(template_id, category_dimension_id)
        
        logger.info("✅ 维度值列表获取成功", 
                   template_id=template_id,
                   value_count=len(values))
        
        return [DimensionValueResponse.model_validate(value) for value in values]
        
    except Exception as e:
        logger.error("❌ 维度值列表获取异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取维度值列表失败: {str(e)}")


@router.get("/categories/{category_id}/effective", response_model=EffectiveDimensionsResponse)
async def get_effective_dimensions(
    category_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> EffectiveDimensionsResponse:
    """获取分类的有效维度"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始获取分类有效维度", 
                   category_id=category_id,
                   tenant_id=tenant.id)
        
        service = ProductDimensionService(db)
        dimensions = await service.get_effective_dimensions_for_category(category_id, tenant.id)
        
        logger.info("✅ 分类有效维度获取成功", 
                   category_id=category_id,
                   dimension_count=len(dimensions))
        
        return EffectiveDimensionsResponse(dimensions=dimensions)
        
    except Exception as e:
        logger.error("❌ 分类有效维度获取异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取分类有效维度失败: {str(e)}")


@router.post("/categories/inherit", response_model=Dict[str, Any])
async def inherit_dimension_from_parent(
    request: CategoryDimensionInheritRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> Dict[str, Any]:
    """从父分类继承维度"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始继承维度", 
                   child_category_id=request.child_category_id,
                   parent_category_id=request.parent_category_id,
                   dimension_template_id=request.dimension_template_id)
        
        service = ProductDimensionService(db)
        category_dimension = await service.inherit_dimension_from_parent(
            request.child_category_id,
            request.parent_category_id,
            request.dimension_template_id,
            request.is_required,
            request.is_overridable
        )
        
        logger.info("✅ 维度继承成功", 
                   category_dimension_id=category_dimension.id)
        
        return {"success": True, "message": "维度继承成功", "category_dimension_id": category_dimension.id}
        
    except ValueError as e:
        logger.error("❌ 维度继承失败", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("❌ 维度继承异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"继承维度失败: {str(e)}")


@router.put("/categories/override", response_model=Dict[str, Any])
async def override_dimension(
    request: CategoryDimensionOverrideRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> Dict[str, Any]:
    """覆盖继承的维度设置"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始覆盖维度设置", 
                   category_id=request.category_id,
                   dimension_template_id=request.dimension_template_id)
        
        service = ProductDimensionService(db)
        category_dimension = await service.override_dimension(
            request.category_id,
            request.dimension_template_id,
            request.is_required,
            request.is_overridable
        )
        
        logger.info("✅ 维度设置覆盖成功")
        
        return {"success": True, "message": "维度设置覆盖成功", "category_dimension_id": category_dimension.id}
        
    except ValueError as e:
        logger.error("❌ 维度设置覆盖失败", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("❌ 维度设置覆盖异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"覆盖维度设置失败: {str(e)}")


@router.delete("/categories/{category_id}/dimensions/{dimension_template_id}")
async def remove_inherited_dimension(
    category_id: int,
    dimension_template_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> Dict[str, Any]:
    """移除继承的维度"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始移除继承维度", 
                   category_id=category_id,
                   dimension_template_id=dimension_template_id)
        
        service = ProductDimensionService(db)
        success = await service.remove_inherited_dimension(category_id, dimension_template_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="继承维度不存在")
        
        logger.info("✅ 继承维度移除成功")
        
        return {"success": True, "message": "继承维度移除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ 继承维度移除异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"移除继承维度失败: {str(e)}")


@router.post("/variants", response_model=Dict[str, Any])
async def create_variant_dimension(
    request: VariantDimensionCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> Dict[str, Any]:
    """为SKU创建维度值"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始创建SKU维度值", 
                   variant_id=request.variant_id,
                   dimension_template_id=request.dimension_template_id)
        
        service = ProductDimensionService(db)
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


@router.get("/variants/{variant_id}", response_model=List[Dict[str, Any]])
async def get_variant_dimensions(
    variant_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> List[Dict[str, Any]]:
    """获取SKU的所有维度值"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始获取SKU维度值", 
                   variant_id=variant_id)
        
        service = ProductDimensionService(db)
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
