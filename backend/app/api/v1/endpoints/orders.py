"""
Order management endpoints
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime

from app.core.database import get_async_db
from app.core.tenant_auth_dependency import verify_tenant_auth
from app.models.tenant import Tenant
from app.models.user import User
from app.models.external_system import ExternalSystemType
from app.schemas.order import OrderResponse, OrderListResponse, OrderSyncResponse, BatchUpdateShopifyStatusRequest
from app.services.shopify.order_service import ShopifyOrderService
from app.services.printify_service import PrintifyService
from app.services.external_system_service import ExternalSystemService
from app.tasks.shopify_tasks import sync_shopify_orders_task

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=OrderListResponse)
async def get_orders(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    core_product_id: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> OrderListResponse:
    """
    获取订单列表
    """
    from app.core.logging import RequestLogger

    logger = RequestLogger("orders.get_orders")

    try:
        # 计算skip值
        skip = (page - 1) * limit

        logger.info(
            f"🔍 开始处理订单列表请求: page={page}, limit={limit}, skip={skip}, status={status}, search={search}, sort_by={sort_by}, sort_order={sort_order}"
        )

        tenant, user = auth
        logger.info(
            f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}"
        )

        # 按商品筛选：解码商品 hashid
        product_id_int: Optional[int] = None
        if core_product_id:
            from app.core.hashids_utils import decode_id
            try:
                product_id_int = decode_id(core_product_id)
                logger.info(f"🔍 按商品筛选: core_product_id={core_product_id} -> product_id={product_id_int}")
            except Exception:
                logger.warning(f"⚠️ 无效的商品 hashid，忽略: core_product_id={core_product_id}")

        logger.info(f"🔍 初始化 ShopifyOrderService...")
        order_service = ShopifyOrderService(db)
        logger.info(f"✅ ShopifyOrderService 初始化成功")

        # 获取订单列表和总数
        logger.info(f"🔍 查询订单列表...")
        try:
            orders, total = await order_service.get_orders_paginated(
                tenant_id=tenant.id,
                skip=skip,
                limit=limit,
                status=status,
                search=search,
                sort_by=sort_by,
                sort_order=sort_order,
                core_product_id=product_id_int,
            )
            logger.info(f"✅ 查询订单成功: 找到 {len(orders)} 个订单，总数 {total}")
        except Exception as e:
            logger.error(f"❌ 查询订单失败: {str(e)}")
            import traceback

            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            raise HTTPException(
                status_code=500, detail=f"Failed to get orders: {str(e)}"
            )

        # 批量查询每个订单的 SCM 订单数量
        logger.info(f"🔍 查询每个订单的 SCM 订单数量...")
        from app.models.scm_order import ScmOrderSource
        
        order_ids = [order.id for order in orders]
        scm_counts_result = await db.execute(
            select(
                ScmOrderSource.source_order_id,
                func.count(ScmOrderSource.scm_order_id).label('scm_count')
            )
            .where(
                ScmOrderSource.source_order_id.in_(order_ids),
                ScmOrderSource.tenant_id == tenant.id
            )
            .group_by(ScmOrderSource.source_order_id)
        )
        scm_counts_map = {row[0]: row[1] for row in scm_counts_result.fetchall()}
        logger.info(f"✅ 查询到 {len(scm_counts_map)} 个订单有 SCM 订单")

        # 有 SCM 的订单：仅按多对多表 scm_order_sources 查 SCM 预览与 Printify 链接
        from app.models.scm_order import SCMOrder, ScmOrderSource
        from app.core.hashids_utils import encode_id
        from sqlalchemy.orm import selectinload

        order_ids_with_scm = [oid for oid in order_ids if scm_counts_map.get(oid, 0) > 0]
        scm_preview_by_order: dict = {}
        if order_ids_with_scm:
            src_result = await db.execute(
                select(ScmOrderSource.source_order_id, ScmOrderSource.scm_order_id).where(
                    ScmOrderSource.source_order_id.in_(order_ids_with_scm),
                    ScmOrderSource.tenant_id == tenant.id,
                )
            )
            pairs = src_result.fetchall()
            scm_ids = list({p[1] for p in pairs})
            scm_result = await db.execute(
                select(SCMOrder)
                .where(SCMOrder.id.in_(scm_ids), SCMOrder.tenant_id == tenant.id)
                .options(selectinload(SCMOrder.printify_orders))
            )
            scm_list = scm_result.scalars().all()
            scm_by_id = {s.id: s for s in scm_list}
            order_to_scm_ids: dict = {}
            for src_oid, scm_id in pairs:
                order_to_scm_ids.setdefault(src_oid, []).append(scm_id)
            for oid in order_ids_with_scm:
                scm_ids_for_order = order_to_scm_ids.get(oid, [])[:5]
                preview = []
                for sid in scm_ids_for_order:
                    scm = scm_by_id.get(sid)
                    if not scm:
                        continue
                    printify_shop_id = None
                    if getattr(scm, "printify_orders", None):
                        for po in scm.printify_orders:
                            pd = (po.printify_data or getattr(po, "external_data", None)) if hasattr(po, "printify_data") else None
                            if isinstance(pd, dict) and pd.get("shop_id") is not None:
                                printify_shop_id = str(pd.get("shop_id"))
                                break
                    if not printify_shop_id and getattr(scm, "printify_shop_id", None):
                        printify_shop_id = str(scm.printify_shop_id)
                    preview.append({
                        "id_hashid": encode_id(scm.id),
                        "scm_order_number": scm.scm_order_number or "",
                        "printify_order_id": scm.printify_order_id,
                        "printify_shop_id": printify_shop_id,
                    })
                scm_preview_by_order[oid] = preview

        # Shopify 订单：批量解析 external_order_id 并查外部系统，生成后台订单链接
        import re
        from app.models.external_system import ExternalSystem

        shopify_gid_re = re.compile(r"^gid://shopify/Order/(\d+)$")
        order_id_to_shopify_admin_url: dict[int, str] = {}
        es_ids = list({o.external_system_id for o in orders if getattr(o, "external_system_id", None) is not None})
        shopify_orders = [(o.id, o.external_order_id, getattr(o, "external_system_id", None)) for o in orders if o.external_order_id and shopify_gid_re.match(o.external_order_id.strip())]
        if shopify_orders:
            store_handle_by_es_id: dict[int, str] = {}
            if es_ids:
                es_result = await db.execute(
                    select(ExternalSystem.id, ExternalSystem.external_id, ExternalSystem.base_url, ExternalSystem.external_system_id).where(
                        ExternalSystem.id.in_(es_ids),
                        ExternalSystem.tenant_id == tenant.id,
                        ExternalSystem.system_type == ExternalSystemType.SHOPIFY,
                    )
                )
                for row in es_result.fetchall():
                    handle = (row.external_id or "").strip()
                    if not handle and (row.base_url or row.external_system_id):
                        url_or_domain = (row.base_url or row.external_system_id or "").strip()
                        if ".myshopify.com" in url_or_domain:
                            handle = url_or_domain.replace("https://", "").replace("http://", "").split(".myshopify.com")[0].strip()
                    if handle:
                        store_handle_by_es_id[row.id] = handle
            fallback_handle = None
            fallback_result = await db.execute(
                select(ExternalSystem.external_id, ExternalSystem.base_url, ExternalSystem.external_system_id).where(
                    ExternalSystem.tenant_id == tenant.id,
                    ExternalSystem.system_type == ExternalSystemType.SHOPIFY,
                    ExternalSystem.is_active == True,
                ).limit(1)
            )
            fallback_row = fallback_result.fetchone()
            if fallback_row and (fallback_row.external_id or fallback_row.base_url or fallback_row.external_system_id):
                fallback_handle = (fallback_row.external_id or "").strip()
                if not fallback_handle and (fallback_row.base_url or fallback_row.external_system_id):
                    url_or_domain = (fallback_row.base_url or fallback_row.external_system_id or "").strip()
                    if ".myshopify.com" in url_or_domain:
                        fallback_handle = url_or_domain.replace("https://", "").replace("http://", "").split(".myshopify.com")[0].strip()
            for oid, ext_oid, es_id in shopify_orders:
                match = shopify_gid_re.match(ext_oid.strip())
                if not match:
                    continue
                numeric_id = match.group(1)
                handle = (es_id and store_handle_by_es_id.get(es_id)) or fallback_handle
                if handle:
                    order_id_to_shopify_admin_url[oid] = f"https://admin.shopify.com/store/{handle}/orders/{numeric_id}"

        # 转换为响应格式
        logger.info(f"🔍 转换订单响应格式...")
        try:
            order_responses = []
            for order in orders:
                # 获取该订单的 SCM 订单数量
                scm_orders_count = scm_counts_map.get(order.id, 0)
                external_order_admin_url = order_id_to_shopify_admin_url.get(order.id)

                order_data = {
                    "id_hashid": encode_id(order.id),
                    "order_number": order.order_number or f"ORD-{order.id}",
                    "external_order_id": order.external_order_id,
                    "external_order_number": order.external_order_number,
                    "external_order_name": order.external_order_name,
                    "external_order_admin_url": external_order_admin_url,
                    "status": order.status,
                    "total_amount": float(order.total_amount) if order.total_amount else 0.0,
                    "currency": order.currency,
                    "customer_email": order.customer_email,
                    "customer_name": order.customer_name,
                    "customer_phone": order.customer_phone,
                    "shipping_address": order.shipping_address,
                    "billing_address": order.billing_address,
                    "line_items": [],
                    "order_date": order.order_date,
                    "fulfillment_status": order.fulfillment_status,
                    "tracking_number": order.tracking_number,
                    "tracking_url": order.tracking_url,
                    "address_validation_status": getattr(order, "address_validation_status", None),
                    "address_validation_reason_code": getattr(order, "address_validation_reason_code", None),
                    "address_validation_message": getattr(order, "address_validation_message", None),
                    "address_last_validated_at": getattr(order, "address_last_validated_at", None),
                    "created_at": order.created_at,
                    "updated_at": order.updated_at,
                    "scm_orders_count": scm_orders_count,
                    "scm_orders_preview": scm_preview_by_order.get(order.id),
                }
                order_responses.append(order_data)
            logger.info(f"✅ 订单响应格式转换成功: {len(order_responses)} 个订单")
        except Exception as e:
            logger.error(f"❌ 转换订单响应格式失败: {str(e)}")
            import traceback

            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            raise HTTPException(
                status_code=500, detail=f"Failed to convert order responses: {str(e)}"
            )

        # 计算总页数
        total_pages = (total + limit - 1) // limit

        # 返回符合 OrderListResponse 模型的数据结构
        result = {
            "orders": order_responses,
            "total": total,
            "total_pages": total_pages,
            "current_page": page,
            "skip": skip,
            "limit": limit,
        }

        logger.info(
            f"✅ 订单列表请求处理成功: total={total}, total_pages={total_pages}, page={page}, limit={limit}"
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 订单列表请求处理失败: {str(e)}")
        import traceback

        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{order_hashid}", response_model=OrderResponse)
async def get_order(
    order_hashid: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> OrderResponse:
    """
    获取单个订单详情
    """
    from app.models.order import OrderItem
    from sqlalchemy import select
    from app.core.hashids_utils import encode_id

    tenant, user = auth

    # 解码 hashid 为原始 ID
    from app.core.hashids_utils import decode_id
    try:
        order_id = decode_id(order_hashid)
        logger.info(f"✅ Hashid 解码成功: {order_hashid} -> {order_id}")
    except Exception as e:
        logger.error(f"❌ Hashid 解码失败: {order_hashid}, 错误: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid order ID")

    logger.info(f"🔍 开始处理订单详情请求: order_id={order_id}, tenant_id={tenant.id}")

    try:
        # 直接查询Order模型
        from app.models.order import Order
        from sqlalchemy import select
        
        order_query = select(Order).where(
            Order.id == order_id,
            Order.tenant_id == tenant.id
        )
        order_result = await db.execute(order_query)
        order = order_result.scalar_one_or_none()

        if not order:
            logger.warning(f"⚠️ 订单不存在: order_id={order_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="Order not found")

        # 获取订单行项目
        logger.info(f"🔍 查询订单行项目: order_id={order_id}")
        items_query = select(OrderItem).where(
            OrderItem.order_id == order_id,
            OrderItem.tenant_id == tenant.id
        )
        items_result = await db.execute(items_query)
        order_items = items_result.scalars().all()
        
        logger.info(f"✅ 找到 {len(order_items)} 个订单行项目")

        # Shopify store handle（用于商品链接）：先看订单关联的外部系统，否则用租户下任意 Shopify 配置（订单导入时可能未填 external_system_id）
        from app.models.external_system import ExternalSystem
        shopify_store_handle: Optional[str] = None
        if order.external_system_id:
            es_row = await db.execute(
                select(ExternalSystem.system_type, ExternalSystem.base_url, ExternalSystem.external_system_id).where(
                    ExternalSystem.id == order.external_system_id,
                    ExternalSystem.tenant_id == tenant.id,
                )
            )
            es = es_row.one_or_none()
            if es and es.system_type == ExternalSystemType.SHOPIFY:
                base_url = (es.base_url or "").strip() or (es.external_system_id or "")
                if ".myshopify.com" in base_url:
                    shopify_store_handle = base_url.replace("https://", "").replace("http://", "").split(".myshopify.com")[0].strip()
        if not shopify_store_handle:
            # 回退：订单未关联外部系统时，用本租户下第一个 Shopify 配置（行项目有 gid 时仍可生成链接）
            fallback_row = await db.execute(
                select(ExternalSystem.base_url, ExternalSystem.external_system_id).where(
                    ExternalSystem.tenant_id == tenant.id,
                    ExternalSystem.system_type == ExternalSystemType.SHOPIFY,
                    ExternalSystem.is_active == True,
                ).limit(1)
            )
            fallback = fallback_row.one_or_none()
            if fallback:
                base_url = (fallback.base_url or "").strip() or (fallback.external_system_id or "")
                if ".myshopify.com" in base_url:
                    shopify_store_handle = base_url.replace("https://", "").replace("http://", "").split(".myshopify.com")[0].strip()

        # Printify 商品 ID 映射：core_product_id -> printify external_product_id
        from app.models.product import ProductMapping
        core_product_ids = [item.core_product_id for item in order_items if item.core_product_id]
        printify_product_by_core: dict = {}
        if core_product_ids:
            pm_result = await db.execute(
                select(ProductMapping.core_product_id, ProductMapping.external_product_id).where(
                    ProductMapping.tenant_id == tenant.id,
                    ProductMapping.core_product_id.in_(core_product_ids),
                    ProductMapping.external_system_id.in_(
                        select(ExternalSystem.id).where(
                            ExternalSystem.tenant_id == tenant.id,
                            ExternalSystem.system_type == ExternalSystemType.PRINTIFY,
                        )
                    ),
                )
            )
            for row in pm_result.all():
                printify_product_by_core[row.core_product_id] = row.external_product_id

        # 构建 line_items 数组（含 Shopify / Printify 商品链接）
        line_items = []
        for item in order_items:
            shopify_product_url: Optional[str] = None
            if shopify_store_handle and item.external_product_id and "gid://shopify/Product/" in str(item.external_product_id):
                try:
                    shopify_product_id = str(item.external_product_id).split("/")[-1].strip()
                    if shopify_product_id.isdigit():
                        shopify_product_url = f"https://admin.shopify.com/store/{shopify_store_handle}/products/{shopify_product_id}"
                except Exception:
                    pass
            printify_product_url: Optional[str] = None
            if item.core_product_id and item.core_product_id in printify_product_by_core:
                pid = printify_product_by_core[item.core_product_id]
                if pid:
                    printify_product_url = f"https://printify.com/app/product-details/{pid}?fromProductsPage=1"

            core_product_id_hashid = encode_id(item.core_product_id) if item.core_product_id else None
            line_item = {
                "id": item.id,
                "title": item.title or "未知商品",
                "sku": item.sku,
                "variant_title": item.variant_title,
                "quantity": item.quantity,
                "price": float(item.unit_price) if item.unit_price else 0.0,  # 使用price字段
                "unit_price": float(item.unit_price) if item.unit_price else 0.0,
                "total_price": float(item.total_price) if item.total_price else 0.0,
                "core_product_id": item.core_product_id,
                "core_variant_id": item.core_variant_id,
                "core_product_id_hashid": core_product_id_hashid,  # 用于前端「去绑定 Printify」链接
                "external_product_id": item.external_product_id,
                "external_variant_id": item.external_variant_id,
                "fulfillment_status": item.fulfillment_status,
                "item_metadata": item.item_metadata or {},
                "shopify_product_url": shopify_product_url,
                "printify_product_url": printify_product_url,
            }
            line_items.append(line_item)

        # 转换为响应格式并添加 line_items
        order_data = {
            "id": order.id,
            "id_hashid": encode_id(order.id),
            "order_number": order.order_number,
            "external_order_id": order.external_order_id or order.shopify_order_id,
            "external_order_number": order.external_order_number,
            "external_order_name": order.external_order_name,
            "shopify_order_id": order.shopify_order_id,
            "shopify_order_number": order.external_order_number,
            "shopify_order_name": order.external_order_name,
            "status": order.status,
            "total_amount": float(order.total_amount) if order.total_amount else 0.0,
            "currency": order.currency,
            "customer_email": order.customer_email,
            "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
            "shipping_address": order.shipping_address,
            "billing_address": order.billing_address,
            "line_items": line_items,
            "order_date": order.order_date,
            "fulfillment_status": order.fulfillment_status,
            "tracking_number": order.tracking_number,
            "tracking_url": order.tracking_url,
            "external_data": order.external_data,
            "address_validation_status": getattr(order, "address_validation_status", None),
            "address_validation_reason_code": getattr(order, "address_validation_reason_code", None),
            "address_validation_message": getattr(order, "address_validation_message", None),
            "address_last_validated_at": getattr(order, "address_last_validated_at", None),
            "created_at": order.created_at,
            "updated_at": order.updated_at,
        }

        logger.info(f"✅ 订单详情请求处理成功: order_id={order_id}, line_items_count={len(line_items)}")
        return order_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 订单详情请求处理失败: {str(e)}")
        import traceback

        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/sync", response_model=OrderSyncResponse)
async def sync_orders(
    sync_recent_only: bool = True,
    max_orders: Optional[int] = 100,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> OrderSyncResponse:
    """
    手动触发订单同步（从 Shopify API 到 shopify_orders 表）
    注意：这是步骤1，只同步到 shopify_orders 表，不会直接同步到核心订单表
    """
    tenant, user = auth

    order_service = ShopifyOrderService(db)

    try:
        result = await order_service.sync_orders_to_shopify_table(
            tenant_id=tenant.id,
            sync_recent_only=sync_recent_only,
            max_orders=max_orders,
        )

        return OrderSyncResponse(**result)

    except Exception as e:
        return OrderSyncResponse(
            success=False,
            error=str(e),
            orders_fetched=0,
            orders_saved=0,
            orders_updated=0,
            errors=[str(e)],
        )


@router.post("/sync/background")
async def sync_orders_background(
    sync_recent_only: bool = True,
    max_orders: Optional[int] = 100,
    background_tasks: BackgroundTasks = None,
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
):
    """
    后台异步同步订单
    """
    tenant, user = auth

    # 启动后台任务
    task = sync_shopify_orders_task.delay(
        tenant_id=tenant.id, sync_recent_only=sync_recent_only, max_orders=max_orders
    )

    return {"message": "订单同步任务已启动", "task_id": task.id, "status": "PENDING"}


@router.post("/sync/full")
async def full_sync_orders(auth: tuple[Tenant, User] = Depends(verify_tenant_auth)):
    """
    完全重新同步所有Shopify订单（不限制数量和时间）
    """
    tenant, user = auth

    # 启动后台任务，完全重新同步
    task = sync_shopify_orders_task.delay(
        tenant_id=tenant.id,
        sync_recent_only=False,  # 完全重新同步
        max_orders=None,  # 不限制数量
    )

    return {
        "message": "完全重新同步任务已启动",
        "task_id": task.id,
        "status": "PENDING",
        "sync_type": "full_resync",
    }


@router.get("/recent", response_model=List[OrderResponse])
async def get_recent_orders(
    hours: int = 24,
    limit: int = 50,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> List[OrderResponse]:
    """
    获取最近的订单
    """
    tenant, user = auth

    order_service = ShopifyOrderService(db)
    orders = await order_service.get_recent_orders(
        tenant_id=tenant.id, hours=hours, limit=limit
    )

    return [OrderResponse.from_orm(order) for order in orders]


@router.get("/status/{status}", response_model=List[OrderResponse])
async def get_orders_by_status(
    status: str,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> List[OrderResponse]:
    """
    根据状态获取订单
    """
    tenant, user = auth

    order_service = ShopifyOrderService(db)
    orders = await order_service.get_orders_by_status(
        tenant_id=tenant.id, status=status, limit=limit
    )

    return [OrderResponse.from_orm(order) for order in orders]


@router.post("/{order_id}/create-shipping-label")
async def create_shipping_label(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
):
    """
    为订单创建发货单 (通过 Printify API)
    """
    tenant, user = auth

    logger.info(f"🚚 开始创建发货单: order_id={order_id}, tenant_id={tenant.id}")

    try:
        # 获取订单详情
        order_service = ShopifyOrderService(db)
        order = await order_service.get_order_by_id(
            order_id=order_id, tenant_id=tenant.id
        )

        if not order:
            logger.error(f"❌ 订单不存在: order_id={order_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="订单不存在")

        logger.info(
            f"✅ 找到订单: {order.id}, external_order_id={order.external_order_id}"
        )

        # 获取 Printify 配置
        from app.services.external_system_service import ExternalSystemService

        external_system_service = ExternalSystemService(db)

        # 查找 Printify 配置
        printify_configs = await external_system_service.get_external_systems_by_type(
            tenant_id=tenant.id, system_type=ExternalSystemType.PRINTIFY
        )

        if not printify_configs:
            logger.error(f"❌ 未找到 Printify 配置: tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="未找到 Printify 配置")

        # 使用第一个 Printify 配置
        printify_config = printify_configs[0]

        logger.info(f"✅ 找到 Printify 配置: {printify_config.id}")

        # 获取解密的 Printify 凭据
        credentials = await external_system_service.get_decrypted_credentials(
            external_system_id=printify_config.id, tenant_id=tenant.id
        )

        if not credentials:
            logger.error(
                f"❌ 无法解密 Printify 凭据: printify_config_id={printify_config.id}"
            )
            raise HTTPException(status_code=400, detail="无法解密 Printify 凭据")

        access_token = credentials.get("access_token")
        shop_id = (printify_config.settings or {}).get("printify_shop_id") or credentials.get("shop_id")
        if shop_id is not None:
            shop_id = str(shop_id).strip() or None

        if not access_token or not shop_id:
            logger.error(
                f"❌ Printify 凭据不完整: access_token={bool(access_token)}, shop_id={shop_id}"
            )
            raise HTTPException(status_code=400, detail="Printify 凭据不完整")

        # 创建 Printify 服务实例
        printify_service = PrintifyService(access_token)

        # 从订单的原始数据中提取 Shopify 订单信息
        shopify_raw_data = order.shopify_raw_data
        if not shopify_raw_data:
            logger.error(f"❌ 订单缺少 Shopify 原始数据: order_id={order_id}")
            raise HTTPException(status_code=400, detail="订单缺少 Shopify 原始数据")

        logger.info(f"📦 开始创建 Printify 订单...")

        # 创建 Printify 订单
        printify_order = (
            await printify_service.create_shipping_label_from_shopify_order(
                shop_id=shop_id, shopify_order=shopify_raw_data
            )
        )

        if not printify_order:
            logger.error(f"❌ 创建 Printify 订单失败: order_id={order_id}")
            raise HTTPException(status_code=500, detail="创建 Printify 订单失败")

        logger.info(f"✅ 成功创建 Printify 订单: {printify_order.get('id')}")

        return {
            "success": True,
            "message": "发货单创建成功",
            "printify_order_id": printify_order.get("id"),
            "external_id": printify_order.get("external_id"),
            "status": printify_order.get("status"),
            "total_price": printify_order.get("total_price"),
            "created_at": printify_order.get("created_at"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 创建发货单时发生错误: {e}")
        raise HTTPException(status_code=500, detail=f"创建发货单失败: {str(e)}")


@router.put("/{order_hashid}")
async def update_order(
    order_hashid: str,
    status: Optional[str] = None,
    fulfillment_status: Optional[str] = None,
    customer_name: Optional[str] = None,
    customer_email: Optional[str] = None,
    customer_phone: Optional[str] = None,
    order_number: Optional[str] = None,
    external_order_id: Optional[str] = None,
    shopify_order_number: Optional[str] = None,
    shopify_order_name: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
):
    """
    更新核心订单
    """
    from app.core.logging import RequestLogger
    from app.core.hashids_utils import decode_id
    from app.models.order import Order
    from sqlalchemy import select, update, and_
    
    logger = RequestLogger("orders.update_order")
    tenant, user = auth

    try:
        # 解码 hashid
        order_id = decode_id(order_hashid)
        logger.info(f"✅ Hashid 解码成功: {order_hashid} -> {order_id}")

        # 查询订单
        query = select(Order).where(
            and_(
                Order.id == order_id,
                Order.tenant_id == tenant.id
            )
        )
        result = await db.execute(query)
        order = result.scalar_one_or_none()

        if not order:
            logger.error(f"❌ 订单不存在: order_id={order_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="Order not found")

        # 准备更新字段
        update_fields = {}
        if status is not None:
            update_fields["status"] = status
        if fulfillment_status is not None:
            update_fields["fulfillment_status"] = fulfillment_status
        if customer_name is not None:
            update_fields["customer_name"] = customer_name
        if customer_email is not None:
            update_fields["customer_email"] = customer_email
        if customer_phone is not None:
            update_fields["customer_phone"] = customer_phone
        if order_number is not None:
            update_fields["order_number"] = order_number
        if external_order_id is not None:
            update_fields["external_order_id"] = external_order_id
        if shopify_order_number is not None:
            update_fields["shopify_order_number"] = shopify_order_number
        if shopify_order_name is not None:
            update_fields["shopify_order_name"] = shopify_order_name

        if not update_fields:
            logger.warning(f"⚠️ 没有字段需要更新: order_id={order_id}")
            return OrderResponse.from_orm(order)

        # 更新订单
        update_query = (
            update(Order)
            .where(
                and_(
                    Order.id == order_id,
                    Order.tenant_id == tenant.id
                )
            )
            .values(**update_fields)
        )
        
        await db.execute(update_query)
        await db.commit()

        # 重新查询更新后的订单
        result = await db.execute(query)
        updated_order = result.scalar_one_or_none()

        logger.info(f"✅ 订单更新成功: order_id={order_id}, updated_fields={list(update_fields.keys())}")
        return OrderResponse.from_orm(updated_order)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ 更新订单失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/{order_hashid}")
async def delete_order(
    order_hashid: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    删除订单
    """
    from app.core.logging import RequestLogger
    from app.core.hashids_utils import decode_id
    from app.models.order import Order
    from sqlalchemy import select, delete, and_
    from sqlalchemy.orm import selectinload

    logger = RequestLogger("orders.delete_order")
    tenant, user = auth

    try:
        logger.info(f"🔍 开始删除订单: order_hashid={order_hashid}, tenant_id={tenant.id}")
        
        # 解码 hashid
        try:
            order_id = decode_id(order_hashid)
            logger.info(f"✅ Hashid 解码成功: {order_hashid} -> {order_id}")
        except Exception as e:
            logger.error(f"❌ Hashid 解码失败: {order_hashid}, 错误: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid order ID")
        
        # 查询订单
        query = select(Order).where(
            and_(
                Order.id == order_id,
                Order.tenant_id == tenant.id
            )
        )
        result = await db.execute(query)
        order = result.scalar_one_or_none()
        
        if not order:
            logger.error(f"❌ 订单不存在: order_id={order_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="Order not found")

        # 禁止删除：已映射到外部订单（如 Shopify）。仅检查映射用 ID；external_system_id 为审计字段，解除映射后仍保留，不参与此判断。
        if order.shopify_order_id or order.external_order_id:
            logger.warning(
                f"⚠️ 订单已映射到外部订单，禁止删除: order_id={order_id}, "
                f"shopify_order_id={order.shopify_order_id}, external_order_id={order.external_order_id}"
            )
            raise HTTPException(
                status_code=400,
                detail="不能删除：该订单已映射到外部订单，请先解除映射后再删除",
            )
        
        # 先删除相关的 scm_order_sources 记录
        from app.models.scm_order import ScmOrderSource, SCMOrder, RoutingStatus
        scm_sources_stmt = delete(ScmOrderSource).where(
            ScmOrderSource.source_order_id == order_id,
            ScmOrderSource.tenant_id == tenant.id
        )
        await db.execute(scm_sources_stmt)
        logger.info(f"✅ 删除相关 SCM 订单源记录: order_id={order_id}")
        
        # 删除相关的 routing_status 记录
        routing_status_stmt = delete(RoutingStatus).where(
            RoutingStatus.order_id == order_id,
            RoutingStatus.tenant_id == tenant.id
        )
        await db.execute(routing_status_stmt)
        logger.info(f"✅ 删除相关路由状态记录: order_id={order_id}")
        
        # 删除相关的 scm_orders 记录（将 source_order_id 设为 NULL）
        scm_orders_stmt = select(SCMOrder).where(
            SCMOrder.source_order_id == order_id,
            SCMOrder.tenant_id == tenant.id
        )
        scm_orders_result = await db.execute(scm_orders_stmt)
        scm_orders = scm_orders_result.scalars().all()
        
        for scm_order in scm_orders:
            scm_order.source_order_id = None
        logger.info(f"✅ 清空相关 SCM 订单的源订单引用: order_id={order_id}, count={len(scm_orders)}")
        
        # 删除订单（级联删除相关数据）
        await db.delete(order)
        await db.commit()
        
        logger.info(f"✅ 订单删除成功: {order.external_order_name or order.external_order_id}")
        
        return {"message": "Order deleted successfully", "success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ 删除订单失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/{order_hashid}/unbind-external", response_model=dict)
async def unbind_order_from_external(
    order_hashid: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
):
    """
    解除订单与外部订单的映射（如 Shopify）。
    解除后可再删除该核心订单。
    """
    from app.core.logging import RequestLogger
    from app.core.hashids_utils import decode_id
    from app.models.order import Order
    from sqlalchemy import select, update, and_

    logger = RequestLogger("orders.unbind_external")
    tenant, user = auth

    try:
        order_id = decode_id(order_hashid)
        result = await db.execute(
            select(Order).where(
                and_(Order.id == order_id, Order.tenant_id == tenant.id)
            )
        )
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if not order.shopify_order_id and not order.external_order_id:
            return {"message": "订单未绑定外部订单", "success": True}
        # 只清除「映射用」的 ID，保留 external_system_id 作为来源审计（来自哪个外部系统）
        await db.execute(
            update(Order)
            .where(and_(Order.id == order_id, Order.tenant_id == tenant.id))
            .values(
                shopify_order_id=None,
                external_order_id=None,
                shopify_fulfillment_order_id=None,
                shopify_fulfillment_id=None,
            )
        )
        await db.commit()
        logger.info(f"✅ 订单已解除外部映射: order_id={order_id}（保留 external_system_id 审计）")
        return {"message": "已解除与外部订单的映射", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ 解除订单外部映射失败: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/batch-update-shopify-status", response_model=dict)
async def batch_update_shopify_status(
    request_data: BatchUpdateShopifyStatusRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> dict:
    """
    批量更新 Shopify 订单状态
    """
    from app.core.logging import RequestLogger
    from app.core.hashids_utils import decode_id
    from app.models.order import Order
    from app.models.external_system import ExternalSystemType
    from sqlalchemy import select, and_
    import httpx
    import asyncio
    
    logger = RequestLogger("orders.batch_update_shopify_status")
    tenant, user = auth

    try:
        order_ids = request_data.order_ids
        if not order_ids:
            raise HTTPException(status_code=400, detail="No order IDs provided")

        logger.info(f"🔍 开始批量更新 Shopify 订单状态: order_count={len(order_ids)}, tenant_id={tenant.id}")

        # 解码订单 ID
        decoded_order_ids = []
        for order_id_hashid in order_ids:
            try:
                order_id = decode_id(order_id_hashid)
                decoded_order_ids.append(order_id)
                logger.info(f"✅ 订单 ID 解码成功: {order_id_hashid} -> {order_id}")
            except Exception as e:
                logger.error(f"❌ 订单 ID 解码失败: {order_id_hashid}, 错误: {str(e)}")
                continue

        if not decoded_order_ids:
            raise HTTPException(status_code=400, detail="No valid order IDs found")

        # 查询订单
        query = select(Order).where(
            and_(
                Order.id.in_(decoded_order_ids),
                Order.tenant_id == tenant.id
            )
        )
        result = await db.execute(query)
        orders = result.scalars().all()

        if not orders:
            raise HTTPException(status_code=404, detail="No orders found")

        logger.info(f"✅ 找到 {len(orders)} 个订单")

        # 获取 Shopify 凭据（与订单页面使用相同的 ExternalSystemService.get_decrypted_credentials）
        from app.services.external_system_service import ExternalSystemService

        service = ExternalSystemService(db)
        # 优先使用第一个订单的 external_system_id（若有多店铺）
        external_system_id = next((o.external_system_id for o in orders if o.external_system_id), None)
        if external_system_id:
            shopify_system = await service.get_external_system(external_system_id, tenant.id)
        else:
            shopify_systems = await service.get_external_systems_by_tenant(
                tenant.id, ExternalSystemType.SHOPIFY, active_only=True
            )
            shopify_system = shopify_systems[0] if shopify_systems else None

        if not shopify_system:
            raise HTTPException(status_code=404, detail="Shopify system not configured")

        decrypted_credentials = await service.get_decrypted_credentials(
            shopify_system.id, tenant.id
        )
        if not decrypted_credentials:
            raise HTTPException(status_code=400, detail="Failed to get decrypted credentials")

        access_token = decrypted_credentials.get("access_token") or decrypted_credentials.get("api_key")
        if not access_token:
            raise HTTPException(status_code=400, detail="Access Token not configured for this store")

        store_url = decrypted_credentials.get("store_url") or shopify_system.base_url or ""
        if store_url:
            shop_domain = store_url.replace("https://", "").replace("http://", "").rstrip("/")
        else:
            sub = shopify_system.external_system_id or ""
            shop_domain = f"{sub}.myshopify.com" if sub and ".myshopify.com" not in sub else sub

        if not shop_domain:
            raise HTTPException(status_code=400, detail="Cannot determine Shopify shop domain")

        logger.info(f"✅ Shopify 配置获取成功（与订单页面相同凭据来源）: shop_domain={shop_domain}")

        # 批量更新订单状态
        success_orders = []
        failed_orders = []

        async with httpx.AsyncClient(timeout=30) as client:
            for order in orders:
                try:
                    # 从订单的 external_order_id 中提取 Shopify 订单 ID
                    shopify_order_id = order.external_order_id
                    if not shopify_order_id:
                        logger.warning(f"⚠️ 订单 {order.id} 缺少 external_order_id")
                        failed_orders.append({
                            'order_id': order.id,
                            'error': 'Missing external_order_id'
                        })
                        continue

                    logger.info(f"🔍 原始 shopify_order_id: {shopify_order_id}")
                    
                    # 确保 shopify_order_id 是正确的格式
                    if not shopify_order_id.startswith('gid://shopify/Order/'):
                        shopify_order_id = f"gid://shopify/Order/{shopify_order_id}"
                        logger.info(f"🔍 添加前缀后的 shopify_order_id: {shopify_order_id}")
                    else:
                        logger.info(f"🔍 已有正确前缀的 shopify_order_id: {shopify_order_id}")

                    # 查询 Shopify 订单详情
                    query = '''
                        query getOrder($id: ID!) {
                            order(id: $id) {
                                id
                                name
                                displayFulfillmentStatus
                                fulfillments {
                                    id
                                    status
                                    trackingInfo {
                                        number
                                        url
                                        company
                                    }
                                    createdAt
                                    updatedAt
                                }
                            }
                        }
                    '''
                    variables = {'id': shopify_order_id}
                    
                    url = f'https://{shop_domain}/admin/api/2024-01/graphql.json'
                    headers = {
                        'X-Shopify-Access-Token': access_token,
                        'Content-Type': 'application/json'
                    }
                    payload = {'query': query, 'variables': variables}

                    logger.info(f"🔍 调用 Shopify API: {url}")
                    logger.info(f"🔍 请求头: {headers}")
                    logger.info(f"🔍 请求体: {payload}")
                    
                    response = await client.post(url, headers=headers, json=payload)
                    
                    logger.info(f"🔍 Shopify API 响应状态: {response.status_code}")
                    logger.info(f"🔍 Shopify API 响应内容: {response.text}")
                    
                    if response.status_code != 200:
                        logger.error(f"❌ Shopify API 请求失败: order_id={order.id}, status={response.status_code}, response={response.text}")
                        failed_orders.append({
                            'order_id': order.id,
                            'error': f'Shopify API error: {response.status_code} - {response.text}'
                        })
                        continue

                    data = response.json()
                    logger.info(f"🔍 解析的响应数据: {data}")
                    
                    if 'errors' in data:
                        logger.error(f"❌ Shopify GraphQL 错误: order_id={order.id}, errors={data['errors']}")
                        failed_orders.append({
                            'order_id': order.id,
                            'error': f"GraphQL errors: {data['errors']}"
                        })
                        continue

                    order_data = data.get('data', {}).get('order')
                    if not order_data:
                        logger.error(f"❌ Shopify 订单不存在: order_id={order.id}, shopify_order_id={shopify_order_id}, response={data}")
                        failed_orders.append({
                            'order_id': order.id,
                            'error': 'Order not found in Shopify'
                        })
                        continue

                    # 更新订单状态和履行信息
                    order.fulfillment_status = order_data.get('displayFulfillmentStatus', order.fulfillment_status)
                    
                    # 更新履行信息
                    fulfillments = order_data.get('fulfillments', [])
                    logger.info(f"🔍 Shopify API 返回的履行信息: {fulfillments}")
                    
                    if fulfillments:
                        # 将履行信息存储到订单的 external_data 中
                        if not order.external_data:
                            order.external_data = {}
                        
                        # 创建新的 external_data 副本
                        updated_external_data = order.external_data.copy()
                        updated_external_data['fulfillments'] = fulfillments
                        logger.info(f"✅ 履行信息已存储到 external_data: {len(fulfillments)} 个履行")
                        
                        # 提取最新的跟踪信息
                        latest_fulfillment = fulfillments[0]  # 取第一个履行信息
                        tracking_info = latest_fulfillment.get('trackingInfo', [])
                        logger.info(f"🔍 跟踪信息: {tracking_info}")
                        
                        if tracking_info and len(tracking_info) > 0:
                            tracking = tracking_info[0]  # 取第一个跟踪信息
                            updated_external_data['tracking_number'] = tracking.get('number')
                            updated_external_data['tracking_url'] = tracking.get('url')
                            updated_external_data['carrier'] = tracking.get('company')
                            logger.info(f"✅ 跟踪信息已存储: {tracking}")
                        
                        # 使用 UPDATE 语句直接更新数据库
                        from sqlalchemy import update
                        update_stmt = update(Order).where(Order.id == order.id).values(
                            external_data=updated_external_data
                        )
                        await db.execute(update_stmt)
                        logger.info(f"✅ 使用 UPDATE 语句更新 external_data 成功")
                    else:
                        logger.warning(f"⚠️ 订单 {order.id} 没有履行信息")

                    await db.commit()
                    await db.refresh(order)

                    success_orders.append({
                        'order_id': order.id,
                        'shopify_order_id': shopify_order_id,
                        'fulfillment_status': order.fulfillment_status
                    })

                    logger.info(f"✅ 订单状态更新成功: order_id={order.id}, fulfillment_status={order.fulfillment_status}")

                except httpx.HTTPStatusError as e:
                    logger.error(f"❌ 调用 Shopify API 失败: order_id={order.id}, status_code={e.response.status_code}, response={e.response.text}")
                    failed_orders.append({
                        'order_id': order.id,
                        'error': f"Shopify API error: {e.response.text}"
                    })
                except httpx.ConnectError as e:
                    logger.error(f"❌ 连接 Shopify API 失败: order_id={order.id}, 错误: {str(e)}")
                    failed_orders.append({
                        'order_id': order.id,
                        'error': f"Network connection error: {str(e)}"
                    })
                except Exception as e:
                    logger.error(f"❌ 批量更新 Shopify 订单状态失败: order_id={order.id}, error={e}", exc_info=True)
                    failed_orders.append({
                        'order_id': order.id,
                        'error': str(e)
                    })

        logger.info(f"✅ 批量更新完成: 成功 {len(success_orders)} 个, 失败 {len(failed_orders)} 个")

        return {
            "success": True,
            "message": f"Batch update completed: {len(success_orders)} successful, {len(failed_orders)} failed",
            "results": {
                "success": success_orders,
                "failed": failed_orders
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 批量更新 Shopify 订单状态失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
