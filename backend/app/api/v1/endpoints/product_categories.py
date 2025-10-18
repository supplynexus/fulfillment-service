"""
Product Categories API - 产品分类管理 API

实现功能：
1. 分类的 CRUD 操作
2. 分类树查询
3. 分类关系管理
4. 分类维度管理
5. 分类切换分析
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import logging

from app.schemas.base import BaseResponse

from app.core.database import get_async_db
from app.core.jwt_auth_dependency import verify_jwt_auth
from app.services.product_category_service import ProductCategoryService
from app.services.product_category_switch_service import ProductCategorySwitchService
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# Pydantic Models
class CategoryCreateRequest(BaseModel):
    category_code: str = Field(..., description="分类编码")
    category_name: str = Field(..., description="分类名称")
    description: Optional[str] = Field(None, description="描述")
    parent_category_ids: Optional[List[int]] = Field(None, description="父分类ID列表")
    is_root: bool = Field(False, description="是否为根分类")
    sort_order: int = Field(0, description="排序")


class CategoryUpdateRequest(BaseModel):
    category_name: Optional[str] = Field(None, description="分类名称")
    description: Optional[str] = Field(None, description="描述")
    sort_order: Optional[int] = Field(None, description="排序")
    is_active: Optional[bool] = Field(None, description="是否激活")


class CategoryResponse(BaseResponse):
    id: int
    category_code: str
    category_name: str
    description: Optional[str]
    is_root: bool
    sort_order: int
    is_active: bool
    children: Optional[List['CategoryResponse']] = None


class CategoryTreeResponse(BaseModel):
    categories: List[CategoryResponse]


class CategoryRelationRequest(BaseModel):
    parent_category_id: int = Field(..., description="父分类ID")
    child_category_id: int = Field(..., description="子分类ID")


class CategoryPathResponse(BaseModel):
    path: List[CategoryResponse]


class CategorySwitchAnalysisRequest(BaseModel):
    product_id: int = Field(..., description="产品ID")
    new_category_id: int = Field(..., description="新分类ID")


class CategorySwitchRequest(BaseModel):
    product_id: int = Field(..., description="产品ID")
    new_category_id: int = Field(..., description="新分类ID")
    migration_strategy: str = Field("auto", description="迁移策略")
    preserve_incompatible_dimensions: bool = Field(True, description="是否保留不兼容维度")


# API Endpoints
@router.post("/", response_model=CategoryResponse)
async def create_category(
    request: CategoryCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> CategoryResponse:
    """创建产品分类"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始创建产品分类", 
                   tenant_id=tenant.id,
                   category_code=request.category_code)
        
        service = ProductCategoryService(db)
        category = await service.create_category(
            tenant_id=tenant.id,
            category_code=request.category_code,
            category_name=request.category_name,
            description=request.description,
            parent_category_ids=request.parent_category_ids,
            is_root=request.is_root,
            sort_order=request.sort_order
        )
        
        logger.info("✅ 产品分类创建成功", 
                   category_id=category.id,
                   category_code=category.category_code)
        
        return CategoryResponse.from_orm(category)
        
    except ValueError as e:
        logger.error("❌ 产品分类创建失败", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("❌ 产品分类创建异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"创建分类失败: {str(e)}")


@router.get("/", response_model=CategoryTreeResponse)
async def get_category_tree(
    include_inactive: bool = Query(False, description="是否包含非激活分类"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> CategoryTreeResponse:
    """获取分类树"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始获取分类树", 
                   tenant_id=tenant.id,
                   include_inactive=include_inactive)
        
        service = ProductCategoryService(db)
        categories = await service.get_category_tree(tenant.id, include_inactive)
        
        logger.info("✅ 分类树获取成功", 
                   tenant_id=tenant.id,
                   category_count=len(categories))
        
        return CategoryTreeResponse(categories=categories)
        
    except Exception as e:
        logger.error("❌ 分类树获取异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取分类树失败: {str(e)}")


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> CategoryResponse:
    """获取单个分类"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始获取分类", 
                   category_id=category_id,
                   tenant_id=tenant.id)
        
        service = ProductCategoryService(db)
        category = await service.get_category_by_id(category_id, tenant.id)
        
        if not category:
            raise HTTPException(status_code=404, detail="分类不存在")
        
        logger.info("✅ 分类获取成功", category_id=category_id)
        
        return CategoryResponse.from_orm(category)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ 分类获取异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取分类失败: {str(e)}")


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    request: CategoryUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> CategoryResponse:
    """更新分类"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始更新分类", 
                   category_id=category_id,
                   tenant_id=tenant.id)
        
        service = ProductCategoryService(db)
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        
        category = await service.update_category(category_id, tenant.id, **update_data)
        
        if not category:
            raise HTTPException(status_code=404, detail="分类不存在")
        
        logger.info("✅ 分类更新成功", category_id=category_id)
        
        return CategoryResponse.from_orm(category)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ 分类更新异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"更新分类失败: {str(e)}")


@router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    force: bool = Query(False, description="是否强制删除"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> Dict[str, Any]:
    """删除分类"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始删除分类", 
                   category_id=category_id,
                   force=force,
                   tenant_id=tenant.id)
        
        service = ProductCategoryService(db)
        success = await service.delete_category(category_id, tenant.id, force)
        
        if not success:
            raise HTTPException(status_code=404, detail="分类不存在")
        
        logger.info("✅ 分类删除成功", category_id=category_id)
        
        return {"success": True, "message": "分类删除成功"}
        
    except ValueError as e:
        logger.error("❌ 分类删除失败", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ 分类删除异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"删除分类失败: {str(e)}")


@router.get("/{category_id}/path", response_model=CategoryPathResponse)
async def get_category_path(
    category_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> CategoryPathResponse:
    """获取分类路径"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始获取分类路径", 
                   category_id=category_id,
                   tenant_id=tenant.id)
        
        service = ProductCategoryService(db)
        path = await service.get_category_path(category_id, tenant.id)
        
        logger.info("✅ 分类路径获取成功", 
                   category_id=category_id,
                   path_length=len(path))
        
        return CategoryPathResponse(path=[CategoryResponse.from_orm(cat) for cat in path])
        
    except Exception as e:
        logger.error("❌ 分类路径获取异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取分类路径失败: {str(e)}")


@router.post("/relations", response_model=Dict[str, Any])
async def add_category_relation(
    request: CategoryRelationRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> Dict[str, Any]:
    """添加分类关系"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始添加分类关系", 
                   parent_id=request.parent_category_id,
                   child_id=request.child_category_id,
                   tenant_id=tenant.id)
        
        service = ProductCategoryService(db)
        relation = await service.add_parent_relation(
            request.child_category_id,
            request.parent_category_id,
            tenant.id
        )
        
        logger.info("✅ 分类关系添加成功")
        
        return {"success": True, "message": "分类关系添加成功", "relation_id": relation.id}
        
    except ValueError as e:
        logger.error("❌ 分类关系添加失败", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("❌ 分类关系添加异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"添加分类关系失败: {str(e)}")


@router.delete("/relations")
async def remove_category_relation(
    parent_category_id: int = Query(..., description="父分类ID"),
    child_category_id: int = Query(..., description="子分类ID"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> Dict[str, Any]:
    """移除分类关系"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始移除分类关系", 
                   parent_id=parent_category_id,
                   child_id=child_category_id,
                   tenant_id=tenant.id)
        
        service = ProductCategoryService(db)
        success = await service.remove_parent_relation(child_category_id, parent_category_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="分类关系不存在")
        
        logger.info("✅ 分类关系移除成功")
        
        return {"success": True, "message": "分类关系移除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ 分类关系移除异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"移除分类关系失败: {str(e)}")


@router.post("/switch/analyze", response_model=Dict[str, Any])
async def analyze_category_switch(
    request: CategorySwitchAnalysisRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> Dict[str, Any]:
    """分析分类切换影响"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始分析分类切换", 
                   product_id=request.product_id,
                   new_category_id=request.new_category_id,
                   tenant_id=tenant.id)
        
        service = ProductCategorySwitchService(db)
        analysis = await service.analyze_category_switch(
            request.product_id,
            request.new_category_id,
            tenant.id
        )
        
        logger.info("✅ 分类切换分析完成", 
                   product_id=request.product_id,
                   new_category_id=request.new_category_id)
        
        return analysis
        
    except ValueError as e:
        logger.error("❌ 分类切换分析失败", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("❌ 分类切换分析异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"分析分类切换失败: {str(e)}")


@router.post("/switch/execute", response_model=Dict[str, Any])
async def execute_category_switch(
    request: CategorySwitchRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> Dict[str, Any]:
    """执行分类切换"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始执行分类切换", 
                   product_id=request.product_id,
                   new_category_id=request.new_category_id,
                   migration_strategy=request.migration_strategy,
                   tenant_id=tenant.id)
        
        service = ProductCategorySwitchService(db)
        result = await service.switch_product_category(
            request.product_id,
            request.new_category_id,
            tenant.id,
            request.migration_strategy,
            request.preserve_incompatible_dimensions,
            user.id
        )
        
        logger.info("✅ 分类切换执行完成", 
                   product_id=request.product_id,
                   new_category_id=request.new_category_id,
                   success=result["switch_successful"])
        
        return result
        
    except ValueError as e:
        logger.error("❌ 分类切换执行失败", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("❌ 分类切换执行异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"执行分类切换失败: {str(e)}")


@router.get("/{category_id}/dimensions", response_model=List[Dict[str, Any]])
async def get_category_dimensions(
    category_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> List[Dict[str, Any]]:
    """获取分类的维度"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始获取分类维度", 
                   category_id=category_id,
                   tenant_id=tenant.id)
        
        service = ProductCategoryService(db)
        dimensions = await service.get_category_dimensions(category_id, tenant.id)
        
        logger.info("✅ 分类维度获取成功", 
                   category_id=category_id,
                   dimension_count=len(dimensions))
        
        return dimensions
        
    except Exception as e:
        logger.error("❌ 分类维度获取异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取分类维度失败: {str(e)}")
