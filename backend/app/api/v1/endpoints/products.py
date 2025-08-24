"""
Product management endpoints
"""

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_async_db
from app.core.tenant_auth_dependency import verify_tenant_auth
from app.models.tenant import Tenant
from app.models.user import User
from app.models.external_system import ExternalSystem, ExternalSystemType
from app.schemas.product import ProductResponse
from app.services.printify_service import PrintifyService
from app.services.shopify.product_service import ShopifyProductService
from app.tasks.shopify_tasks import sync_shopify_products_task

router = APIRouter()


class ProductSyncResponse(BaseModel):
    success: bool
    products_fetched: int = 0
    products_saved: int = 0
    products_updated: int = 0
    errors: List[str] = []
    error: Optional[str] = None


@router.get("/", response_model=List[ProductResponse])
async def get_products(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    Get available products from Printify
    """
    tenant, user = auth
    
    # 从数据库获取 Printify external system 的 credentials
    stmt = select(ExternalSystem).where(
        ExternalSystem.tenant_id == tenant.id,
        ExternalSystem.system_type == ExternalSystemType.PRINTIFY,
        ExternalSystem.is_active == True
    )
    result = await db.execute(stmt)
    printify_system = result.scalar_one_or_none()
    
    if not printify_system or not printify_system.credentials.get("api_token"):
        raise HTTPException(status_code=400, detail="Printify API token not configured for this tenant")
    
    printify_service = PrintifyService(printify_system.credentials["api_token"])
    shop_id = printify_system.credentials.get("shop_id", "")
    products = await printify_service.get_products(shop_id)
    return products


@router.get("/catalog")
async def sync_product_catalog(
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    Sync product catalog from Printify
    """
    tenant, user = auth
    
    # 从数据库获取 Printify external system 的 credentials
    stmt = select(ExternalSystem).where(
        ExternalSystem.tenant_id == tenant.id,
        ExternalSystem.system_type == ExternalSystemType.PRINTIFY,
        ExternalSystem.is_active == True
    )
    result = await db.execute(stmt)
    printify_system = result.scalar_one_or_none()
    
    if not printify_system or not printify_system.credentials.get("api_token"):
        raise HTTPException(status_code=400, detail="Printify API token not configured for this tenant")
    
    printify_service = PrintifyService(printify_system.credentials["api_token"])
    shops = await printify_service.get_shops()
    return {"message": "Product catalog sync initiated", "shops": shops}


@router.post("/sync", response_model=ProductSyncResponse)
async def sync_shopify_products(
    sync_recent_only: bool = True,
    max_products: Optional[int] = 100,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> ProductSyncResponse:
    """
    手动触发Shopify商品同步
    
    Args:
        sync_recent_only: 是否只同步最近的商品（False表示完全重新同步）
        max_products: 最大商品数量（None表示不限制）
    """
    tenant, user = auth
    
    product_service = ShopifyProductService(db)
    
    try:
        result = await product_service.sync_products(
            tenant_id=tenant.id,
            sync_recent_only=sync_recent_only,
            max_products=max_products
        )
        
        return ProductSyncResponse(**result)
        
    except Exception as e:
        return ProductSyncResponse(
            success=False,
            error=str(e),
            products_fetched=0,
            products_saved=0,
            products_updated=0,
            errors=[str(e)]
        )


@router.post("/sync/background")
async def sync_shopify_products_background(
    sync_recent_only: bool = True,
    max_products: Optional[int] = 100,
    background_tasks: BackgroundTasks = None,
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    后台异步同步Shopify商品
    """
    tenant, user = auth
    
    # 启动后台任务
    task = sync_shopify_products_task.delay(
        tenant_id=tenant.id,
        sync_recent_only=sync_recent_only,
        max_products=max_products
    )
    
    return {
        "message": "商品同步任务已启动",
        "task_id": task.id,
        "status": "PENDING"
    }


@router.post("/sync/full")
async def full_sync_shopify_products(
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    完全重新同步所有Shopify商品（不限制数量和时间）
    """
    tenant, user = auth
    
    # 启动后台任务，完全重新同步
    task = sync_shopify_products_task.delay(
        tenant_id=tenant.id,
        sync_recent_only=False,  # 完全重新同步
        max_products=None  # 不限制数量
    )
    
    return {
        "message": "完全重新同步任务已启动",
        "task_id": task.id,
        "status": "PENDING",
        "sync_type": "full_resync"
    }
