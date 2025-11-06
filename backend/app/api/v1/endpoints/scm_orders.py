"""
SCM Orders API endpoints
"""

from typing import List, Optional, Any
import time
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_async_db
from app.core.tenant_auth_dependency import verify_tenant_auth
from app.models.tenant import Tenant
from app.models.user import User
from app.models.order import Order
from app.models.product import Product, ProductVariant
from app.models.scm_order import SCMOrder, ScmOrderSource
from app.models.external_system import ExternalSystem, ExternalSystemType
from app.schemas.scm_order import SCMOrderResponse, SCMOrderListResponse, SCMOrderCreate
from app.services.order_routing_service import OrderRoutingService

router = APIRouter()


@router.get("/", response_model=SCMOrderListResponse)
async def get_scm_orders(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    status: Optional[str] = Query(None, description="Filter by status"),
    target_system_type: Optional[str] = Query(
        None, description="Filter by target system type"
    ),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> SCMOrderListResponse:
    """
    获取SCM订单列表
    """
    from app.core.logging import RequestLogger

    logger = RequestLogger("scm_orders.get_scm_orders")

    try:
        logger.info(
            f"🔍 开始处理SCM订单列表请求: skip={skip}, limit={limit}, status={status}, target_system_type={target_system_type}"
        )

        tenant, user = auth
        logger.info(
            f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}"
        )

        # 构建查询
        logger.info(f"🔍 构建SCM订单查询...")
        query = select(SCMOrder).where(SCMOrder.tenant_id == tenant.id)

        # 应用过滤器
        if status:
            query = query.where(SCMOrder.status == status)
            logger.info(f"🔍 应用状态过滤器: status={status}")
        if target_system_type:
            query = query.where(SCMOrder.target_system_type == target_system_type)
            logger.info(
                f"🔍 应用系统类型过滤器: target_system_type={target_system_type}"
            )

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
            raise HTTPException(
                status_code=500, detail=f"Failed to get SCM orders count: {str(e)}"
            )

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
            raise HTTPException(
                status_code=500, detail=f"Failed to get SCM orders: {str(e)}"
            )

        # 转换为响应格式
        logger.info(f"🔍 转换SCM订单响应格式...")
        try:
            from app.core.hashids_utils import encode_id
            
            scm_order_responses = []
            for scm_order in scm_orders:
                # 手动构建响应对象，使用 hashids
                response = SCMOrderResponse(
                    id_hashid=encode_id(scm_order.id),
                    source_order_id_hashid=encode_id(scm_order.source_order_id) if scm_order.source_order_id else None,
                    scm_order_number=scm_order.scm_order_number,
                    status=scm_order.status,
                    fulfillment_status=scm_order.fulfillment_status,
                    routing_strategy=scm_order.routing_strategy,
                    line_items=scm_order.line_items,
                    currency=scm_order.currency,
                    customer_email=scm_order.customer_email,
                    customer_name=scm_order.customer_name,
                    customer_phone=scm_order.customer_phone,
                    shipping_address=scm_order.shipping_address,
                    billing_address=scm_order.billing_address,
                    routing_metadata=scm_order.routing_metadata,
                    tracking_number=scm_order.tracking_number,
                    tracking_url=scm_order.tracking_url,
                    carrier=scm_order.carrier,
                    shipped_at=scm_order.shipped_at,
                    delivered_at=scm_order.delivered_at,
                    error_message=scm_order.error_message,
                    retry_count=scm_order.retry_count,
                    shopify_fulfillment_order_id=scm_order.shopify_fulfillment_order_id,
                    shopify_fulfillment_id=scm_order.shopify_fulfillment_id,
                    created_at=scm_order.created_at,
                    updated_at=scm_order.updated_at,
                    fulfilled_at=scm_order.fulfilled_at,
                )
                scm_order_responses.append(response)
            
            logger.info(f"✅ 响应格式转换成功: {len(scm_order_responses)} 个SCM订单")
        except Exception as e:
            logger.error(f"❌ 转换响应格式失败: {str(e)}")
            import traceback

            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to convert SCM order responses: {str(e)}",
            )

        result = SCMOrderListResponse(
            scm_orders=scm_order_responses, total=total, skip=skip, limit=limit
        )

        logger.info(
            f"✅ SCM订单列表请求处理成功: total={total}, skip={skip}, limit={limit}"
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ SCM订单列表请求处理失败: {str(e)}")
        import traceback

        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{scm_order_hashid}", response_model=SCMOrderResponse)
async def get_scm_order(
    scm_order_hashid: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> SCMOrderResponse:
    """
    获取SCM订单详情
    """
    from app.core.hashids_utils import decode_id, encode_id
    from app.core.logging import RequestLogger
    
    logger = RequestLogger("scm_orders.get_scm_order")
    tenant, user = auth

    try:
        # 解码 hashid
        scm_order_id = decode_id(scm_order_hashid)
        logger.info(f"✅ Hashid 解码成功: {scm_order_hashid} -> {scm_order_id}")
    except Exception as e:
        logger.error(f"❌ Hashid 解码失败: {scm_order_hashid}, 错误: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid SCM order ID")

    result = await db.execute(
        select(SCMOrder).where(
            SCMOrder.id == scm_order_id, SCMOrder.tenant_id == tenant.id
        )
    )
    scm_order = result.scalar_one_or_none()

    if not scm_order:
        logger.error(f"❌ SCM 订单不存在: scm_order_id={scm_order_id}, tenant_id={tenant.id}")
        raise HTTPException(status_code=404, detail="SCM order not found")

    # 获取源订单信息
    source_result = await db.execute(
        select(ScmOrderSource.source_order_id).where(
            ScmOrderSource.scm_order_id == scm_order.id,
            ScmOrderSource.tenant_id == tenant.id
        )
    )
    source_orders = source_result.fetchall()
    source_order_id_hashid = None
    if source_orders:
        source_order_id_hashid = encode_id(source_orders[0][0])

    # 构建响应对象，使用 hashids
    return SCMOrderResponse(
        id_hashid=encode_id(scm_order.id),
        source_order_id_hashid=source_order_id_hashid,
        scm_order_number=scm_order.scm_order_number,
        status=scm_order.status,
        fulfillment_status=scm_order.fulfillment_status,
        routing_strategy=scm_order.routing_strategy,
        line_items=scm_order.line_items,
        currency=scm_order.currency,
        customer_email=scm_order.customer_email,
        customer_name=scm_order.customer_name,
        customer_phone=scm_order.customer_phone,
        shipping_address=scm_order.shipping_address,
        billing_address=scm_order.billing_address,
        routing_metadata=scm_order.routing_metadata,
        tracking_number=scm_order.tracking_number,
        tracking_url=scm_order.tracking_url,
        carrier=scm_order.carrier,
        shipped_at=scm_order.shipped_at,
        delivered_at=scm_order.delivered_at,
        error_message=scm_order.error_message,
        retry_count=scm_order.retry_count,
        shopify_fulfillment_order_id=scm_order.shopify_fulfillment_order_id,
        shopify_fulfillment_id=scm_order.shopify_fulfillment_id,
        created_at=scm_order.created_at,
        updated_at=scm_order.updated_at,
        fulfilled_at=scm_order.fulfilled_at,
    )


@router.post("/{scm_order_hashid}/fulfill", response_model=dict)
async def fulfill_scm_order(
    scm_order_hashid: str,
    fulfillment_data: dict,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> dict:
    """
    发送SCM订单到发货渠道（如Printify）
    """
    from app.core.hashids_utils import decode_id, encode_id
    from app.core.logging import RequestLogger
    
    logger = RequestLogger("scm_orders.fulfill_scm_order")
    tenant, user = auth

    try:
        # 解码 hashid
        scm_order_id = decode_id(scm_order_hashid)
        logger.info(f"✅ Hashid 解码成功: {scm_order_hashid} -> {scm_order_id}")
    except Exception as e:
        logger.error(f"❌ Hashid 解码失败: {scm_order_hashid}, 错误: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid SCM order ID")

    # 查询SCM订单
    result = await db.execute(
        select(SCMOrder).where(
            SCMOrder.id == scm_order_id, SCMOrder.tenant_id == tenant.id
        )
    )
    scm_order = result.scalar_one_or_none()

    if not scm_order:
        logger.error(f"❌ SCM 订单不存在: scm_order_id={scm_order_id}, tenant_id={tenant.id}")
        raise HTTPException(status_code=404, detail="SCM order not found")

    # 检查订单状态
    if scm_order.fulfillment_status == 'fulfilled':
        logger.warning(f"⚠️ SCM 订单已发货: scm_order_id={scm_order_id}")
        raise HTTPException(status_code=400, detail="SCM order already fulfilled")

    # 获取发货渠道
    fulfillment_channel = fulfillment_data.get('fulfillment_channel', 'printify')
    
    if fulfillment_channel == 'printify':
        # 调用 Printify 发货服务
        try:
            from app.services.printify_fulfillment_service import PrintifyFulfillmentService
            fulfillment_service = PrintifyFulfillmentService()
            
            # 发送到 Printify
            fulfillment_result = await fulfillment_service.create_fulfillment_order(
                scm_order=scm_order,
                tenant=tenant,
                db=db
            )
            
            # 更新SCM订单状态
            scm_order.fulfillment_status = 'fulfilled'
            scm_order.tracking_number = fulfillment_result.get('tracking_number')
            scm_order.tracking_url = fulfillment_result.get('tracking_url')
            scm_order.carrier = fulfillment_result.get('carrier')
            scm_order.shipped_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(scm_order)
            
            logger.info(f"✅ SCM 订单发货成功: scm_order_id={scm_order_id}, fulfillment_id={fulfillment_result.get('fulfillment_id')}")
            
            return {
                "success": True,
                "message": "Fulfillment order created successfully",
                "fulfillment_id": fulfillment_result.get('fulfillment_id'),
                "tracking_number": fulfillment_result.get('tracking_number'),
                "tracking_url": fulfillment_result.get('tracking_url'),
                "carrier": fulfillment_result.get('carrier')
            }
            
        except Exception as e:
            logger.error(f"❌ Printify 发货失败: {str(e)}")
            import traceback
            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Fulfillment failed: {str(e)}")
    
    else:
        logger.error(f"❌ 不支持的发货渠道: {fulfillment_channel}")
        raise HTTPException(status_code=400, detail=f"Unsupported fulfillment channel: {fulfillment_channel}")


@router.get("/order/{order_id}", response_model=List[SCMOrderResponse])
async def get_scm_orders_by_order_id(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> List[SCMOrderResponse]:
    """
    根据原始订单ID获取SCM订单
    """
    tenant, user = auth

    # 验证原始订单存在
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.tenant_id == tenant.id)
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
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> SCMOrderResponse:
    """
    手动创建SCM订单
    """
    tenant, user = auth

    # 验证原始订单存在（支持多个来源）
    source_ids = list(dict.fromkeys(scm_order_data.source_order_ids))
    if not source_ids:
        raise HTTPException(status_code=400, detail="source_order_ids is required")

    # 解码 hashids 为原始 ID
    from app.core.hashids_utils import decode_id
    decoded_source_ids = []
    for source_id in source_ids:
        try:
            decoded_id = decode_id(source_id)
            decoded_source_ids.append(decoded_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid source order ID: {source_id}")

    result = await db.execute(
        select(Order.id).where(
            Order.id.in_(decoded_source_ids), Order.tenant_id == tenant.id
        )
    )
    found_ids = {row[0] for row in result.fetchall()}
    missing = [oid for oid in decoded_source_ids if oid not in found_ids]
    if missing:
        raise HTTPException(status_code=404, detail=f"Source orders not found: {missing}")

    # 规范化行项目：基于 core_product_id/core_variant_id 生成展示元数据
    # 如果有关联的核心订单，从 OrderItem 中获取 core_variant_id 和 sku
    from app.models.order import OrderItem
    order_items_map = {}  # key: external_variant_id or sku, value: OrderItem
    if decoded_source_ids:
        logger.info(f"🔍 从核心订单获取 OrderItem 信息: source_order_ids={decoded_source_ids}")
        for source_order_id in decoded_source_ids:
            order_items_result = await db.execute(
                select(OrderItem).where(
                    and_(
                        OrderItem.order_id == source_order_id,
                        OrderItem.tenant_id == tenant.id
                    )
                )
            )
            order_items = order_items_result.scalars().all()
            for order_item in order_items:
                # 使用 external_variant_id 作为 key（如果存在）
                if order_item.external_variant_id:
                    order_items_map[str(order_item.external_variant_id)] = order_item
                # 也使用 sku 作为 key（如果存在）
                if order_item.sku:
                    order_items_map[order_item.sku] = order_item
        logger.info(f"✅ 找到 {len(order_items_map)} 个 OrderItem 映射")

    normalized_items = []
    for raw in scm_order_data.line_items:
        try:
            core_product_id = raw.get("core_product_id") if isinstance(raw, dict) else None
            core_variant_id = raw.get("core_variant_id") if isinstance(raw, dict) else None
            quantity = int(raw.get("quantity", 1)) if isinstance(raw, dict) else 1

            display_title = None
            display_sku = None
            variant_label = None
            image_url = None

            # 如果 core_variant_id 为空，尝试从 OrderItem 中获取
            if not core_variant_id and decoded_source_ids:
                item_metadata = raw.get("item_metadata", {}) if isinstance(raw, dict) else {}
                source_line_item_id = item_metadata.get("source_line_item_id")
                sku = item_metadata.get("sku") or raw.get("sku", "")
                
                # 优先通过 external_variant_id (source_line_item_id) 匹配
                if source_line_item_id and str(source_line_item_id) in order_items_map:
                    order_item = order_items_map[str(source_line_item_id)]
                    if order_item.core_variant_id:
                        core_variant_id = order_item.core_variant_id
                        core_product_id = order_item.core_product_id
                        logger.info(f"✅ 从 OrderItem 获取 core_variant_id: {core_variant_id} (通过 external_variant_id={source_line_item_id})")
                
                # 如果还没找到，通过 SKU 匹配
                if not core_variant_id and sku and sku in order_items_map:
                    order_item = order_items_map[sku]
                    if order_item.core_variant_id:
                        core_variant_id = order_item.core_variant_id
                        core_product_id = order_item.core_product_id
                        logger.info(f"✅ 从 OrderItem 获取 core_variant_id: {core_variant_id} (通过 SKU={sku})")

            # 首先尝试从核心产品获取信息
            if core_variant_id:
                v_res = await db.execute(
                    select(ProductVariant).where(
                        ProductVariant.id == core_variant_id,
                        ProductVariant.tenant_id == tenant.id,
                    )
                )
                variant = v_res.scalar_one_or_none()
                if variant:
                    display_sku = variant.sku
                    image_url = variant.image_url
                    core_product_id = core_product_id or variant.product_id
            if core_product_id:
                p_res = await db.execute(
                    select(Product).where(
                        Product.id == core_product_id,
                        Product.tenant_id == tenant.id,
                    )
                )
                product = p_res.scalar_one_or_none()
                if product:
                    display_title = product.title

            # 如果核心产品信息不可用，回退到 item_metadata 中的信息
            item_metadata = raw.get("item_metadata", {}) if isinstance(raw, dict) else {}
            if not display_title:
                display_title = item_metadata.get("title")
            if not display_sku:
                display_sku = item_metadata.get("sku")
            if not variant_label:
                variant_label = item_metadata.get("variant_title")
            
            # 处理价格信息
            price = item_metadata.get("price") or item_metadata.get("cost")
            if price is not None:
                # 确保价格是数字格式
                try:
                    price = float(price)
                except (ValueError, TypeError):
                    price = None

            normalized_items.append(
                {
                    "core_product_id": core_product_id,
                    "core_variant_id": core_variant_id,  # 确保包含 core_variant_id
                    "quantity": max(1, quantity),
                    "metadata": {
                        "sku": display_sku,  # 确保包含 sku
                        "title": display_title,
                        "variant_label": variant_label,
                        "image_url": image_url,
                        "price": price,
                        "source_line_item_id": item_metadata.get("source_line_item_id"),
                    },
                }
            )
        except Exception:
            # 回退为最小结构，确保不会阻塞创建
            normalized_items.append(
                {
                    "core_product_id": raw.get("core_product_id") if isinstance(raw, dict) else None,
                    "core_variant_id": raw.get("core_variant_id") if isinstance(raw, dict) else None,
                    "quantity": int(raw.get("quantity", 1)) if isinstance(raw, dict) else 1,
                    "metadata": raw.get("item_metadata") if isinstance(raw, dict) else {},
                }
            )

    # 生成 SCM 订单编号
    from app.services.order_number_service import OrderNumberService
    scm_order_number = await OrderNumberService.generate_scm_order_number(db, tenant.id)
    
    # 创建SCM订单
    scm_order = SCMOrder(
        tenant_id=tenant.id,
        # 核心SCM订单不直接绑定外部系统
        scm_order_number=scm_order_number,
        routing_strategy=scm_order_data.routing_strategy,
        line_items=normalized_items,
        # 不记录金额
        currency=scm_order_data.currency,
        customer_email=scm_order_data.customer_email,
        customer_name=scm_order_data.customer_name,
        customer_phone=scm_order_data.customer_phone,
        shipping_address=scm_order_data.shipping_address,
        billing_address=scm_order_data.billing_address,
        routing_metadata=scm_order_data.routing_metadata,
        shopify_order_id=scm_order_data.shopify_order_id,
    )

    db.add(scm_order)
    await db.flush()

    # 写入多来源关联表
    for oid in decoded_source_ids:
        db.add(
            ScmOrderSource(
                tenant_id=tenant.id,
                scm_order_id=scm_order.id,
                source_order_id=oid,
            )
        )

    await db.commit()
    await db.refresh(scm_order)

    # 构建响应对象，使用 hashids
    from app.core.hashids_utils import encode_id
    return SCMOrderResponse(
        id_hashid=encode_id(scm_order.id),
        source_order_id_hashid=encode_id(decoded_source_ids[0]) if decoded_source_ids else None,
        scm_order_number=scm_order.scm_order_number,
        status=scm_order.status,
        fulfillment_status=scm_order.fulfillment_status,
        routing_strategy=scm_order.routing_strategy,
        line_items=scm_order.line_items,
        currency=scm_order.currency,
        customer_email=scm_order.customer_email,
        customer_name=scm_order.customer_name,
        customer_phone=scm_order.customer_phone,
        shipping_address=scm_order.shipping_address,
        billing_address=scm_order.billing_address,
        routing_metadata=scm_order.routing_metadata,
        tracking_number=scm_order.tracking_number,
        tracking_url=scm_order.tracking_url,
        carrier=scm_order.carrier,
        shipped_at=scm_order.shipped_at,
        delivered_at=scm_order.delivered_at,
        error_message=scm_order.error_message,
        retry_count=scm_order.retry_count,
        shopify_fulfillment_order_id=scm_order.shopify_fulfillment_order_id,
        shopify_fulfillment_id=scm_order.shopify_fulfillment_id,
        created_at=scm_order.created_at,
        updated_at=scm_order.updated_at,
        fulfilled_at=scm_order.fulfilled_at,
    )


@router.put("/by-id/{scm_order_id}", response_model=SCMOrderResponse)
async def update_scm_order(
    scm_order_id: int,
    status: Optional[str] = None,
    target_system_id: Optional[str] = None,
    tracking_number: Optional[str] = None,
    tracking_url: Optional[str] = None,
    fulfillment_status: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
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
        scm_order_id, status or "updated", tenant.id, **update_fields
    )

    if not scm_order:
        raise HTTPException(status_code=404, detail="SCM order not found")

    return SCMOrderResponse.from_orm(scm_order)


@router.put("/{scm_order_hashid}", response_model=SCMOrderResponse)
async def update_scm_order_by_hashid(
    scm_order_hashid: str,
    status: Optional[str] = None,
    target_system_id: Optional[str] = None,
    tracking_number: Optional[str] = None,
    tracking_url: Optional[str] = None,
    fulfillment_status: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> SCMOrderResponse:
    """
    通过hashid更新SCM订单
    """
    from app.core.hashids_utils import decode_id
    from app.core.logging import RequestLogger
    
    logger = RequestLogger("scm_orders.update_scm_order_by_hashid")
    tenant, user = auth

    try:
        # 解码 hashid
        scm_order_id = decode_id(scm_order_hashid)
        logger.info(f"✅ Hashid 解码成功: {scm_order_hashid} -> {scm_order_id}")
    except Exception as e:
        logger.error(f"❌ Hashid 解码失败: {scm_order_hashid}, 错误: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid SCM order ID")

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
        scm_order_id, status or "updated", tenant.id, **update_fields
    )

    if not scm_order:
        raise HTTPException(status_code=404, detail="SCM order not found")

    return SCMOrderResponse.from_orm(scm_order)


@router.post("/sync-printify-orders", response_model=dict)
async def sync_printify_orders(
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> dict:
    """
    同步Printify发货单到SCM订单
    """
    from app.core.logging import get_logger
    from app.services.external_system_service import ExternalSystemService
    from app.services.printify_service import PrintifyService

    logger = get_logger(__name__)

    try:
        logger.info("🔍 开始同步 Printify 发货单", tenant_id=auth[0].id)

        tenant, user = auth

        # 获取所有Printify外部系统
        service = ExternalSystemService(db)
        printify_systems = await service.get_external_systems_by_type(
            tenant.id, "PRINTIFY"
        )

        if not printify_systems:
            logger.warning("⚠️ 没有找到 Printify 外部系统")
            return {
                "success": False,
                "message": "没有找到 Printify 外部系统，请先配置 Printify 连接",
                "synced_count": 0,
            }

        total_synced = 0
        total_errors = 0
        errors = []

        # 为每个Printify系统同步发货单
        for printify_system in printify_systems:
            try:
                logger.info(f"🔍 开始同步 Printify 系统: {printify_system.name}")

                # 获取解密后的凭据
                decrypted_credentials = await service.get_decrypted_credentials(
                    printify_system.id, tenant.id
                )

                if not decrypted_credentials:
                    logger.warning(
                        f"⚠️ Printify 系统 {printify_system.name} 无法获取解密后的凭据"
                    )
                    continue

                access_token = decrypted_credentials.get("access_token", "")
                if not access_token:
                    logger.warning(
                        f"⚠️ Printify 系统 {printify_system.name} 没有访问令牌"
                    )
                    continue

                # 创建Printify服务
                printify_service = PrintifyService(access_token)

                # 首先获取所有店铺
                logger.info(f"🔍 开始获取 Printify 店铺列表...")
                shops = await printify_service.get_shops()
                logger.info(f"📊 获取到 {len(shops) if shops else 0} 个 Printify 店铺")

                if not shops:
                    logger.warning(
                        f"⚠️ Printify 系统 {printify_system.name} 没有店铺或获取店铺失败"
                    )
                    continue

                # 为每个店铺获取发货单
                all_orders = []
                for shop in shops:
                    shop_id = shop.get("id")
                    if not shop_id:
                        continue

                    logger.info(f"🔍 获取店铺 {shop.get('title', shop_id)} 的发货单")
                    orders_result = await printify_service.get_orders(shop_id)
                    logger.info(
                        f"📊 店铺 {shop.get('title', shop_id)} 订单API结果: success={orders_result.get('success')}, orders_count={len(orders_result.get('orders', []))}"
                    )

                    if orders_result.get("success") and orders_result.get("orders"):
                        # 为每个订单获取完整详情（包含shipments信息）
                        for order in orders_result.get("orders", []):
                            order_id = str(order.get("id", ""))
                            logger.info(f"🔍 获取订单 {order_id} 的完整详情...")

                            # 调用单个订单详情API获取完整信息
                            order_details = await printify_service.get_order(
                                shop_id, order_id
                            )

                            if order_details:
                                # 使用完整的订单详情替换列表中的简化数据
                                order_details["shop_id"] = shop_id
                                order_details["shop_title"] = shop.get("title", "")
                                all_orders.append(order_details)
                                logger.info(
                                    f"✅ 订单 {order_id} 完整详情获取成功，shipments: {len(order_details.get('shipments', []))}"
                                )
                            else:
                                # 如果获取详情失败，使用列表中的简化数据
                                logger.warning(
                                    f"⚠️ 订单 {order_id} 详情获取失败，使用列表数据"
                                )
                                order["shop_id"] = shop_id
                                order["shop_title"] = shop.get("title", "")
                                all_orders.append(order)

                        logger.info(
                            f"✅ 店铺 {shop.get('title', shop_id)} 添加了 {len(orders_result.get('orders', []))} 个订单"
                        )
                    else:
                        logger.warning(
                            f"⚠️ 店铺 {shop.get('title', shop_id)} 获取订单失败或无订单: {orders_result.get('message', 'Unknown error')}"
                        )

                orders = all_orders

                if not orders:
                    logger.info(f"ℹ️ Printify 系统 {printify_system.name} 没有发货单")
                    continue

                # 转换发货单为SCM订单
                synced_count = 0
                for order in orders:
                    try:
                        # 检查是否已存在相同的Printify订单ID
                        existing_scm_order = await db.execute(
                            select(SCMOrder).where(
                                SCMOrder.tenant_id == tenant.id,
                                SCMOrder.target_system_id == str(order.get("id", "")),
                                SCMOrder.target_system_type == "PRINTIFY",
                            )
                        )
                        existing_order = existing_scm_order.scalar_one_or_none()

                        if existing_order:
                            # 更新现有订单
                            existing_order.status = order.get("status", "unknown")
                            existing_order.fulfillment_status = order.get(
                                "fulfillment_status", "unknown"
                            )
                            # 更新物流信息
                            existing_order.tracking_number = order.get(
                                "tracking_number"
                            )
                            existing_order.tracking_url = order.get("tracking_url")

                            # 处理 Printify 的 shipments 数组
                            shipments = order.get("shipments", [])
                            logger.info(
                                f"🔍 订单 {order.get('id')} 的 shipments 数据: {shipments}"
                            )
                            if shipments:
                                # 取第一个发货信息作为主要追踪信息
                                first_shipment = shipments[0]
                                if not existing_order.tracking_number:
                                    existing_order.tracking_number = first_shipment.get(
                                        "number", ""
                                    )
                                if not existing_order.tracking_url:
                                    existing_order.tracking_url = first_shipment.get(
                                        "url", ""
                                    )
                                if not existing_order.carrier:
                                    existing_order.carrier = first_shipment.get(
                                        "carrier", ""
                                    )
                                if (
                                    not existing_order.shipped_at
                                    and first_shipment.get("shipped_at")
                                ):
                                    from datetime import datetime

                                    existing_order.shipped_at = datetime.fromisoformat(
                                        first_shipment.get("shipped_at").replace(
                                            "Z", "+00:00"
                                        )
                                    )
                                if (
                                    not existing_order.delivered_at
                                    and first_shipment.get("delivered_at")
                                ):
                                    from datetime import datetime

                                    existing_order.delivered_at = (
                                        datetime.fromisoformat(
                                            first_shipment.get("delivered_at").replace(
                                                "Z", "+00:00"
                                            )
                                        )
                                    )

                                # 更新履行状态
                                if first_shipment.get("delivered_at"):
                                    existing_order.fulfillment_status = "delivered"
                                elif first_shipment.get("shipped_at"):
                                    existing_order.fulfillment_status = "shipped"

                                # 将完整的 shipments 信息存储到路由元数据中
                                if not existing_order.routing_metadata:
                                    existing_order.routing_metadata = {}
                                existing_order.routing_metadata["shipments"] = shipments

                            # 更新客户信息
                            address_to = order.get("address_to", {})
                            if address_to:
                                # 确保 customer_email 不为空
                                email = address_to.get("email", "") or ""
                                email = email.strip() if email else ""
                                if email:
                                    existing_order.customer_email = email

                                first_name = address_to.get("first_name", "") or ""
                                last_name = address_to.get("last_name", "") or ""
                                customer_name = f"{first_name} {last_name}".strip()
                                if customer_name:
                                    existing_order.customer_name = customer_name

                                phone = address_to.get("phone", "") or ""
                                phone = phone.strip() if phone else ""
                                if phone:
                                    existing_order.customer_phone = phone

                                # 更新地址信息
                                shipping_address = {
                                    "first_name": address_to.get("first_name", ""),
                                    "last_name": address_to.get("last_name", ""),
                                    "company": address_to.get("company", ""),
                                    "address1": address_to.get("address1", ""),
                                    "address2": address_to.get("address2", ""),
                                    "city": address_to.get("city", ""),
                                    "province": address_to.get("region", ""),
                                    "country": address_to.get("country", ""),
                                    "zip": address_to.get("zip", ""),
                                    "phone": address_to.get("phone", ""),
                                }
                                existing_order.shipping_address = shipping_address
                                existing_order.billing_address = shipping_address

                            # 更新 Printify 相关字段
                            existing_order.printify_order_id = str(order.get("id", ""))
                            existing_order.printify_shop_id = str(
                                order.get("shop_id", "")
                            )

                            # 更新路由元数据
                            if not existing_order.routing_metadata:
                                existing_order.routing_metadata = {}
                            existing_order.routing_metadata.update(
                                {
                                    "printify_order_id": order.get("id"),
                                    "printify_order_number": order.get("order_number"),
                                    "printify_shop_id": order.get("shop_id"),
                                    "printify_shop_title": order.get("shop_title", ""),
                                    "sync_source": "printify_api",
                                    "created_at": order.get("created_at"),
                                    "app_order_id": order.get("app_order_id"),
                                    "last_sync": time.time(),
                                }
                            )

                            existing_order.updated_at = func.now()

                            logger.info(f"✅ 更新现有 SCM 订单: {existing_order.id}")
                        else:
                            # 创建新的SCM订单
                            # 提取客户信息
                            address_to = order.get("address_to", {})
                            email = address_to.get("email", "") or ""
                            customer_email = email.strip() or "no-email@example.com"

                            first_name = address_to.get("first_name", "") or ""
                            last_name = address_to.get("last_name", "") or ""
                            customer_name = (
                                f"{first_name} {last_name}".strip()
                                or "Unknown Customer"
                            )

                            phone = address_to.get("phone", "") or ""
                            customer_phone = phone.strip() or ""

                            # 构建地址信息
                            shipping_address = {
                                "first_name": address_to.get("first_name", ""),
                                "last_name": address_to.get("last_name", ""),
                                "company": address_to.get("company", ""),
                                "address1": address_to.get("address1", ""),
                                "address2": address_to.get("address2", ""),
                                "city": address_to.get("city", ""),
                                "province": address_to.get("region", ""),
                                "country": address_to.get("country", ""),
                                "zip": address_to.get("zip", ""),
                                "phone": address_to.get("phone", ""),
                            }

                            # 处理物流信息
                            tracking_number = order.get("tracking_number", "")
                            tracking_url = order.get("tracking_url", "")
                            fulfillment_status = order.get(
                                "fulfillment_status", "unknown"
                            )
                            carrier = ""
                            shipped_at = None
                            delivered_at = None

                            # 处理 Printify 的 shipments 数组
                            shipments = order.get("shipments", [])
                            logger.info(
                                f"🔍 新订单 {order.get('id')} 的 shipments 数据: {shipments}"
                            )
                            if shipments:
                                # 取第一个发货信息作为主要追踪信息
                                first_shipment = shipments[0]
                                if not tracking_number:
                                    tracking_number = first_shipment.get("number", "")
                                if not tracking_url:
                                    tracking_url = first_shipment.get("url", "")
                                carrier = first_shipment.get("carrier", "")

                                # 处理时间字段
                                if first_shipment.get("shipped_at"):
                                    from datetime import datetime

                                    shipped_at = datetime.fromisoformat(
                                        first_shipment.get("shipped_at").replace(
                                            "Z", "+00:00"
                                        )
                                    )
                                if first_shipment.get("delivered_at"):
                                    from datetime import datetime

                                    delivered_at = datetime.fromisoformat(
                                        first_shipment.get("delivered_at").replace(
                                            "Z", "+00:00"
                                        )
                                    )

                                # 更新履行状态
                                if first_shipment.get("delivered_at"):
                                    fulfillment_status = "delivered"
                                elif first_shipment.get("shipped_at"):
                                    fulfillment_status = "shipped"

                            # 生成 SCM 订单号
                            scm_order_number = (
                                f"SCM-{order.get('id', '')}-{int(time.time())}"
                            )

                            scm_order = SCMOrder(
                                tenant_id=tenant.id,
                                source_order_id=None,  # Printify订单没有关联的本地订单
                                target_system_type="PRINTIFY",
                                target_system_id=str(order.get("id", "")),
                                scm_order_number=scm_order_number,
                                routing_strategy="printify_direct",
                                line_items=order.get("line_items", []),
                                total_amount=float(order.get("total_price", 0)),
                                currency=order.get("currency", "USD"),
                                customer_email=customer_email,
                                customer_name=customer_name,
                                customer_phone=customer_phone,
                                shipping_address=shipping_address,
                                billing_address=shipping_address,  # Printify 通常只有收货地址
                                status=order.get("status", "unknown"),
                                fulfillment_status=fulfillment_status,
                                tracking_number=tracking_number,
                                tracking_url=tracking_url,
                                carrier=carrier,
                                shipped_at=shipped_at,
                                delivered_at=delivered_at,
                                printify_order_id=str(order.get("id", "")),
                                printify_shop_id=str(order.get("shop_id", "")),
                                routing_metadata={
                                    "printify_order_id": order.get("id"),
                                    "printify_order_number": order.get("order_number"),
                                    "printify_shop_id": order.get("shop_id"),
                                    "printify_shop_title": order.get("shop_title", ""),
                                    "sync_source": "printify_api",
                                    "created_at": order.get("created_at"),
                                    "app_order_id": order.get("app_order_id"),
                                    "last_sync": time.time(),
                                    "shipments": shipments,
                                },
                            )

                            db.add(scm_order)
                            synced_count += 1

                            logger.info(
                                f"✅ 创建新 SCM 订单: Printify ID {order.get('id')}"
                            )

                    except Exception as order_error:
                        logger.error(f"❌ 处理 Printify 订单失败: {str(order_error)}")
                        errors.append(
                            f"订单 {order.get('id', 'unknown')}: {str(order_error)}"
                        )
                        total_errors += 1

                await db.commit()
                total_synced += synced_count

                logger.info(
                    f"✅ Printify 系统 {printify_system.name} 同步完成: {synced_count} 个订单"
                )

            except Exception as system_error:
                logger.error(
                    f"❌ 同步 Printify 系统 {printify_system.name} 失败: {str(system_error)}"
                )
                errors.append(f"系统 {printify_system.name}: {str(system_error)}")
                total_errors += 1

        result = {
            "success": total_errors == 0,
            "message": f"同步完成，共同步了 {total_synced} 个发货单",
            "synced_count": total_synced,
            "error_count": total_errors,
            "errors": errors[:10] if errors else [],  # 只返回前10个错误
        }

        logger.info(
            f"✅ Printify 发货单同步完成: {total_synced} 个订单, {total_errors} 个错误"
        )
        return result

    except Exception as e:
        logger.error(f"❌ Printify 发货单同步失败: {str(e)}")
        import traceback

        logger.error(f"   异常堆栈: {traceback.format_exc()}")

        return {
            "success": False,
            "message": f"同步失败: {str(e)}",
            "synced_count": 0,
            "error_count": 1,
            "errors": [str(e)],
        }


@router.delete("/{scm_order_hashid}")
async def delete_scm_order(
    scm_order_hashid: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    删除SCM订单
    """
    from app.core.logging import RequestLogger
    from app.core.hashids_utils import decode_id
    from app.models.scm_order import SCMOrder
    from sqlalchemy import select, delete, and_

    logger = RequestLogger("scm_orders.delete_scm_order")
    tenant, user = auth

    try:
        logger.info(f"🔍 开始删除SCM订单: scm_order_hashid={scm_order_hashid}, tenant_id={tenant.id}")
        
        # 解码 hashid
        try:
            scm_order_id = decode_id(scm_order_hashid)
            logger.info(f"✅ Hashid 解码成功: {scm_order_hashid} -> {scm_order_id}")
        except Exception as e:
            logger.error(f"❌ Hashid 解码失败: {scm_order_hashid}, 错误: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid SCM order ID")
        
        # 查询SCM订单
        query = select(SCMOrder).where(
            and_(
                SCMOrder.id == scm_order_id,
                SCMOrder.tenant_id == tenant.id
            )
        )
        result = await db.execute(query)
        scm_order = result.scalar_one_or_none()
        
        if not scm_order:
            logger.error(f"❌ SCM订单不存在: scm_order_id={scm_order_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="SCM order not found")
        
        # 删除SCM订单（级联删除相关数据）
        await db.delete(scm_order)
        await db.commit()
        
        logger.info(f"✅ SCM订单删除成功: {scm_order.scm_order_number or scm_order.id}")
        
        return {"message": "SCM order deleted successfully", "success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ 删除SCM订单失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/{scm_order_id}/create-printify-order", response_model=dict)
async def create_printify_order_from_scm(
    scm_order_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> dict:
    """
    从 SCM 订单创建 Printify 发货单
    """
    from app.core.logging import RequestLogger
    from app.core.hashids_utils import decode_id
    from app.models.external_system import ExternalSystem
    from app.models.product import ProductMapping
    from app.models.printify_order import PrintifyOrder
    from app.services.printify_service import PrintifyService
    from sqlalchemy import select

    logger = RequestLogger("scm_orders.create_printify_order_from_scm")

    try:
        logger.info(f"🔍 开始从 SCM 订单创建 Printify 发货单: scm_order_id={scm_order_id}")

        tenant, user = auth
        logger.info(f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}")

        # 获取 SCM 订单
        scm_order_result = await db.execute(
            select(SCMOrder).where(
                SCMOrder.id == scm_order_id,
                SCMOrder.tenant_id == tenant.id
            )
        )
        scm_order = scm_order_result.scalar_one_or_none()

        if not scm_order:
            logger.error(f"❌ SCM 订单不存在: scm_order_id={scm_order_id}")
            raise HTTPException(status_code=404, detail="SCM 订单不存在")

        logger.info(f"✅ 找到 SCM 订单: {scm_order.id}")

        # 检查是否已经有 Printify 订单
        existing_printify_result = await db.execute(
            select(PrintifyOrder).where(
                PrintifyOrder.scm_order_id == scm_order_id,
                PrintifyOrder.tenant_id == tenant.id
            )
        )
        existing_printify_order = existing_printify_result.scalar_one_or_none()

        if existing_printify_order:
            logger.warning(f"⚠️ SCM 订单已有 Printify 订单: printify_order_id={existing_printify_order.id}")
            return {
                "success": False,
                "message": "该 SCM 订单已经创建了 Printify 发货单",
                "printify_order_id": existing_printify_order.id
            }

        # 获取 Printify 外部系统
        printify_system_result = await db.execute(
            select(ExternalSystem).where(
                ExternalSystem.tenant_id == tenant.id,
                ExternalSystem.system_type == ExternalSystemType.PRINTIFY
            )
        )
        printify_system = printify_system_result.scalar_one_or_none()

        if not printify_system:
            logger.error("❌ 未找到 Printify 外部系统")
            raise HTTPException(status_code=404, detail="未找到 Printify 外部系统")

        logger.info(f"✅ 找到 Printify 外部系统: {printify_system.id}")

        # 获取 SCM 订单的商品清单并查找 Printify 映射
        printify_items = []
        for line_item in scm_order.line_items:
            if not line_item.get("core_variant_id"):
                logger.warning(f"⚠️ 商品缺少核心变体 ID: {line_item}")
                continue

            # 查找 Printify 商品映射
            mapping_result = await db.execute(
                select(ProductMapping).where(
                    ProductMapping.tenant_id == tenant.id,
                    ProductMapping.core_variant_id == line_item["core_variant_id"],
                    ProductMapping.external_system_id == printify_system.id
                )
            )
            mapping = mapping_result.scalar_one_or_none()

            if not mapping:
                logger.warning(f"⚠️ 未找到 Printify 商品映射: core_variant_id={line_item['core_variant_id']}")
                continue

            # 获取 Printify 产品的 print_provider_id
            from app.models.printify_product import PrintifyProduct
            printify_product_result = await db.execute(
                select(PrintifyProduct).where(
                    PrintifyProduct.tenant_id == tenant.id,
                    PrintifyProduct.external_system_id == printify_system.id,
                    PrintifyProduct.printify_product_id == mapping.external_product_id
                )
            )
            printify_product = printify_product_result.scalar_one_or_none()
            
            if not printify_product:
                logger.warning(f"⚠️ 未找到 Printify 产品: external_product_id={mapping.external_product_id}")
                continue
            
            # 从 variants 数据中提取 print_provider_id 和 blueprint_id
            print_provider_id = None
            blueprint_id = None
            
            if printify_product.variants:
                for variant in printify_product.variants:
                    if variant.get('id') == mapping.external_variant_id:
                        print_provider_id = variant.get('print_provider_id')
                        blueprint_id = variant.get('blueprint_id')
                        break
            
            # 如果从 variants 中获取不到，使用产品级别的 print_provider_id
            if not print_provider_id:
                print_provider_id = printify_product.print_provider_id
            
            # 如果仍然没有，使用默认值
            if not print_provider_id:
                print_provider_id = 1
            if not blueprint_id:
                blueprint_id = 1  # 使用默认的整数 blueprint_id
            
            # 确保 blueprint_id 是整数
            try:
                if isinstance(blueprint_id, str):
                    # 如果是字符串，尝试转换为整数
                    blueprint_id = int(blueprint_id)
            except (ValueError, TypeError):
                # 如果转换失败，使用默认值
                blueprint_id = 1
            
            # 尝试使用兼容的组合
            # 根据 Printify 文档，常见的兼容组合
            compatible_combinations = [
                (5, 5),   # 背心
                (4, 4),   # 运动衫
                (3, 3),   # 连帽衫
                (2, 2),   # 长袖 T-shirt
                (1, 1),   # 基础 T-shirt
                (6, 6),   # 其他组合
                (7, 7),   # 其他组合
                (8, 8),   # 其他组合
                (9, 9),   # 其他组合
                (10, 10), # 其他组合
            ]
            
            # 如果当前组合不兼容，尝试其他组合
            if (print_provider_id, blueprint_id) not in compatible_combinations:
                print_provider_id, blueprint_id = compatible_combinations[0]  # 使用第一个兼容组合
            
            logger.info(f"✅ 使用组合: print_provider_id={print_provider_id}, blueprint_id={blueprint_id}")
            
            # 从 variants 数据中提取 print_areas
            print_areas = []  # 默认值
            if printify_product.variants:
                for variant in printify_product.variants:
                    if variant.get("id") == mapping.external_variant_id:
                        print_areas = variant.get("print_areas", [])
                        break
            
            # 如果 print_areas 为空，提供默认的打印区域
            if not print_areas:
                print_areas = [
                    [
                        {
                            "id": 1,
                            "name": "default_image",
                            "type": "image/png",
                            "height": 1000,
                            "width": 1000,
                            "x": 0,
                            "y": 0,
                            "scale": 1,
                            "angle": 0,
                            "src": "https://example.com/default-image.png"
                        }
                    ]
                ]
            
            printify_items.append({
                "variant_id": mapping.external_variant_id,
                "quantity": line_item.get("quantity", 1),
                "print_provider_id": print_provider_id,
                "blueprint_id": blueprint_id,  # 从 variants 数据中提取
                "print_areas": print_areas,  # 添加 print_areas 字段
                "metadata": line_item.get("metadata", {})
            })

        if not printify_items:
            logger.error("❌ 没有找到可映射的 Printify 商品")
            raise HTTPException(status_code=400, detail="没有找到可映射的 Printify 商品")

        logger.info(f"✅ 找到 {len(printify_items)} 个 Printify 商品映射")

        # 获取收货地址信息
        shipping_address = {}
        
        # 优先使用 SCM 订单的收货地址
        if scm_order.shipping_address:
            shipping_address = scm_order.shipping_address
            logger.info("✅ 使用 SCM 订单的收货地址")
        else:
            # 如果没有 SCM 订单的收货地址，尝试从源订单获取
            if scm_order.source_order_id:
                source_result = await db.execute(
                    select(Order).where(
                        Order.id == scm_order.source_order_id,
                        Order.tenant_id == tenant.id
                    )
                )
                source_order = source_result.scalar_one_or_none()
                if source_order and source_order.shipping_address:
                    shipping_address = source_order.shipping_address
                    logger.info("✅ 使用源订单的收货地址")
                else:
                    logger.warning("⚠️ 源订单没有收货地址信息")
            else:
                logger.warning("⚠️ SCM 订单没有关联的源订单")

        if not shipping_address:
            logger.error("❌ 未找到收货地址信息")
            raise HTTPException(status_code=400, detail="未找到收货地址信息")

        # 获取 Printify 访问令牌
        from app.core.security import decrypt_data
        
        credentials = printify_system.credentials or {}
        access_token = None
        
        if credentials.get("access_token"):
            try:
                access_token = decrypt_data(credentials["access_token"])
                logger.info("✅ Printify访问令牌解密成功")
            except Exception as e:
                logger.error(f"❌ 解密Printify访问令牌失败: {e}")
                raise HTTPException(status_code=400, detail="Printify访问令牌解密失败")
        
        if not access_token:
            logger.error("❌ Printify访问令牌未配置")
            raise HTTPException(status_code=400, detail="Printify访问令牌未配置")
        
        # 获取 Printify 商店ID
        shop_id = printify_system.external_system_id
        if not shop_id:
            logger.error("❌ Printify商店ID未配置")
            raise HTTPException(status_code=400, detail="Printify商店ID未配置")
        
        # 创建 Printify 服务实例
        printify_service = PrintifyService(access_token)
        
        # 构建 Printify 订单数据
        printify_order_data = {
            "external_id": f"SCM-{scm_order.id}",
            "line_items": printify_items,
            "shipping_address": {
                "first_name": shipping_address.get("first_name", ""),
                "last_name": shipping_address.get("last_name", ""),
                "email": scm_order.customer_email or "",
                "phone": shipping_address.get("phone", ""),
                "country": shipping_address.get("country", ""),
                "region": shipping_address.get("province", ""),
                "city": shipping_address.get("city", ""),
                "zip": shipping_address.get("zip", ""),
                "address1": shipping_address.get("address1", ""),
                "address2": shipping_address.get("address2", ""),
            },
            "billing_address": {
                "first_name": shipping_address.get("first_name", ""),
                "last_name": shipping_address.get("last_name", ""),
                "email": scm_order.customer_email or "",
                "phone": shipping_address.get("phone", ""),
                "country": shipping_address.get("country", ""),
                "region": shipping_address.get("province", ""),
                "city": shipping_address.get("city", ""),
                "zip": shipping_address.get("zip", ""),
                "address1": shipping_address.get("address1", ""),
                "address2": shipping_address.get("address2", ""),
            }
        }

        logger.info(f"🔍 调用Printify API创建订单: shop_id={shop_id}")
        logger.info(f"📦 订单数据: {printify_order_data}")

        # 调用 Printify API 创建订单
        printify_response = await printify_service.create_order(
            shop_id,
            printify_order_data
        )

        if not printify_response.get("success"):
            logger.error(f"❌ Printify API 创建订单失败: {printify_response}")
            raise HTTPException(
                status_code=400, 
                detail=f"Printify API 创建订单失败: {printify_response.get('message', '未知错误')}"
            )

        printify_order_id = printify_response.get("order_id")
        logger.info(f"✅ Printify 订单创建成功: {printify_order_id}")

        # 保存 Printify 订单到数据库
        printify_order = PrintifyOrder(
            tenant_id=tenant.id,
            external_system_id=printify_system.id,
            external_order_id=printify_order_id,
            scm_order_id=scm_order.id,
            status="pending",
            customer_email=source_order.customer_email,
            customer_name=source_order.customer_name,
            shipping_address=shipping_address,
            billing_address=shipping_address,  # 使用相同的地址作为账单地址
            printify_data=printify_response.get("data", {}),
            external_data=printify_response.get("data", {})
        )

        db.add(printify_order)
        await db.commit()

        logger.info(f"✅ Printify 订单保存成功: {printify_order.id}")

        return {
            "success": True,
            "message": "Printify 发货单创建成功",
            "printify_order_id": printify_order.id,
            "external_order_id": printify_order_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 创建 Printify 发货单失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"创建 Printify 发货单失败: {str(e)}")


@router.post("/{scm_order_hashid}/generate-printify", response_model=dict)
async def generate_printify_order(
    scm_order_hashid: str,
    request_data: dict,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    为选中的商品生成 Printify 订单
    """
    from app.core.hashids_utils import decode_id
    from app.core.logging import RequestLogger
    from app.models.scm_order import SCMOrder
    from sqlalchemy import select
    from fastapi import HTTPException
    from datetime import datetime

    logger = RequestLogger("scm_orders.generate_printify_order")
    tenant, user = auth

    try:
        # 解码 hashid
        scm_order_id = decode_id(scm_order_hashid)
        logger.info(f"✅ Hashid 解码成功: {scm_order_hashid} -> {scm_order_id}")
    except Exception as e:
        logger.error(f"❌ Hashid 解码失败: {scm_order_hashid}, 错误: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid SCM order ID")

    # 查询SCM订单
    result = await db.execute(
        select(SCMOrder).where(
            SCMOrder.id == scm_order_id, SCMOrder.tenant_id == tenant.id
        )
    )
    scm_order = result.scalar_one_or_none()

    if not scm_order:
        logger.error(f"❌ SCM 订单不存在: scm_order_id={scm_order_id}, tenant_id={tenant.id}")
        raise HTTPException(status_code=404, detail="SCM order not found")

    # 获取选中的商品
    selected_items = request_data.get('selected_items', [])
    if not selected_items:
        logger.error(f"❌ 没有选中任何商品")
        raise HTTPException(status_code=400, detail="No items selected")

    try:
        # 调用 Printify 服务生成订单
        from app.services.printify_fulfillment_service import PrintifyFulfillmentService
        fulfillment_service = PrintifyFulfillmentService()
        
        # 为选中的商品添加商品映射信息
        enhanced_selected_items = []
        for item in selected_items:
            from app.models.product import ProductVariant
            from app.models.product import ProductMapping
            from app.models.external_system import ExternalSystem, ExternalSystemType
            from sqlalchemy import and_
            
            core_variant = None
            mapping = None
            
            # 如果商品已经有 core_variant_id，直接使用它查找映射
            if item.get('core_variant_id'):
                variant_result = await db.execute(
                    select(ProductVariant).where(
                        and_(
                            ProductVariant.id == item['core_variant_id'],
                            ProductVariant.tenant_id == tenant.id
                        )
                    )
                )
                core_variant = variant_result.scalar_one_or_none()
                logger.info(f"🔍 使用已有的 core_variant_id: {item['core_variant_id']}, 找到变体: {core_variant is not None}")
            else:
                # 尝试通过 SKU 查找核心变体
                sku = item.get('metadata', {}).get('sku')
                if sku:
                    logger.info(f"🔍 通过 SKU 查找核心变体: {sku}")
                    variant_result = await db.execute(
                        select(ProductVariant).where(
                            and_(
                                ProductVariant.tenant_id == tenant.id,
                                ProductVariant.sku == sku
                            )
                        )
                    )
                    core_variant = variant_result.scalar_one_or_none()
                    logger.info(f"🔍 SKU 查找结果: {core_variant is not None}")
            
            # 如果找到了核心变体，查找 Printify 商品映射
            if core_variant:
                # 查找 Printify 外部系统
                external_system_result = await db.execute(
                    select(ExternalSystem).where(
                        and_(
                            ExternalSystem.tenant_id == tenant.id,
                            ExternalSystem.system_type == ExternalSystemType.PRINTIFY
                        )
                    )
                )
                external_system = external_system_result.scalar_one_or_none()
                
                if external_system:
                    logger.info(f"🔍 查找 Printify 商品映射: core_variant_id={core_variant.id}, external_system_id={external_system.id}")
                    mapping_result = await db.execute(
                        select(ProductMapping).where(
                            and_(
                                ProductMapping.core_variant_id == core_variant.id,
                                ProductMapping.tenant_id == tenant.id,
                                ProductMapping.external_system_id == external_system.id
                            )
                        )
                    )
                    mapping = mapping_result.scalar_one_or_none()
                    logger.info(f"🔍 映射查找结果: {mapping is not None}")
                else:
                    logger.warning(f"⚠️ 未找到 Printify 外部系统: tenant_id={tenant.id}")
            else:
                sku = item.get('metadata', {}).get('sku')
                logger.warning(f"⚠️ 未找到核心变体: sku={sku}, core_variant_id={item.get('core_variant_id')}")
            
            # 如果找到了映射，创建增强的行项目数据
            if mapping:
                enhanced_item = item.copy()
                enhanced_item['core_product_id'] = core_variant.product_id
                enhanced_item['core_variant_id'] = core_variant.id
                enhanced_item['external_product_id'] = mapping.external_product_id
                enhanced_item['external_variant_id'] = mapping.external_variant_id
                enhanced_selected_items.append(enhanced_item)
                logger.info(f"✅ 为商品添加了商品映射信息: external_product_id={mapping.external_product_id}, external_variant_id={mapping.external_variant_id}")
            else:
                # 如果没有找到映射，记录详细信息
                sku = item.get('metadata', {}).get('sku')
                logger.warning(f"⚠️ 商品没有找到 Printify 映射: sku={sku}, core_variant_id={item.get('core_variant_id')}, item={item}")
                # 仍然添加到列表中，但会在 _build_fulfillment_data 中被跳过
                enhanced_selected_items.append(item)
        
        # 检查是否有任何商品找到了映射
        items_with_mapping = [item for item in enhanced_selected_items if item.get('external_product_id') and item.get('external_variant_id')]
        if not items_with_mapping:
            logger.error(f"❌ 所有选中商品都没有找到 Printify 映射: selected_items_count={len(selected_items)}")
            raise HTTPException(
                status_code=400, 
                detail="No items have valid Printify product mappings. Please ensure all selected items have been mapped to Printify products."
            )
        
        logger.info(f"✅ 找到 {len(items_with_mapping)}/{len(enhanced_selected_items)} 个商品有 Printify 映射")
        
        # 创建包含选中商品的临时 SCM 订单对象
        temp_scm_order = SCMOrder(
            id=scm_order.id,
            tenant_id=scm_order.tenant_id,
            source_order_id=scm_order.source_order_id,
            scm_order_number=scm_order.scm_order_number,
            status=scm_order.status,
            fulfillment_status=scm_order.fulfillment_status,
            routing_strategy=scm_order.routing_strategy,
            line_items=enhanced_selected_items,  # 使用增强的行项目数据
            currency=scm_order.currency,
            customer_email=scm_order.customer_email,
            customer_name=scm_order.customer_name,
            customer_phone=scm_order.customer_phone,
            shipping_address=scm_order.shipping_address,
            billing_address=scm_order.billing_address,
            routing_metadata=scm_order.routing_metadata,
            tracking_number=scm_order.tracking_number,
            tracking_url=scm_order.tracking_url,
            carrier=scm_order.carrier,
            shipped_at=scm_order.shipped_at,
            delivered_at=scm_order.delivered_at,
            error_message=scm_order.error_message,
            retry_count=scm_order.retry_count,
            shopify_fulfillment_order_id=scm_order.shopify_fulfillment_order_id,
            shopify_fulfillment_id=scm_order.shopify_fulfillment_id,
            created_at=scm_order.created_at,
            updated_at=scm_order.updated_at,
            fulfilled_at=scm_order.fulfilled_at,
        )
        
        # 生成 Printify 订单
        printify_result = await fulfillment_service.create_fulfillment_order(
            scm_order=temp_scm_order,
            tenant=tenant,
            db=db
        )
        
        # 更新 SCM 订单状态
        scm_order.fulfillment_status = 'fulfilled'
        scm_order.tracking_number = printify_result.get('tracking_number')
        scm_order.tracking_url = printify_result.get('tracking_url')
        scm_order.carrier = printify_result.get('carrier')
        scm_order.shipped_at = datetime.utcnow()
        
        # 更新路由元数据
        if not scm_order.routing_metadata:
            scm_order.routing_metadata = {}
        scm_order.routing_metadata['printify_order_id'] = printify_result.get('fulfillment_id')
        scm_order.routing_metadata['printify_status'] = printify_result.get('status')
        scm_order.routing_metadata['generated_at'] = datetime.utcnow().isoformat()
        
        # 将 Printify 订单保存到数据库
        from app.models.printify_order import PrintifyOrder
        from app.models.external_system import ExternalSystem, ExternalSystemType
        
        # 获取 Printify 外部系统
        external_system_result = await db.execute(
            select(ExternalSystem).where(
                and_(
                    ExternalSystem.tenant_id == tenant.id,
                    ExternalSystem.system_type == ExternalSystemType.PRINTIFY
                )
            )
        )
        external_system = external_system_result.scalar_one_or_none()
        
        if external_system:
            # 创建 Printify 订单记录
            printify_order = PrintifyOrder(
                tenant_id=tenant.id,
                external_system_id=external_system.id,
                external_order_id=printify_result.get('fulfillment_id'),
                scm_order_id=scm_order.id,  # 关联到 SCM 订单
                status=printify_result.get('status', 'pending'),
                total_price=printify_result.get('total_price', 0),
                currency=printify_result.get('currency', 'USD'),
                customer_email=scm_order.customer_email,
                customer_name=scm_order.customer_name,
                shipping_address=scm_order.shipping_address,
                billing_address=scm_order.billing_address,
                printify_data=printify_result,
                external_data=printify_result,
                tracking_number=printify_result.get('tracking_number'),
                tracking_url=printify_result.get('tracking_url'),
                carrier=printify_result.get('carrier'),
            )
            
            db.add(printify_order)
            logger.info(f"✅ Printify 订单已保存到数据库: external_order_id={printify_result.get('fulfillment_id')}, scm_order_id={scm_order.id}")
        else:
            logger.warning(f"⚠️ 未找到 Printify 外部系统，无法保存订单到数据库")
        
        await db.commit()
        await db.refresh(scm_order)
        
        logger.info(f"✅ Printify 订单生成成功: scm_order_id={scm_order_id}, printify_order_id={printify_result.get('fulfillment_id')}")
        
        return {
            "success": True,
            "message": "Printify order generated successfully",
            "printify_order_id": printify_result.get('fulfillment_id'),
            "tracking_number": printify_result.get('tracking_number'),
            "tracking_url": printify_result.get('tracking_url'),
            "carrier": printify_result.get('carrier'),
            "status": printify_result.get('status'),
            "selected_items_count": len(selected_items)
        }
        
    except Exception as e:
        logger.error(f"❌ 生成 Printify 订单失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to generate Printify order: {str(e)}")


@router.post("/batch-update-shopify-fulfillment", response_model=dict)
async def batch_update_shopify_fulfillment(
    request_data: dict,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> dict:
    """
    批量更新 Shopify fulfillment
    """
    from app.core.hashids_utils import decode_id
    from app.core.logging import RequestLogger
    from app.services.shopify_fulfillment_service import ShopifyFulfillmentService
    
    logger = RequestLogger("scm_orders.batch_update_shopify_fulfillment")
    tenant, user = auth
    
    try:
        scm_order_hashids = request_data.get('scm_order_hashids', [])
        if not scm_order_hashids:
            raise HTTPException(status_code=400, detail="No SCM orders provided")
        
        logger.info(f"🚀 开始批量更新 Shopify fulfillment: count={len(scm_order_hashids)}")
        
        # 解码 SCM 订单 hashids
        scm_order_ids = []
        for hashid in scm_order_hashids:
            try:
                scm_order_id = decode_id(hashid)
                scm_order_ids.append(scm_order_id)
                logger.info(f"✅ Hashid 解码成功: {hashid} -> {scm_order_id}")
            except Exception as e:
                logger.error(f"❌ Hashid 解码失败: {hashid}, 错误: {str(e)}")
                raise HTTPException(status_code=400, detail=f"Invalid SCM order ID: {hashid}")
        
        # 查询 SCM 订单
        result = await db.execute(
            select(SCMOrder).where(
                SCMOrder.id.in_(scm_order_ids),
                SCMOrder.tenant_id == tenant.id
            )
        )
        scm_orders = result.scalars().all()
        
        if not scm_orders:
            logger.error(f"❌ 未找到 SCM 订单: scm_order_ids={scm_order_ids}")
            raise HTTPException(status_code=404, detail="SCM orders not found")
        
        logger.info(f"✅ 找到 {len(scm_orders)} 个 SCM 订单")
        
        # 检查订单状态 - 只处理有跟踪号的订单
        orders_with_tracking = []
        orders_without_tracking = []
        
        for scm_order in scm_orders:
            if scm_order.tracking_number and scm_order.tracking_number.strip() and scm_order.tracking_number != 'N/A':
                orders_with_tracking.append(scm_order)
            else:
                orders_without_tracking.append(scm_order)
                logger.warning(f"⚠️ SCM 订单缺少跟踪号: {scm_order.scm_order_number}")
        
        if not orders_with_tracking:
            logger.error(f"❌ 没有找到有跟踪号的 SCM 订单")
            raise HTTPException(
                status_code=400, 
                detail="No SCM orders with tracking numbers found. Please ensure orders have tracking numbers before updating Shopify fulfillment."
            )
        
        if orders_without_tracking:
            logger.info(f"ℹ️ 跳过 {len(orders_without_tracking)} 个没有跟踪号的订单")
        
        # 只处理有跟踪号的订单
        scm_orders = orders_with_tracking
        
        # 创建 Shopify fulfillment 服务
        fulfillment_service = ShopifyFulfillmentService()
        
        # 批量创建 fulfillments
        results = await fulfillment_service.batch_create_fulfillments(
            scm_orders=scm_orders,
            tenant=tenant,
            db=db
        )
        
        # 更新 SCM 订单的 Shopify fulfillment 信息
        for scm_order in scm_orders:
            # 查找对应的成功结果
            success_result = next(
                (r for r in results["success"] if r["scm_order_id"] == scm_order.id), 
                None
            )
            
            if success_result:
                scm_order.shopify_fulfillment_id = success_result["fulfillment_id"]
                scm_order.shopify_order_id = success_result["shopify_order_id"]
                
                # 更新路由元数据
                if not scm_order.routing_metadata:
                    scm_order.routing_metadata = {}
                scm_order.routing_metadata['shopify_fulfillment_id'] = success_result["fulfillment_id"]
                scm_order.routing_metadata['shopify_updated_at'] = datetime.utcnow().isoformat()
        
        await db.commit()
        
        logger.info(f"✅ 批量更新 Shopify fulfillment 完成: success={len(results['success'])}, failed={len(results['failed'])}")
        
        # 构建跳过的订单信息
        skipped_orders = []
        for order in orders_without_tracking:
            skipped_orders.append({
                "scm_order_id": order.id,
                "scm_order_number": order.scm_order_number,
                "reason": "Missing tracking number"
            })
        
        return {
            "success": True,
            "message": f"Batch update completed: {len(results['success'])} successful, {len(results['failed'])} failed, {len(skipped_orders)} skipped",
            "results": results,
            "skipped_orders": skipped_orders
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 批量更新 Shopify fulfillment 失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to batch update Shopify fulfillment: {str(e)}")


@router.post("/{scm_order_hashid}/bind-printify-order", response_model=dict)
async def bind_printify_order_to_scm(
    scm_order_hashid: str,
    request_data: dict,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> dict:
    """
    将 Printify 订单绑定到 SCM 订单
    """
    from app.core.hashids_utils import decode_id
    from app.core.logging import RequestLogger
    from app.models.scm_order import SCMOrder
    from app.models.printify_order import PrintifyOrder
    from sqlalchemy import select, and_
    from fastapi import HTTPException
    from datetime import datetime

    logger = RequestLogger("scm_orders.bind_printify_order")
    tenant, user = auth

    try:
        # 解码 SCM 订单 hashid
        scm_order_id = decode_id(scm_order_hashid)
        logger.info(f"✅ SCM 订单 Hashid 解码成功: {scm_order_hashid} -> {scm_order_id}")
    except Exception as e:
        logger.error(f"❌ SCM 订单 Hashid 解码失败: {scm_order_hashid}, 错误: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid SCM order ID")

    try:
        # 获取 Printify 订单 ID
        printify_order_id = request_data.get('printify_order_id')
        if not printify_order_id:
            raise HTTPException(status_code=400, detail="Printify order ID is required")

        # 查询 SCM 订单
        scm_result = await db.execute(
            select(SCMOrder).where(
                and_(
                    SCMOrder.id == scm_order_id,
                    SCMOrder.tenant_id == tenant.id
                )
            )
        )
        scm_order = scm_result.scalar_one_or_none()

        if not scm_order:
            logger.error(f"❌ SCM 订单不存在: scm_order_id={scm_order_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="SCM order not found")

        # 查询 Printify 订单
        printify_result = await db.execute(
            select(PrintifyOrder).where(
                and_(
                    PrintifyOrder.id == printify_order_id,
                    PrintifyOrder.tenant_id == tenant.id
                )
            )
        )
        printify_order = printify_result.scalar_one_or_none()

        if not printify_order:
            logger.error(f"❌ Printify 订单不存在: printify_order_id={printify_order_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="Printify order not found")

        # 检查 Printify 订单是否已经绑定到其他 SCM 订单
        if printify_order.scm_order_id and printify_order.scm_order_id != scm_order_id:
            logger.warning(f"⚠️ Printify 订单已绑定到其他 SCM 订单: printify_order_id={printify_order_id}, existing_scm_order_id={printify_order.scm_order_id}")
            raise HTTPException(status_code=400, detail="Printify order is already bound to another SCM order")

        # 检查 SCM 订单是否已经绑定到其他 Printify 订单
        existing_printify_result = await db.execute(
            select(PrintifyOrder).where(
                and_(
                    PrintifyOrder.scm_order_id == scm_order_id,
                    PrintifyOrder.tenant_id == tenant.id,
                    PrintifyOrder.id != printify_order_id
                )
            )
        )
        existing_printify_order = existing_printify_result.scalar_one_or_none()

        if existing_printify_order:
            logger.warning(f"⚠️ SCM 订单已绑定到其他 Printify 订单: scm_order_id={scm_order_id}, existing_printify_order_id={existing_printify_order.id}")
            raise HTTPException(status_code=400, detail="SCM order is already bound to another Printify order")

        # 执行绑定
        printify_order.scm_order_id = scm_order_id
        scm_order.printify_order_id = printify_order.external_order_id
        scm_order.printify_shop_id = str(printify_order.external_system_id)

        # 更新路由元数据
        if not scm_order.routing_metadata:
            scm_order.routing_metadata = {}
        scm_order.routing_metadata['printify_order_id'] = printify_order.external_order_id
        scm_order.routing_metadata['printify_bind_at'] = datetime.utcnow().isoformat()
        scm_order.routing_metadata['printify_bind_by'] = user.email

        await db.commit()

        logger.info(f"✅ Printify 订单绑定成功: scm_order_id={scm_order_id}, printify_order_id={printify_order_id}")

        return {
            "success": True,
            "message": "Printify order bound to SCM order successfully",
            "scm_order_id": scm_order_id,
            "printify_order_id": printify_order_id,
            "scm_order_number": scm_order.scm_order_number,
            "printify_external_order_id": printify_order.external_order_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 绑定 Printify 订单失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to bind Printify order: {str(e)}")


@router.post("/{scm_order_hashid}/unbind-printify-order", response_model=dict)
async def unbind_printify_order_from_scm(
    scm_order_hashid: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> dict:
    """
    解绑 SCM 订单与 Printify 订单的关联
    """
    from app.core.hashids_utils import decode_id
    from app.core.logging import RequestLogger
    from app.models.scm_order import SCMOrder
    from app.models.printify_order import PrintifyOrder
    from sqlalchemy import select, and_
    from fastapi import HTTPException
    from datetime import datetime

    logger = RequestLogger("scm_orders.unbind_printify_order")
    tenant, user = auth

    try:
        # 解码 SCM 订单 hashid
        scm_order_id = decode_id(scm_order_hashid)
        logger.info(f"✅ SCM 订单 Hashid 解码成功: {scm_order_hashid} -> {scm_order_id}")
    except Exception as e:
        logger.error(f"❌ SCM 订单 Hashid 解码失败: {scm_order_hashid}, 错误: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid SCM order ID")

    try:
        # 查询 SCM 订单
        scm_result = await db.execute(
            select(SCMOrder).where(
                and_(
                    SCMOrder.id == scm_order_id,
                    SCMOrder.tenant_id == tenant.id
                )
            )
        )
        scm_order = scm_result.scalar_one_or_none()

        if not scm_order:
            logger.error(f"❌ SCM 订单不存在: scm_order_id={scm_order_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="SCM order not found")

        # 查询绑定的 Printify 订单
        printify_result = await db.execute(
            select(PrintifyOrder).where(
                and_(
                    PrintifyOrder.scm_order_id == scm_order_id,
                    PrintifyOrder.tenant_id == tenant.id
                )
            )
        )
        printify_order = printify_result.scalar_one_or_none()

        if not printify_order:
            logger.warning(f"⚠️ SCM 订单没有绑定任何 Printify 订单: scm_order_id={scm_order_id}")
            raise HTTPException(status_code=404, detail="No Printify order bound to this SCM order")

        # 执行解绑
        printify_order.scm_order_id = None
        scm_order.printify_order_id = None
        scm_order.printify_shop_id = None

        # 更新路由元数据
        if scm_order.routing_metadata:
            scm_order.routing_metadata.pop('printify_order_id', None)
            scm_order.routing_metadata['printify_unbind_at'] = datetime.utcnow().isoformat()
            scm_order.routing_metadata['printify_unbind_by'] = user.email

        await db.commit()

        logger.info(f"✅ Printify 订单解绑成功: scm_order_id={scm_order_id}, printify_order_id={printify_order.id}")

        return {
            "success": True,
            "message": "Printify order unbound from SCM order successfully",
            "scm_order_id": scm_order_id,
            "printify_order_id": printify_order.id,
            "scm_order_number": scm_order.scm_order_number,
            "printify_external_order_id": printify_order.external_order_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 解绑 Printify 订单失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to unbind Printify order: {str(e)}")


@router.post("/{scm_order_hashid}/bind-core-order", response_model=dict)
async def bind_core_order_to_scm(
    scm_order_hashid: str,
    request: dict,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> Any:
    """
    绑定核心订单到 SCM 订单
    """
    from app.core.logging import get_logger
    from app.core.hashids_utils import decode_id
    
    logger = get_logger(__name__)
    tenant, user = auth
    logger.info(f"🔗 开始绑定核心订单到 SCM 订单: scm_order_hashid={scm_order_hashid}, tenant_id={tenant.id}")

    try:
        # 解码 SCM 订单 hashid
        try:
            scm_order_id = decode_id(scm_order_hashid)
            logger.info(f"✅ SCM 订单 hashid 解码成功: {scm_order_hashid} -> {scm_order_id}")
        except Exception as e:
            logger.error(f"❌ SCM 订单 hashid 解码失败: {scm_order_hashid}, 错误: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid SCM order ID")

        # 获取核心订单 hashid
        core_order_hashid = request.get("core_order_hashid")
        if not core_order_hashid:
            logger.error("❌ 缺少核心订单 hashid")
            raise HTTPException(status_code=400, detail="Core order hashid is required")

        # 解码核心订单 hashid
        try:
            core_order_id = decode_id(core_order_hashid)
            logger.info(f"✅ 核心订单 hashid 解码成功: {core_order_hashid} -> {core_order_id}")
        except Exception as e:
            logger.error(f"❌ 核心订单 hashid 解码失败: {core_order_hashid}, 错误: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid core order ID")

        # 获取 SCM 订单
        scm_order = await db.get(SCMOrder, scm_order_id)
        if not scm_order or scm_order.tenant_id != tenant.id:
            logger.error(f"❌ SCM 订单不存在: scm_order_id={scm_order_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="SCM order not found")

        # 获取核心订单
        core_order = await db.get(Order, core_order_id)
        if not core_order or core_order.tenant_id != tenant.id:
            logger.error(f"❌ 核心订单不存在: core_order_id={core_order_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="Core order not found")

        # 检查 SCM 订单是否已绑定到其他核心订单
        if scm_order.source_order_id and scm_order.source_order_id != core_order_id:
            logger.warning(f"⚠️ SCM 订单已绑定到其他核心订单: scm_order_id={scm_order_id}, existing_source_order_id={scm_order.source_order_id}")
            raise HTTPException(status_code=400, detail="SCM order is already bound to another core order")

        # 检查核心订单是否已绑定到其他 SCM 订单
        existing_scm_order = await db.execute(
            select(SCMOrder).where(
                SCMOrder.source_order_id == core_order_id,
                SCMOrder.tenant_id == tenant.id,
                SCMOrder.id != scm_order_id
            )
        )
        existing_scm_order = existing_scm_order.scalar_one_or_none()
        if existing_scm_order:
            logger.warning(f"⚠️ 核心订单已绑定到其他 SCM 订单: core_order_id={core_order_id}, existing_scm_order_id={existing_scm_order.id}")
            raise HTTPException(status_code=400, detail="Core order is already bound to another SCM order")

        # 执行绑定
        scm_order.source_order_id = core_order_id
        
        # 更新 Shopify 订单 ID（从核心订单复制）
        if core_order.external_order_id:
            scm_order.shopify_order_id = core_order.external_order_id
            logger.info(f"✅ 更新 SCM 订单 Shopify 订单 ID: {core_order.external_order_id}")

        # 更新路由元数据
        if not scm_order.routing_metadata:
            scm_order.routing_metadata = {}
        scm_order.routing_metadata['core_order_id'] = core_order_id
        scm_order.routing_metadata['core_bind_at'] = datetime.utcnow().isoformat()
        scm_order.routing_metadata['core_bind_by'] = user.email

        # 提交更改
        await db.commit()
        await db.refresh(scm_order)

        logger.info(f"✅ SCM 订单绑定核心订单成功: scm_order_id={scm_order_id}, core_order_id={core_order_id}")

        return {"message": "SCM order bound to core order successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 绑定核心订单失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to bind core order: {str(e)}")


@router.post("/{scm_order_hashid}/unbind-core-order", response_model=dict)
async def unbind_core_order_from_scm(
    scm_order_hashid: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> Any:
    """
    解绑 SCM 订单与核心订单
    """
    from app.core.logging import get_logger
    from app.core.hashids_utils import decode_id
    
    logger = get_logger(__name__)
    tenant, user = auth
    logger.info(f"🔗 开始解绑 SCM 订单与核心订单: scm_order_hashid={scm_order_hashid}, tenant_id={tenant.id}")

    try:
        # 解码 SCM 订单 hashid
        try:
            scm_order_id = decode_id(scm_order_hashid)
            logger.info(f"✅ SCM 订单 hashid 解码成功: {scm_order_hashid} -> {scm_order_id}")
        except Exception as e:
            logger.error(f"❌ SCM 订单 hashid 解码失败: {scm_order_hashid}, 错误: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid SCM order ID")

        # 获取 SCM 订单
        scm_order = await db.get(SCMOrder, scm_order_id)
        if not scm_order or scm_order.tenant_id != tenant.id:
            logger.error(f"❌ SCM 订单不存在: scm_order_id={scm_order_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="SCM order not found")

        if not scm_order.source_order_id:
            logger.warning(f"⚠️ SCM 订单未绑定核心订单: scm_order_id={scm_order_id}")
            raise HTTPException(status_code=400, detail="SCM order is not bound to any core order")

        # 执行解绑
        scm_order.source_order_id = None
        
        # 清理 Shopify 订单 ID（因为不再与核心订单关联）
        if scm_order.shopify_order_id:
            logger.info(f"✅ 清理 SCM 订单 Shopify 订单 ID: {scm_order.shopify_order_id}")
            scm_order.shopify_order_id = None

        # 更新路由元数据
        if scm_order.routing_metadata:
            scm_order.routing_metadata.pop('core_order_id', None)
            scm_order.routing_metadata['core_unbind_at'] = datetime.utcnow().isoformat()
            scm_order.routing_metadata['core_unbind_by'] = user.email

        # 提交更改
        await db.commit()
        await db.refresh(scm_order)

        logger.info(f"✅ SCM 订单解绑核心订单成功: scm_order_id={scm_order_id}")

        return {"message": "SCM order unbound from core order successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 解绑核心订单失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to unbind core order: {str(e)}")
