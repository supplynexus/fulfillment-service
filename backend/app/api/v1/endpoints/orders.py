"""
Orders API endpoints with tenant isolation
"""

from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_async_db
from app.core.api_key_auth import get_api_key_auth, require_permission
from app.models.api_key import ApiKey
from app.models.tenant import Tenant
from app.models.customer import Customer
from app.models.order import Order
from app.schemas.order import OrderResponse, OrderListResponse

router = APIRouter()


@router.get("/orders", response_model=OrderListResponse)
async def get_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[ApiKey, Tenant] = Depends(require_permission("orders:read"))
) -> Any:
    """
    Get orders for the authenticated tenant
    """
    api_key, tenant = auth
    
    # Query orders for the specific tenant
    result = await db.execute(
        select(Order)
        .join(Customer)
        .where(Customer.tenant_id == tenant.id)
        .offset(skip)
        .limit(limit)
    )
    orders = result.scalars().all()
    
    return {
        "orders": orders,
        "total": len(orders),
        "skip": skip,
        "limit": limit
    }


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[ApiKey, Tenant] = Depends(require_permission("orders:read"))
) -> Any:
    """
    Get specific order for the authenticated tenant
    """
    api_key, tenant = auth
    
    # Query order for the specific tenant
    result = await db.execute(
        select(Order)
        .join(Customer)
        .where(Order.id == order_id, Customer.tenant_id == tenant.id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return order


@router.post("/orders/{order_id}/fulfill")
async def fulfill_order(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[ApiKey, Tenant] = Depends(require_permission("orders:write"))
) -> Any:
    """
    Fulfill an order (requires write permission)
    """
    api_key, tenant = auth
    
    # Query order for the specific tenant
    result = await db.execute(
        select(Order)
        .join(Customer)
        .where(Order.id == order_id, Customer.tenant_id == tenant.id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Update order status
    order.status = "fulfilled"
    await db.commit()
    
    return {"message": "Order fulfilled successfully"}


# Example of an endpoint that only allows frontend server access
@router.get("/orders/internal/stats")
async def get_order_stats(
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[ApiKey, Tenant] = Depends(require_frontend_server_key)
) -> Any:
    """
    Get internal order statistics (only accessible by frontend server)
    """
    api_key, tenant = auth
    
    # This endpoint is only accessible by frontend server API keys
    # It can provide more detailed statistics for the frontend dashboard
    
    # Query order statistics for the tenant
    result = await db.execute(
        select(Order)
        .join(Customer)
        .where(Customer.tenant_id == tenant.id)
    )
    orders = result.scalars().all()
    
    total_orders = len(orders)
    pending_orders = len([o for o in orders if o.status == "pending"])
    fulfilled_orders = len([o for o in orders if o.status == "fulfilled"])
    
    return {
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "fulfilled_orders": fulfilled_orders,
        "fulfillment_rate": fulfilled_orders / total_orders if total_orders > 0 else 0
    }