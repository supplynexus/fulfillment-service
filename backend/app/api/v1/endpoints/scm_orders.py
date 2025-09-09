"""
SCM Orders API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_async_db
from app.core.tenant_auth_dependency import verify_tenant_auth
from app.models.tenant import Tenant
from app.models.user import User
from app.models.order import Order
from app.models.scm_order import SCMOrder
from app.schemas.scm_order import (
    SCMOrderResponse, 
    SCMOrderListResponse,
    SCMOrderCreate
)
from app.services.order_routing_service import OrderRoutingService

router = APIRouter()


@router.get("/", response_model=SCMOrderListResponse)
async def get_scm_orders(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    status: Optional[str] = Query(None, description="Filter by status"),
    target_system_type: Optional[str] = Query(None, description="Filter by target system type"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> SCMOrderListResponse:
    """
    获取SCM订单列表
    """
    from app.core.logging import RequestLogger
    logger = RequestLogger("scm_orders.get_scm_orders")
    
    try:
        logger.info(f"🔍 开始处理SCM订单列表请求: skip={skip}, limit={limit}, status={status}, target_system_type={target_system_type}")
        
        tenant, user = auth
        logger.info(f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}")
        
        # 构建查询
        logger.info(f"🔍 构建SCM订单查询...")
        query = select(SCMOrder).where(SCMOrder.tenant_id == tenant.id)
        
        # 应用过滤器
        if status:
            query = query.where(SCMOrder.status == status)
            logger.info(f"🔍 应用状态过滤器: status={status}")
        if target_system_type:
            query = query.where(SCMOrder.target_system_type == target_system_type)
            logger.info(f"🔍 应用系统类型过滤器: target_system_type={target_system_type}")
        
        # 获取总数
        logger.info(f"🔍 查询SCM订单总数...")
        try:
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar()
            logger.info(f"✅ 查询总数成功: total={total}")
        except Exception as e:
            logger.error(f"❌ 查询总数失败: {str(e)}")
            import traceback
            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Failed to get SCM orders count: {str(e)}")
        
        # 分页查询
        logger.info(f"🔍 执行分页查询: skip={skip}, limit={limit}")
        try:
            query = query.order_by(SCMOrder.created_at.desc()).offset(skip).limit(limit)
            result = await db.execute(query)
            scm_orders = result.scalars().all()
            logger.info(f"✅ 分页查询成功: 找到 {len(scm_orders)} 个SCM订单")
        except Exception as e:
            logger.error(f"❌ 分页查询失败: {str(e)}")
            import traceback
            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Failed to get SCM orders: {str(e)}")
        
        # 转换为响应格式
        logger.info(f"🔍 转换SCM订单响应格式...")
        try:
            scm_order_responses = [
                SCMOrderResponse.from_orm(scm_order) for scm_order in scm_orders
            ]
            logger.info(f"✅ 响应格式转换成功: {len(scm_order_responses)} 个SCM订单")
        except Exception as e:
            logger.error(f"❌ 转换响应格式失败: {str(e)}")
            import traceback
            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Failed to convert SCM order responses: {str(e)}")
        
        result = SCMOrderListResponse(
            scm_orders=scm_order_responses,
            total=total,
            skip=skip,
            limit=limit
        )
        
        logger.info(f"✅ SCM订单列表请求处理成功: total={total}, skip={skip}, limit={limit}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ SCM订单列表请求处理失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{scm_order_id}", response_model=SCMOrderResponse)
async def get_scm_order(
    scm_order_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> SCMOrderResponse:
    """
    获取SCM订单详情
    """
    tenant, user = auth
    
    result = await db.execute(
        select(SCMOrder).where(
            SCMOrder.id == scm_order_id,
            SCMOrder.tenant_id == tenant.id
        )
    )
    scm_order = result.scalar_one_or_none()
    
    if not scm_order:
        raise HTTPException(status_code=404, detail="SCM order not found")
    
    return SCMOrderResponse.from_orm(scm_order)


@router.get("/order/{order_id}", response_model=List[SCMOrderResponse])
async def get_scm_orders_by_order_id(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> List[SCMOrderResponse]:
    """
    根据原始订单ID获取SCM订单
    """
    tenant, user = auth
    
    # 验证原始订单存在
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
    
    return [SCMOrderResponse.from_orm(scm_order) for scm_order in scm_orders]


@router.post("/", response_model=SCMOrderResponse)
async def create_scm_order(
    scm_order_data: SCMOrderCreate,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> SCMOrderResponse:
    """
    手动创建SCM订单
    """
    tenant, user = auth
    
    # 验证原始订单存在
    result = await db.execute(
        select(Order).where(
            Order.id == scm_order_data.source_order_id,
            Order.tenant_id == tenant.id
        )
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Source order not found")
    
    # 创建SCM订单
    scm_order = SCMOrder(
        tenant_id=tenant.id,
        source_order_id=scm_order_data.source_order_id,
        target_system_type=scm_order_data.target_system_type,
        target_system_id=scm_order_data.target_system_id,
        routing_strategy=scm_order_data.routing_strategy,
        line_items=scm_order_data.line_items,
        total_amount=scm_order_data.total_amount,
        currency=scm_order_data.currency,
        customer_email=scm_order_data.customer_email,
        customer_name=scm_order_data.customer_name,
        customer_phone=scm_order_data.customer_phone,
        shipping_address=scm_order_data.shipping_address,
        billing_address=scm_order_data.billing_address,
        routing_metadata=scm_order_data.routing_metadata
    )
    
    db.add(scm_order)
    await db.commit()
    await db.refresh(scm_order)
    
    return SCMOrderResponse.from_orm(scm_order)


@router.put("/{scm_order_id}", response_model=SCMOrderResponse)
async def update_scm_order(
    scm_order_id: int,
    status: Optional[str] = None,
    target_system_id: Optional[str] = None,
    tracking_number: Optional[str] = None,
    tracking_url: Optional[str] = None,
    fulfillment_status: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> SCMOrderResponse:
    """
    更新SCM订单
    """
    tenant, user = auth
    
    routing_service = OrderRoutingService(db)
    
    # 准备更新字段
    update_fields = {}
    if status is not None:
        update_fields["status"] = status
    if target_system_id is not None:
        update_fields["target_system_id"] = target_system_id
    if tracking_number is not None:
        update_fields["tracking_number"] = tracking_number
    if tracking_url is not None:
        update_fields["tracking_url"] = tracking_url
    if fulfillment_status is not None:
        update_fields["fulfillment_status"] = fulfillment_status
    
    scm_order = await routing_service.update_scm_order_status(
        scm_order_id, 
        status or "updated", 
        tenant.id,
        **update_fields
    )
    
    if not scm_order:
        raise HTTPException(status_code=404, detail="SCM order not found")
    
    return SCMOrderResponse.from_orm(scm_order)


@router.delete("/{scm_order_id}")
async def delete_scm_order(
    scm_order_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    删除SCM订单
    """
    tenant, user = auth
    
    result = await db.execute(
        select(SCMOrder).where(
            SCMOrder.id == scm_order_id,
            SCMOrder.tenant_id == tenant.id
        )
    )
    scm_order = result.scalar_one_or_none()
    
    if not scm_order:
        raise HTTPException(status_code=404, detail="SCM order not found")
    
    # 检查是否可以删除（只有创建状态的订单可以删除）
    if scm_order.status not in ["created", "failed"]:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete SCM order with status: " + scm_order.status
        )
    
    await db.delete(scm_order)
    await db.commit()
    
    return {"message": "SCM order deleted successfully"}
