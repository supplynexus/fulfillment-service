"""
Shopify Orders CRUD API endpoints
专门处理 Shopify 订单的 CRUD 操作
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_async_db
from app.core.tenant_auth_dependency import verify_tenant_auth
from app.core.logging import get_logger
from app.core.hashids_utils import encode_id, decode_id
from app.models.tenant import Tenant
from app.models.user import User
from app.models.shopify_order import ShopifyOrder
from app.schemas.shopify_order import (
    ShopifyOrderCreate,
    ShopifyOrderUpdate,
    ShopifyOrderResponse,
    ShopifyOrderListResponse,
    ShopifyOrderSyncResponse,
    ShopifyOrderStatisticsResponse
)

router = APIRouter()
logger = get_logger(__name__)


@router.get("/", response_model=ShopifyOrderListResponse)
async def get_shopify_orders(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(10, ge=1, le=100, description="每页记录数"),
    financial_status: Optional[str] = Query(None, description="财务状态过滤"),
    fulfillment_status: Optional[str] = Query(None, description="履行状态过滤"),
    confirmed: Optional[bool] = Query(None, description="是否确认过滤"),
    closed: Optional[bool] = Query(None, description="是否关闭过滤"),
    cancelled: Optional[bool] = Query(None, description="是否取消过滤"),
    search: Optional[str] = Query(None, description="搜索关键词（订单名称、确认号、客户邮箱）"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向（asc/desc）"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    获取 Shopify 订单列表
    
    支持多种过滤条件和搜索功能
    """
    tenant, user = auth
    
    try:
        logger.info(f"🔍 开始获取 Shopify 订单列表: tenant_id={tenant.id}, user_id={user.id}")
        logger.info(f"   过滤条件: financial_status={financial_status}, fulfillment_status={fulfillment_status}")
        logger.info(f"   分页: skip={skip}, limit={limit}")
        
        # 构建基础查询
        query = select(ShopifyOrder).where(ShopifyOrder.tenant_id == tenant.id)
        
        # 应用过滤条件
        if financial_status:
            query = query.where(ShopifyOrder.financial_status == financial_status)
        if fulfillment_status:
            query = query.where(ShopifyOrder.fulfillment_status == fulfillment_status)
        if confirmed is not None:
            query = query.where(ShopifyOrder.confirmed == confirmed)
        if closed is not None:
            query = query.where(ShopifyOrder.closed == closed)
        if cancelled is not None:
            query = query.where(ShopifyOrder.cancelled == cancelled)
        
        # 搜索功能
        if search:
            search_filter = or_(
                ShopifyOrder.name.ilike(f"%{search}%"),
                ShopifyOrder.confirmation_number.ilike(f"%{search}%"),
                ShopifyOrder.customer_data["email"].astext.ilike(f"%{search}%")
            )
            query = query.where(search_filter)
        
        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # 排序
        if sort_by == "created_at":
            order_column = ShopifyOrder.created_at
        elif sort_by == "updated_at":
            order_column = ShopifyOrder.updated_at
        elif sort_by == "name":
            order_column = ShopifyOrder.name
        elif sort_by == "total_price":
            order_column = ShopifyOrder.total_price
        else:
            order_column = ShopifyOrder.created_at
        
        if sort_order == "asc":
            query = query.order_by(order_column.asc())
        else:
            query = query.order_by(order_column.desc())
        
        # 分页
        query = query.offset(skip).limit(limit)
        
        # 执行查询
        result = await db.execute(query)
        orders = result.scalars().all()
        
        # 转换为响应格式
        order_responses = []
        for order in orders:
            order_responses.append(ShopifyOrderResponse(
                id=order.id,
                tenant_id=order.tenant_id,
                shopify_order_id=order.shopify_order_id,
                name=order.name,
                confirmation_number=order.confirmation_number,
                financial_status=order.financial_status,
                fulfillment_status=order.fulfillment_status,
                confirmed=order.confirmed,
                closed=order.closed,
                cancelled=order.cancelled,
                currency_code=order.currency_code,
                total_price=float(order.total_price) if order.total_price else None,
                subtotal_price=float(order.subtotal_price) if order.subtotal_price else None,
                total_tax=float(order.total_tax) if order.total_tax else None,
                total_shipping=float(order.total_shipping) if order.total_shipping else None,
                tags=order.tags,
                note=order.note,
                customer_data=order.customer_data,
                billing_address=order.billing_address,
                shipping_address=order.shipping_address,
                line_items=order.line_items,
                fulfillments=order.fulfillments,
                refunds=order.refunds,
                raw_data=order.raw_data,
                created_at=order.created_at,
                updated_at=order.updated_at,
                last_synced_at=order.last_synced_at
            ))
        
        logger.info(f"✅ 获取 Shopify 订单列表成功: 总数={total}, 返回={len(order_responses)}")
        
        return ShopifyOrderListResponse(
            orders=order_responses,
            total=total,
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"❌ 获取 Shopify 订单列表失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to get Shopify orders: {str(e)}")


