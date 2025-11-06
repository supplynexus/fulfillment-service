"""
Shopify Orders CRUD API endpoints
专门处理 Shopify 订单的 CRUD 操作
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
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
from app.models.order import Order, OrderItem  # core order models
from app.models.product import ProductVariant
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
    page: int = Query(1, ge=1, description="页码"),
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
    
    # 如果提供了 page 参数，计算 skip
    if page > 1:
        skip = (page - 1) * limit
    
    try:
        logger.info(f"🔍 开始获取 Shopify 订单列表: tenant_id={tenant.id}, user_id={user.id}")
        logger.info(f"   过滤条件: financial_status={financial_status}, fulfillment_status={fulfillment_status}")
        logger.info(f"   分页: page={page}, skip={skip}, limit={limit}")
        
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
            # 处理日期时间格式，确保时区格式正确
            def format_datetime(dt):
                if dt is None:
                    return None
                # 如果已经是datetime对象，直接返回
                if isinstance(dt, datetime):
                    return dt
                # 如果是字符串，尝试解析并重新格式化
                if isinstance(dt, str):
                    try:
                        from dateutil import parser
                        parsed_dt = parser.parse(dt)
                        return parsed_dt
                    except:
                        return None
                return None
            
            order_responses.append(ShopifyOrderResponse(
                id=order.id,
                id_hashid=encode_id(order.id),  # 添加 hashid
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
                created_at=format_datetime(order.created_at),
                updated_at=format_datetime(order.updated_at),
                last_synced_at=format_datetime(order.last_synced_at)
            ))
        
        # 计算分页信息
        total_pages = (total + limit - 1) // limit  # 向上取整
        current_page = (skip // limit) + 1
        
        logger.info(f"✅ 获取 Shopify 订单列表成功: 总数={total}, 返回={len(order_responses)}, 总页数={total_pages}, 当前页={current_page}")
        
        return ShopifyOrderListResponse(
            orders=order_responses,
            total=total,
            skip=skip,
            limit=limit,
            total_pages=total_pages,
            current_page=current_page
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
        
        # 解码 hashid 或回退为数字 ID
        order_id = None
        try:
            order_id = decode_id(order_hashid)
            if order_id is None:
                raise ValueError("decode_id returned None")
            logger.info(f"✅ Hashid 解码成功: {order_hashid} -> {order_id}")
        except Exception:
            # 回退为数字 ID
            try:
                order_id = int(order_hashid)
                logger.info(f"ℹ️ 使用数字ID: {order_hashid} -> {order_id}")
            except Exception as e2:
                logger.error(f"❌ 订单ID无效: {order_hashid}, 错误: {str(e2)}")
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
            id_hashid=encode_id(order.id),  # 添加 hashid
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
            logger.info(f"🔄 Shopify 订单已存在，更新订单: {order_data.shopify_order_id}")
            # 使用 update 语句更新现有订单
            from sqlalchemy import update
            
            update_stmt = (
                update(ShopifyOrder)
                .where(ShopifyOrder.id == existing_order.id)
                .values(
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
                    raw_data=order_data.raw_data,
                    last_synced_at=datetime.utcnow()
                )
            )
            await db.execute(update_stmt)
            await db.commit()
            
            # 重新查询更新后的订单
            result = await db.execute(select(ShopifyOrder).where(ShopifyOrder.id == existing_order.id))
            order = result.scalar_one()
            
            logger.info(f"✅ Shopify 订单更新成功: {order_data.shopify_order_id}")
        else:
            # 创建新订单
            logger.info(f"➕ 创建新的 Shopify 订单: {order_data.shopify_order_id}")
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
            id_hashid=encode_id(order.id),  # 添加 hashid
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
            id_hashid=encode_id(order.id),  # 添加 hashid
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


@router.post("/{order_hashid}/sync-to-core", response_model=dict)
async def sync_shopify_order_to_core(
    order_hashid: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    将 Shopify 订单同步到核心订单系统
    """
    tenant, user = auth
    
    try:
        logger.info(f"🔍 开始同步 Shopify 订单到核心系统: order_hashid={order_hashid}, tenant_id={tenant.id}")
        
        # 解码 hashid
        try:
            order_id = decode_id(order_hashid)
            logger.info(f"✅ Hashid 解码成功: {order_hashid} -> {order_id}")
        except Exception as e:
            logger.error(f"❌ Hashid 解码失败: {order_hashid}, 错误: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid order ID")
        
        # 查询 Shopify 订单
        query = select(ShopifyOrder).where(
            and_(
                ShopifyOrder.id == order_id,
                ShopifyOrder.tenant_id == tenant.id
            )
        )
        result = await db.execute(query)
        shopify_order = result.scalar_one_or_none()
        
        if not shopify_order:
            logger.error(f"❌ Shopify 订单不存在: order_id={order_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="Shopify order not found")
        
        logger.info(f"✅ 找到 Shopify 订单: {shopify_order.name}")
        
        # 检查是否已经同步过
        existing_core_order_query = select(Order).where(
            and_(
                Order.tenant_id == tenant.id,
                Order.external_order_id == shopify_order.shopify_order_id
            )
        )
        existing_result = await db.execute(existing_core_order_query)
        existing_core_order = existing_result.scalar_one_or_none()
        
        if existing_core_order:
            logger.info(f"ℹ️ 核心订单已存在，更新现有订单: {existing_core_order.id}")
            core_order = existing_core_order
        else:
            # 创建核心订单
            logger.info(f"➕ 创建新的核心订单")
            
            # 生成人类可读的订单编号
            from app.services.order_number_service import OrderNumberService
            order_number = await OrderNumberService.generate_order_number(db, tenant.id, "ORD")
            logger.info(f"📝 生成订单编号: {order_number}")
            
            # 转换 Shopify 地址格式到核心订单格式
            def convert_shopify_address(shopify_addr):
                if not shopify_addr:
                    return {}
                
                # 合并 firstName 和 lastName
                first_name = shopify_addr.get("firstName", "")
                last_name = shopify_addr.get("lastName", "")
                full_name = f"{first_name} {last_name}".strip()
                
                return {
                    "name": full_name,
                    "address1": shopify_addr.get("address1", ""),
                    "address2": shopify_addr.get("address2", ""),
                    "city": shopify_addr.get("city", ""),
                    "province": shopify_addr.get("province", ""),
                    "country": shopify_addr.get("country", ""),
                    "zip": shopify_addr.get("zip", ""),
                    "phone": shopify_addr.get("phone", "")
                }
            
            core_order = Order(
                tenant_id=tenant.id,
                external_system_id=None,  # 暂时不关联外部系统
                external_order_id=shopify_order.shopify_order_id,
                external_order_number=shopify_order.name,
                external_order_name=shopify_order.name,
                order_number=order_number,  # 使用生成的订单编号
                status="pending",
                total_amount=float(shopify_order.total_price) if shopify_order.total_price else 0.0,
                subtotal_amount=float(shopify_order.subtotal_price) if shopify_order.subtotal_price else None,
                tax_amount=float(shopify_order.total_tax) if shopify_order.total_tax else None,
                currency=shopify_order.currency_code or "USD",
                customer_email=shopify_order.customer_data.get("email", "") if shopify_order.customer_data else "",
                customer_name=shopify_order.customer_data.get("name", "") if shopify_order.customer_data else "",
                customer_phone=None,
                shipping_address=convert_shopify_address(shopify_order.shipping_address),
                billing_address=convert_shopify_address(shopify_order.billing_address),
                shopify_raw_data=shopify_order.raw_data,
                external_data=shopify_order.raw_data,
                order_date=shopify_order.created_at
            )
            db.add(core_order)
            await db.flush()  # 获取 ID
            logger.info(f"✅ 核心订单创建成功: ID={core_order.id}")
        
        # 处理订单行项目
        if shopify_order.line_items:
            logger.info(f"🔍 开始处理订单行项目: {len(shopify_order.line_items)} 个")
            
            # 删除现有的订单行项目（如果存在）
            if existing_core_order:
                delete_items_query = select(OrderItem).where(OrderItem.order_id == core_order.id)
                existing_items_result = await db.execute(delete_items_query)
                existing_items = existing_items_result.scalars().all()
                for item in existing_items:
                    await db.delete(item)
                logger.info(f"🗑️ 删除现有订单行项目: {len(existing_items)} 个")
            
            for line_item in shopify_order.line_items:
                try:
                    # 尝试匹配核心 SKU
                    core_variant_id = None
                    core_product_id = None
                    
                    # 方法1: 通过 SKU 查找核心变体
                    if line_item.get("sku"):
                        variant_query = select(ProductVariant).where(
                            and_(
                                ProductVariant.tenant_id == tenant.id,
                                ProductVariant.sku == line_item["sku"]
                            )
                        )
                        variant_result = await db.execute(variant_query)
                        core_variant = variant_result.scalar_one_or_none()
                        
                        if core_variant:
                            core_variant_id = core_variant.id
                            core_product_id = core_variant.product_id
                            logger.info(f"✅ SKU 匹配成功: {line_item['sku']} -> core_variant_id={core_variant_id}")
                    
                    # 方法2: 如果 SKU 匹配失败，尝试通过 ProductMapping 查找
                    if not core_variant_id:
                        from app.models.product import ProductMapping
                        from app.models.external_system import ExternalSystem, ExternalSystemType
                        
                        # 获取该租户下的所有 Shopify 外部系统
                        shopify_systems_result = await db.execute(
                            select(ExternalSystem).where(
                                and_(
                                    ExternalSystem.tenant_id == tenant.id,
                                    ExternalSystem.system_type == ExternalSystemType.SHOPIFY,
                                    ExternalSystem.is_active == True
                                )
                            )
                        )
                        shopify_systems = shopify_systems_result.scalars().all()
                        
                        if shopify_systems:
                            # 获取 ProductVariant ID（不是 LineItem ID）
                            # line_item.variant.id 是 ProductVariant ID，用于匹配 ProductMapping
                            # line_item.id 是 LineItem ID，用于存储到 OrderItem.external_variant_id
                            line_item_id = line_item.get("id")  # LineItem ID (用于存储)
                            variant_data = line_item.get("variant", {})
                            product_variant_id = variant_data.get("id") if variant_data else None  # ProductVariant ID (用于匹配)
                            
                            # 如果 line_item 中没有 variant，尝试从 raw_data 中获取
                            if not product_variant_id and shopify_order.raw_data:
                                raw_line_items = shopify_order.raw_data.get("line_items", [])
                                # 通过 line_item.id 在 raw_data 中查找对应的 line_item
                                for raw_item in raw_line_items:
                                    raw_item_id = raw_item.get("id")
                                    if raw_item_id == line_item_id or str(raw_item_id) == str(line_item_id):
                                        raw_variant = raw_item.get("variant", {})
                                        if raw_variant:
                                            product_variant_id = raw_variant.get("id")
                                            logger.info(f"🔍 从 raw_data 获取 ProductVariant ID: {product_variant_id}")
                                        break
                            
                            external_product_id = line_item.get("product", {}).get("id") if line_item.get("product") else None
                            
                            # 如果还是没有，尝试从 raw_data 中获取 product_id
                            if not external_product_id and shopify_order.raw_data:
                                raw_line_items = shopify_order.raw_data.get("line_items", [])
                                for raw_item in raw_line_items:
                                    raw_item_id = raw_item.get("id")
                                    if raw_item_id == line_item_id or str(raw_item_id) == str(line_item_id):
                                        raw_product = raw_item.get("product", {})
                                        if raw_product:
                                            external_product_id = raw_product.get("id")
                                            logger.info(f"🔍 从 raw_data 获取 Product ID: {external_product_id}")
                                        break
                            
                            logger.info(f"🔍 尝试通过 ProductMapping 匹配: product_variant_id={product_variant_id}, external_product_id={external_product_id}")
                            
                            # 遍历所有 Shopify 系统，尝试查找映射
                            for shopify_system in shopify_systems:
                                # 方法1: 优先通过 ProductVariant ID 查找（最准确）
                                if product_variant_id:
                                    # 处理 GID 格式: gid://shopify/ProductVariant/xxx -> xxx
                                    variant_id_str = str(product_variant_id)
                                    if "ProductVariant/" in variant_id_str:
                                        variant_id_str = variant_id_str.split("ProductVariant/")[-1].split("?")[0]
                                    
                                    # 尝试精确匹配
                                    mapping_query = select(ProductMapping).where(
                                        and_(
                                            ProductMapping.tenant_id == tenant.id,
                                            ProductMapping.external_system_id == shopify_system.id,
                                            ProductMapping.external_variant_id == variant_id_str
                                        )
                                    )
                                    mapping_result = await db.execute(mapping_query)
                                    mapping = mapping_result.scalar_one_or_none()
                                    
                                    if mapping and mapping.core_variant_id:
                                        core_variant_id = mapping.core_variant_id
                                        core_product_id = mapping.core_product_id
                                        logger.info(f"✅ 通过 ProductMapping (ProductVariant ID={variant_id_str}) 匹配成功: core_variant_id={core_variant_id}, core_product_id={core_product_id}")
                                        break
                                    
                                    # 如果精确匹配失败，尝试模糊匹配（包含 variant_id_str）
                                    if not mapping:
                                        mapping_query = select(ProductMapping).where(
                                            and_(
                                                ProductMapping.tenant_id == tenant.id,
                                                ProductMapping.external_system_id == shopify_system.id,
                                                ProductMapping.external_variant_id.like(f"%{variant_id_str}%")
                                            )
                                        )
                                        mapping_result = await db.execute(mapping_query)
                                        mapping = mapping_result.scalar_one_or_none()
                                        
                                        if mapping and mapping.core_variant_id:
                                            core_variant_id = mapping.core_variant_id
                                            core_product_id = mapping.core_product_id
                                            logger.info(f"✅ 通过 ProductMapping (ProductVariant ID模糊匹配={variant_id_str}) 匹配成功: core_variant_id={core_variant_id}, core_product_id={core_product_id}")
                                            break
                                
                                # 方法2: 如果还没找到，通过 external_product_id 查找（产品级别映射）
                                if not core_variant_id and external_product_id:
                                    # 处理 GID 格式: gid://shopify/Product/xxx -> xxx
                                    product_id_str = str(external_product_id)
                                    if "Product/" in product_id_str:
                                        product_id_str = product_id_str.split("Product/")[-1].split("?")[0]
                                    
                                    # 查找该产品下的所有变体映射，选择第一个有 core_variant_id 的
                                    mapping_query = select(ProductMapping).where(
                                        and_(
                                            ProductMapping.tenant_id == tenant.id,
                                            ProductMapping.external_system_id == shopify_system.id,
                                            ProductMapping.external_product_id == product_id_str,
                                            ProductMapping.core_variant_id.isnot(None)  # 确保有变体映射
                                        )
                                    ).limit(1)  # 如果有多个变体，选择第一个
                                    mapping_result = await db.execute(mapping_query)
                                    mapping = mapping_result.scalar_one_or_none()
                                    
                                    if mapping and mapping.core_variant_id:
                                        core_variant_id = mapping.core_variant_id
                                        core_product_id = mapping.core_product_id
                                        logger.info(f"✅ 通过 ProductMapping (external_product_id={product_id_str}) 匹配成功: core_variant_id={core_variant_id}, core_product_id={core_product_id}")
                                        break
                                
                                # 如果找到了，跳出循环
                                if core_variant_id:
                                    break
                    
                    # 如果仍然没找到，记录警告
                    if not core_variant_id:
                        logger.warning(f"⚠️ 无法匹配核心产品: SKU={line_item.get('sku')}, external_variant_id={line_item.get('id')}, external_product_id={line_item.get('product', {}).get('id') if line_item.get('product') else None}")
                    
                    # 创建订单行项目
                    order_item = OrderItem(
                        tenant_id=tenant.id,
                        order_id=core_order.id,
                        core_product_id=core_product_id,
                        core_variant_id=core_variant_id,
                        external_product_id=line_item.get("product", {}).get("id") if line_item.get("product") else None,
                        external_variant_id=line_item.get("id"),
                        sku=line_item.get("sku"),
                        title=line_item.get("title"),
                        variant_title=line_item.get("variant_title"),
                        quantity=int(line_item.get("quantity", 1)),
                        unit_price=float(line_item.get("price", 0)) if line_item.get("price") else None,
                        total_price=float(line_item.get("price", 0)) * int(line_item.get("quantity", 1)) if line_item.get("price") else None,
                        discount=None,
                        tax=None,
                        fulfillment_status=shopify_order.fulfillment_status,
                        item_metadata={
                            "vendor": line_item.get("vendor"),
                            "currency": line_item.get("currency"),
                            "product_handle": line_item.get("product", {}).get("handle") if line_item.get("product") else None
                        }
                    )
                    db.add(order_item)
                    logger.info(f"✅ 订单行项目创建: SKU={line_item.get('sku')}, 数量={line_item.get('quantity')}")
                    
                except Exception as e:
                    logger.error(f"❌ 处理订单行项目失败: {str(e)}")
                    continue
        
        await db.commit()
        logger.info(f"✅ Shopify 订单同步到核心系统成功: {shopify_order.name}")
        
        return {
            "success": True,
            "message": f"订单 {shopify_order.name} 已成功同步到核心系统",
            "core_order_id": core_order.id,
            "items_count": len(shopify_order.line_items) if shopify_order.line_items else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ 同步 Shopify 订单到核心系统失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to sync Shopify order to core: {str(e)}")


@router.get("/{order_id}/json")
async def get_shopify_order_json(
    order_id: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    获取 Shopify 订单的完整 JSON 数据
    """
    tenant, user = auth
    
    try:
        logger.info(f"🔍 开始获取 Shopify 订单 JSON 数据: order_id={order_id}, tenant_id={tenant.id}")
        
        # 查询订单 - 支持纯数字ID和完整GraphQL ID
        # 如果传入的是纯数字，构建完整的GraphQL ID进行查询
        if order_id.isdigit():
            full_order_id = f"gid://shopify/Order/{order_id}"
            logger.info(f"🔍 使用完整GraphQL ID查询: {full_order_id}")
            query = select(ShopifyOrder).where(
                and_(
                    ShopifyOrder.shopify_order_id == full_order_id,
                    ShopifyOrder.tenant_id == tenant.id
                )
            )
        else:
            # 如果传入的是完整GraphQL ID，直接使用
            logger.info(f"🔍 使用完整GraphQL ID查询: {order_id}")
            query = select(ShopifyOrder).where(
                and_(
                    ShopifyOrder.shopify_order_id == order_id,
                    ShopifyOrder.tenant_id == tenant.id
                )
            )
        result = await db.execute(query)
        order = result.scalar_one_or_none()
        
        if not order:
            logger.error(f"❌ Shopify 订单不存在: order_id={order_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="Shopify order not found")
        
        # 返回原始 JSON 数据
        if order.raw_data:
            logger.info(f"✅ 成功获取 Shopify 订单 JSON 数据: {order.name}")
            return {
                "order_id": order.shopify_order_id,
                "name": order.name,
                "raw_data": order.raw_data,
                "last_synced_at": order.last_synced_at
            }
        else:
            logger.warning(f"⚠️ Shopify 订单没有原始数据: {order.name}")
            return {
                "order_id": order.shopify_order_id,
                "name": order.name,
                "raw_data": None,
                "last_synced_at": order.last_synced_at
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取 Shopify 订单 JSON 数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
