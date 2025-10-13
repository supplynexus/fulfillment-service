"""
SCM Orders API endpoints
"""

from typing import List, Optional
import time
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
                tenant=tenant
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

            normalized_items.append(
                {
                    "core_product_id": core_product_id,
                    "core_variant_id": core_variant_id,
                    "quantity": max(1, quantity),
                    "metadata": {
                        "sku": display_sku,
                        "title": display_title,
                        "variant_label": raw.get("item_metadata", {}).get("variant_title")
                        if isinstance(raw, dict)
                        else None,
                        "image_url": image_url,
                        "source_line_item_id": raw.get("item_metadata", {}).get("source_line_item_id")
                        if isinstance(raw, dict)
                        else None,
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

    # 创建SCM订单
    scm_order = SCMOrder(
        tenant_id=tenant.id,
        # 核心SCM订单不直接绑定外部系统
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


@router.put("/{scm_order_id}", response_model=SCMOrderResponse)
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


@router.delete("/{scm_order_id}")
async def delete_scm_order(
    scm_order_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
):
    """
    删除SCM订单
    """
    tenant, user = auth

    result = await db.execute(
        select(SCMOrder).where(
            SCMOrder.id == scm_order_id, SCMOrder.tenant_id == tenant.id
        )
    )
    scm_order = result.scalar_one_or_none()

    if not scm_order:
        raise HTTPException(status_code=404, detail="SCM order not found")

    # 检查是否可以删除（只有创建状态的订单可以删除）
    if scm_order.status not in ["created", "failed"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete SCM order with status: " + scm_order.status,
        )

    await db.delete(scm_order)
    await db.commit()

    return {"message": "SCM order deleted successfully"}


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
        
        # 创建包含选中商品的临时 SCM 订单对象
        temp_scm_order = SCMOrder(
            id=scm_order.id,
            tenant_id=scm_order.tenant_id,
            source_order_id=scm_order.source_order_id,
            scm_order_number=scm_order.scm_order_number,
            status=scm_order.status,
            fulfillment_status=scm_order.fulfillment_status,
            routing_strategy=scm_order.routing_strategy,
            line_items=selected_items,  # 只包含选中的商品
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
