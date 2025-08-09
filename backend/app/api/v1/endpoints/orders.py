"""
Order management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_async_db
from app.schemas.order import OrderResponse, OrderCreate, OrderUpdate
from app.services.order_service import OrderService
from app.tasks.order_tasks import process_order_fulfillment

router = APIRouter()


@router.get("/", response_model=List[OrderResponse])
async def get_orders(
    skip: int = 0,
    limit: int = 100,
    customer_id: int = None,
    status: str = None,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get orders with optional filtering
    """
    order_service = OrderService(db)
    orders = await order_service.get_multi(
        skip=skip, 
        limit=limit, 
        customer_id=customer_id,
        status=status
    )
    return orders


@router.post("/", response_model=OrderResponse)
async def create_order(
    order_in: OrderCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Create new order and trigger fulfillment process
    """
    order_service = OrderService(db)
    order = await order_service.create(obj_in=order_in)
    
    # Trigger async fulfillment processing
    background_tasks.add_task(process_order_fulfillment, order.id)
    
    return order


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get order by ID
    """
    order_service = OrderService(db)
    order = await order_service.get(id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/{order_id}/retry")
async def retry_order_fulfillment(
    order_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Retry failed order fulfillment
    """
    order_service = OrderService(db)
    order = await order_service.get(id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Trigger async fulfillment retry
    background_tasks.add_task(process_order_fulfillment, order.id)
    
    return {"message": "Order fulfillment retry initiated"}
