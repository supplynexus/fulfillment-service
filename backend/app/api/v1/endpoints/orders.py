"""
Order management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

from app.core.database import get_async_db
from app.core.tenant_auth_dependency import verify_tenant_auth
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.order import OrderResponse, OrderListResponse, OrderSyncResponse
from app.services.shopify.order_service import ShopifyOrderService
from app.tasks.shopify_tasks import sync_shopify_orders_task

router = APIRouter()


@router.get("/", response_model=OrderListResponse)
async def get_orders(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> OrderListResponse:
    """
    获取订单列表
    """
    tenant, user = auth
    
    order_service = ShopifyOrderService(db)
    
    if status:
        orders = await order_service.get_orders_by_status(
            tenant_id=tenant.id,
            status=status,
            limit=limit
        )
        total = len(orders)
    else:
        orders = await order_service.get_recent_orders(
            tenant_id=tenant.id,
            hours=24,
            limit=limit
        )
        total = len(orders)
    
    # 转换为响应格式
    order_responses = []
    for order in orders:
        order_responses.append(OrderResponse.from_orm(order))
    
    return OrderListResponse(
        orders=order_responses,
        total=total,
        skip=skip,
        limit=limit
    )


@router.post("/sync", response_model=OrderSyncResponse)
async def sync_orders(
    sync_recent_only: bool = True,
    max_orders: Optional[int] = 100,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> OrderSyncResponse:
    """
    手动触发订单同步
    """
    tenant, user = auth
    
    order_service = ShopifyOrderService(db)
    
    try:
        result = await order_service.sync_orders(
            tenant_id=tenant.id,
            sync_recent_only=sync_recent_only,
            max_orders=max_orders
        )
        
        return OrderSyncResponse(**result)
        
    except Exception as e:
        return OrderSyncResponse(
            success=False,
            error=str(e),
            orders_fetched=0,
            orders_saved=0,
            orders_updated=0,
            errors=[str(e)]
        )


@router.post("/sync/background")
async def sync_orders_background(
    sync_recent_only: bool = True,
    max_orders: Optional[int] = 100,
    background_tasks: BackgroundTasks = None,
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    后台异步同步订单
    """
    tenant, user = auth
    
    # 启动后台任务
    task = sync_shopify_orders_task.delay(
        tenant_id=tenant.id,
        sync_recent_only=sync_recent_only,
        max_orders=max_orders
    )
    
    return {
        "message": "订单同步任务已启动",
        "task_id": task.id,
        "status": "PENDING"
    }


@router.post("/sync/full")
async def full_sync_orders(
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    完全重新同步所有Shopify订单（不限制数量和时间）
    """
    tenant, user = auth
    
    # 启动后台任务，完全重新同步
    task = sync_shopify_orders_task.delay(
        tenant_id=tenant.id,
        sync_recent_only=False,  # 完全重新同步
        max_orders=None  # 不限制数量
    )
    
    return {
        "message": "完全重新同步任务已启动",
        "task_id": task.id,
        "status": "PENDING",
        "sync_type": "full_resync"
    }


@router.get("/recent", response_model=List[OrderResponse])
async def get_recent_orders(
    hours: int = 24,
    limit: int = 50,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> List[OrderResponse]:
    """
    获取最近的订单
    """
    tenant, user = auth
    
    order_service = ShopifyOrderService(db)
    orders = await order_service.get_recent_orders(
        tenant_id=tenant.id,
        hours=hours,
        limit=limit
    )
    
    return [OrderResponse.from_orm(order) for order in orders]


@router.get("/status/{status}", response_model=List[OrderResponse])
async def get_orders_by_status(
    status: str,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> List[OrderResponse]:
    """
    根据状态获取订单
    """
    tenant, user = auth
    
    order_service = ShopifyOrderService(db)
    orders = await order_service.get_orders_by_status(
        tenant_id=tenant.id,
        status=status,
        limit=limit
    )
    
    return [OrderResponse.from_orm(order) for order in orders]