@router.get("/{order_hashid}", response_model=ShopifyOrderResponse)
async def get_shopify_order(
    order_hashid: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    获取单个 Shopify 订单详情
    """
    tenant, user = auth
    
    try:
        logger.info(f"🔍 开始获取 Shopify 订单详情: order_hashid={order_hashid}, tenant_id={tenant.id}")
        
        # 解码 hashid
        try:
            order_id = decode_id(order_hashid)
            logger.info(f"✅ Hashid 解码成功: {order_hashid} -> {order_id}")
        except Exception as e:
            logger.error(f"❌ Hashid 解码失败: {order_hashid}, 错误: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid order ID")
        
        # 查询订单
        query = select(ShopifyOrder).where(
            and_(
                ShopifyOrder.id == order_id,
                ShopifyOrder.tenant_id == tenant.id
            )
        )
        result = await db.execute(query)
        order = result.scalar_one_or_none()
        
        if not order:
            logger.error(f"❌ Shopify 订单不存在: order_id={order_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="Shopify order not found")
        
        logger.info(f"✅ 获取 Shopify 订单详情成功: {order.name}")
        
        return ShopifyOrderResponse(
            id=order.id,
            tenant_id=order.tenant_id,
            shopify_order_id=order.shopify_order_id,
            name=order.name,
            confirmation_number=order.confirmation_number,
            financial_status=order.financial_status,
            fulfillment_status=order.fulfillment_status,
            confirmed=order.confirmed,
            closed=order.closed,
            cancelled=order.cancelled,
            currency_code=order.currency_code,
            total_price=float(order.total_price) if order.total_price else None,
            subtotal_price=float(order.subtotal_price) if order.subtotal_price else None,
            total_tax=float(order.total_tax) if order.total_tax else None,
            total_shipping=float(order.total_shipping) if order.total_shipping else None,
            tags=order.tags,
            note=order.note,
            customer_data=order.customer_data,
            billing_address=order.billing_address,
            shipping_address=order.shipping_address,
            line_items=order.line_items,
            fulfillments=order.fulfillments,
            refunds=order.refunds,
            raw_data=order.raw_data,
            created_at=order.created_at,
            updated_at=order.updated_at,
            last_synced_at=order.last_synced_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取 Shopify 订单详情失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to get Shopify order: {str(e)}")


@router.post("/", response_model=ShopifyOrderResponse)
async def create_shopify_order(
    order_data: ShopifyOrderCreate,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    创建新的 Shopify 订单
    """
    tenant, user = auth
    
    try:
        logger.info(f"🔍 开始创建 Shopify 订单: tenant_id={tenant.id}, user_id={user.id}")
        logger.info(f"   Shopify 订单 ID: {order_data.shopify_order_id}")
        
        # 检查 Shopify 订单 ID 是否已存在
        existing_query = select(ShopifyOrder).where(
            and_(
                ShopifyOrder.tenant_id == tenant.id,
                ShopifyOrder.shopify_order_id == order_data.shopify_order_id
            )
        )
        existing_result = await db.execute(existing_query)
        existing_order = existing_result.scalar_one_or_none()
        
        if existing_order:
            logger.error(f"❌ Shopify 订单已存在: {order_data.shopify_order_id}")
            raise HTTPException(status_code=400, detail="Shopify order already exists")
        
        # 创建订单
        order = ShopifyOrder(
            tenant_id=tenant.id,
            shopify_order_id=order_data.shopify_order_id,
            name=order_data.name,
            confirmation_number=order_data.confirmation_number,
            financial_status=order_data.financial_status,
            fulfillment_status=order_data.fulfillment_status,
            confirmed=order_data.confirmed,
            closed=order_data.closed,
            cancelled=order_data.cancelled,
            currency_code=order_data.currency_code,
            total_price=order_data.total_price,
            subtotal_price=order_data.subtotal_price,
            total_tax=order_data.total_tax,
            total_shipping=order_data.total_shipping,
            tags=order_data.tags,
            note=order_data.note,
            customer_data=order_data.customer_data,
            billing_address=order_data.billing_address,
            shipping_address=order_data.shipping_address,
            line_items=order_data.line_items,
            fulfillments=order_data.fulfillments,
            refunds=order_data.refunds,
            raw_data=order_data.raw_data
        )
        
        db.add(order)
        await db.flush()  # 获取 ID
        await db.commit()
        
        logger.info(f"✅ Shopify 订单创建成功: {order.name} (ID: {order.id})")
        
        return ShopifyOrderResponse(
            id=order.id,
            tenant_id=order.tenant_id,
            shopify_order_id=order.shopify_order_id,
            name=order.name,
            confirmation_number=order.confirmation_number,
            financial_status=order.financial_status,
            fulfillment_status=order.fulfillment_status,
            confirmed=order.confirmed,
            closed=order.closed,
            cancelled=order.cancelled,
            currency_code=order.currency_code,
            total_price=float(order.total_price) if order.total_price else None,
            subtotal_price=float(order.subtotal_price) if order.subtotal_price else None,
            total_tax=float(order.total_tax) if order.total_tax else None,
            total_shipping=float(order.total_shipping) if order.total_shipping else None,
            tags=order.tags,
            note=order.note,
            customer_data=order.customer_data,
            billing_address=order.billing_address,
            shipping_address=order.shipping_address,
            line_items=order.line_items,
            fulfillments=order.fulfillments,
            refunds=order.refunds,
            raw_data=order.raw_data,
            created_at=order.created_at,
            updated_at=order.updated_at,
            last_synced_at=order.last_synced_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ 创建 Shopify 订单失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to create Shopify order: {str(e)}")


@router.put("/{order_hashid}", response_model=ShopifyOrderResponse)
async def update_shopify_order(
    order_hashid: str,
    order_data: ShopifyOrderUpdate,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    更新 Shopify 订单
    """
    tenant, user = auth
    
    try:
        logger.info(f"🔍 开始更新 Shopify 订单: order_hashid={order_hashid}, tenant_id={tenant.id}")
        
        # 解码 hashid
        try:
            order_id = decode_id(order_hashid)
            logger.info(f"✅ Hashid 解码成功: {order_hashid} -> {order_id}")
        except Exception as e:
            logger.error(f"❌ Hashid 解码失败: {order_hashid}, 错误: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid order ID")
        
        # 查询订单
        query = select(ShopifyOrder).where(
            and_(
                ShopifyOrder.id == order_id,
                ShopifyOrder.tenant_id == tenant.id
            )
        )
        result = await db.execute(query)
        order = result.scalar_one_or_none()
        
        if not order:
            logger.error(f"❌ Shopify 订单不存在: order_id={order_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="Shopify order not found")
        
        # 更新字段
        update_data = order_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(order, field):
                setattr(order, field, value)
        
        await db.commit()
        
        logger.info(f"✅ Shopify 订单更新成功: {order.name}")
        
        return ShopifyOrderResponse(
            id=order.id,
            tenant_id=order.tenant_id,
            shopify_order_id=order.shopify_order_id,
            name=order.name,
            confirmation_number=order.confirmation_number,
            financial_status=order.financial_status,
            fulfillment_status=order.fulfillment_status,
            confirmed=order.confirmed,
            closed=order.closed,
            cancelled=order.cancelled,
            currency_code=order.currency_code,
            total_price=float(order.total_price) if order.total_price else None,
            subtotal_price=float(order.subtotal_price) if order.subtotal_price else None,
            total_tax=float(order.total_tax) if order.total_tax else None,
            total_shipping=float(order.total_shipping) if order.total_shipping else None,
            tags=order.tags,
            note=order.note,
            customer_data=order.customer_data,
            billing_address=order.billing_address,
            shipping_address=order.shipping_address,
            line_items=order.line_items,
            fulfillments=order.fulfillments,
            refunds=order.refunds,
            raw_data=order.raw_data,
            created_at=order.created_at,
            updated_at=order.updated_at,
            last_synced_at=order.last_synced_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ 更新 Shopify 订单失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to update Shopify order: {str(e)}")


@router.delete("/{order_hashid}")
async def delete_shopify_order(
    order_hashid: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    删除 Shopify 订单
    """
    tenant, user = auth
    
    try:
        logger.info(f"🔍 开始删除 Shopify 订单: order_hashid={order_hashid}, tenant_id={tenant.id}")
        
        # 解码 hashid
        try:
            order_id = decode_id(order_hashid)
            logger.info(f"✅ Hashid 解码成功: {order_hashid} -> {order_id}")
        except Exception as e:
            logger.error(f"❌ Hashid 解码失败: {order_hashid}, 错误: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid order ID")
        
        # 查询订单
        query = select(ShopifyOrder).where(
            and_(
                ShopifyOrder.id == order_id,
                ShopifyOrder.tenant_id == tenant.id
            )
        )
        result = await db.execute(query)
        order = result.scalar_one_or_none()
        
        if not order:
            logger.error(f"❌ Shopify 订单不存在: order_id={order_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="Shopify order not found")
        
        # 删除订单
        await db.delete(order)
        await db.commit()
        
        logger.info(f"✅ Shopify 订单删除成功: {order.name}")
        
        return {"message": "Shopify order deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ 删除 Shopify 订单失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to delete Shopify order: {str(e)}")


@router.get("/statistics/overview", response_model=ShopifyOrderStatisticsResponse)
async def get_shopify_order_statistics(
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    获取 Shopify 订单统计信息
    """
    tenant, user = auth
    
    try:
        logger.info(f"🔍 开始获取 Shopify 订单统计: tenant_id={tenant.id}")
        
        # 总订单数
        total_query = select(func.count(ShopifyOrder.id)).where(ShopifyOrder.tenant_id == tenant.id)
        total_result = await db.execute(total_query)
        total_orders = total_result.scalar()
        
        # 按状态统计
        status_query = select(
            ShopifyOrder.fulfillment_status,
            func.count(ShopifyOrder.id)
        ).where(ShopifyOrder.tenant_id == tenant.id).group_by(ShopifyOrder.fulfillment_status)
        status_result = await db.execute(status_query)
        orders_by_status = {row[0] or "unknown": row[1] for row in status_result}
        
        # 按财务状态统计
        financial_query = select(
            ShopifyOrder.financial_status,
            func.count(ShopifyOrder.id)
        ).where(ShopifyOrder.tenant_id == tenant.id).group_by(ShopifyOrder.financial_status)
        financial_result = await db.execute(financial_query)
        orders_by_financial_status = {row[0] or "unknown": row[1] for row in financial_result}
        
        # 按履行状态统计
        fulfillment_query = select(
            ShopifyOrder.fulfillment_status,
            func.count(ShopifyOrder.id)
        ).where(ShopifyOrder.tenant_id == tenant.id).group_by(ShopifyOrder.fulfillment_status)
        fulfillment_result = await db.execute(fulfillment_query)
        orders_by_fulfillment_status = {row[0] or "unknown": row[1] for row in fulfillment_result}
        
        # 总收入和平均订单价值
        revenue_query = select(
            func.sum(ShopifyOrder.total_price),
            func.avg(ShopifyOrder.total_price)
        ).where(
            and_(
                ShopifyOrder.tenant_id == tenant.id,
                ShopifyOrder.total_price.isnot(None)
            )
        )
        revenue_result = await db.execute(revenue_query)
        revenue_row = revenue_result.first()
        total_revenue = float(revenue_row[0]) if revenue_row[0] else 0.0
        average_order_value = float(revenue_row[1]) if revenue_row[1] else 0.0
        
        logger.info(f"✅ 获取 Shopify 订单统计成功: 总订单数={total_orders}")
        
        return ShopifyOrderStatisticsResponse(
            total_orders=total_orders,
            orders_by_status=orders_by_status,
            orders_by_financial_status=orders_by_financial_status,
            orders_by_fulfillment_status=orders_by_fulfillment_status,
            total_revenue=total_revenue,
            average_order_value=average_order_value,
            orders_this_month=0,  # TODO: 实现本月订单统计
            orders_last_month=0   # TODO: 实现上月订单统计
        )
        
    except Exception as e:
        logger.error(f"❌ 获取 Shopify 订单统计失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to get Shopify order statistics: {str(e)}")
