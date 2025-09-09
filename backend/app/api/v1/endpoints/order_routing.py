"""
Order routing API endpoints
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_async_db
from app.core.tenant_auth_dependency import verify_tenant_auth
from app.models.tenant import Tenant
from app.models.user import User
from app.models.order import Order
from app.schemas.scm_order import (
    OrderRoutingConfig,
    OrderRoutingResponse,
    BatchOrderRoutingConfig,
    BatchOrderRoutingResponse
)
from app.services.order_routing_service import OrderRoutingService
from app.tasks.order_routing_tasks import route_order_to_scm_task

router = APIRouter()


@router.post("/orders/{order_id}/route-to-scm", response_model=OrderRoutingResponse)
async def route_order_to_scm(
    order_id: int,
    routing_config: OrderRoutingConfig,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> OrderRoutingResponse:
    """
    将订单路由到SCM系统
    """
    tenant, user = auth
    
    # 获取订单
    result = await db.execute(
        select(Order).where(
            Order.id == order_id,
            Order.tenant_id == tenant.id
        )
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    try:
        # 路由服务
        routing_service = OrderRoutingService(db)
        scm_orders = await routing_service.route_order_to_scm(
            order, 
            routing_config,
            tenant.id
        )
        
        # 构建响应
        scm_order_responses = []
        for scm_order in scm_orders:
            scm_order_responses.append({
                "scm_order_id": scm_order.id,
                "scm_order_number": scm_order.scm_order_number,
                "target_system": scm_order.target_system_type,
                "status": scm_order.status,
                "line_items_count": len(scm_order.line_items),
                "total_amount": float(scm_order.total_amount)
            })
        
        # 计算路由摘要
        total_items = len(order.line_items)
        routed_items = sum(len(so.line_items) for so in scm_orders)
        
        routing_summary = {
            "total_items": total_items,
            "routed_items": routed_items,
            "created_orders": len(scm_orders),
            "routing_strategy": routing_config.routing_strategy
        }
        
        return OrderRoutingResponse(
            success=True,
            original_order_id=order_id,
            scm_orders=scm_order_responses,
            routing_summary=routing_summary
        )
        
    except Exception as e:
        return OrderRoutingResponse(
            success=False,
            original_order_id=order_id,
            scm_orders=[],
            routing_summary={},
            errors=[str(e)]
        )


@router.post("/orders/route-to-scm/batch", response_model=BatchOrderRoutingResponse)
async def batch_route_orders_to_scm(
    batch_config: BatchOrderRoutingConfig,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> BatchOrderRoutingResponse:
    """
    批量将订单路由到SCM系统
    """
    tenant, user = auth
    
    processed_orders = 0
    scm_orders_created = 0
    errors = []
    results = []
    
    for order_id in batch_config.order_ids:
        try:
            # 获取订单
            result = await db.execute(
                select(Order).where(
                    Order.id == order_id,
                    Order.tenant_id == tenant.id
                )
            )
            order = result.scalar_one_or_none()
            
            if not order:
                errors.append(f"Order {order_id} not found")
                continue
            
            # 创建路由配置
            routing_config = OrderRoutingConfig(
                routing_strategy=batch_config.routing_strategy,
                routing_rules=batch_config.batch_processing
            )
            
            # 路由服务
            routing_service = OrderRoutingService(db)
            scm_orders = await routing_service.route_order_to_scm(
                order, 
                routing_config,
                tenant.id
            )
            
            processed_orders += 1
            scm_orders_created += len(scm_orders)
            
            results.append({
                "order_id": order_id,
                "success": True,
                "scm_orders_created": len(scm_orders),
                "scm_order_ids": [so.id for so in scm_orders]
            })
            
        except Exception as e:
            errors.append(f"Failed to route order {order_id}: {str(e)}")
            results.append({
                "order_id": order_id,
                "success": False,
                "error": str(e)
            })
    
    return BatchOrderRoutingResponse(
        success=len(errors) == 0,
        processed_orders=processed_orders,
        total_orders=len(batch_config.order_ids),
        scm_orders_created=scm_orders_created,
        errors=errors,
        results=results
    )


@router.post("/orders/{order_id}/route-to-scm/background")
async def route_order_to_scm_background(
    order_id: int,
    routing_config: OrderRoutingConfig,
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    后台异步将订单路由到SCM系统
    """
    tenant, user = auth
    
    # 启动后台任务
    task = route_order_to_scm_task.delay(
        order_id=order_id,
        tenant_id=tenant.id,
        routing_config=routing_config.dict()
    )
    
    return {
        "message": "订单路由任务已启动",
        "task_id": task.id,
        "status": "PENDING"
    }


@router.get("/orders/{order_id}/routing-status")
async def get_order_routing_status(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    获取订单路由状态
    """
    tenant, user = auth
    
    # 验证订单存在
    result = await db.execute(
        select(Order).where(
            Order.id == order_id,
            Order.tenant_id == tenant.id
        )
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # 获取SCM订单
    routing_service = OrderRoutingService(db)
    scm_orders = await routing_service.get_scm_orders_by_order_id(order_id, tenant.id)
    
    # 构建状态信息
    status_info = {
        "order_id": order_id,
        "total_scm_orders": len(scm_orders),
        "scm_orders": []
    }
    
    for scm_order in scm_orders:
        status_info["scm_orders"].append({
            "scm_order_id": scm_order.id,
            "scm_order_number": scm_order.scm_order_number,
            "target_system": scm_order.target_system_type,
            "status": scm_order.status,
            "created_at": scm_order.created_at.isoformat(),
            "updated_at": scm_order.updated_at.isoformat() if scm_order.updated_at else None
        })
    
    return status_info
