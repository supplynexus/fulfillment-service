"""
订单自动化任务
用于自动化处理订单流程
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from celery import Celery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_async_db
from app.core.logging import get_logger
from app.models.order import Order
from app.models.scm_order import SCMOrder
from app.services.order_routing_service import OrderRoutingService
from app.services.order_status_sync_service import OrderStatusSyncService
from app.services.printify_service import PrintifyService
from app.core.security import decrypt_data

logger = get_logger(__name__)

# 获取Celery应用实例
from app.tasks.celery_app import celery_app


@celery_app.task(bind=True)
async def process_new_shopify_orders(self, tenant_id: int, limit: int = 50):
    """
    处理新的Shopify订单
    自动创建SCM订单并调用Printify API
    """
    try:
        logger.info("🔍 开始处理新的Shopify订单", tenant_id=tenant_id, limit=limit)

        # 使用同步数据库会话
        from app.core.database import get_sync_db

        db = next(get_sync_db())

        # 获取未处理的Shopify订单
        orders = (
            db.query(Order)
            .filter(
                and_(
                    Order.tenant_id == tenant_id,
                    Order.external_system_id == 1,  # Shopify系统ID
                    Order.shopify_order_id.isnot(None),
                    ~Order.id.in_(
                        db.query(SCMOrder.source_order_id).filter(
                            SCMOrder.source_order_id.isnot(None)
                        )
                    ),
                )
            )
            .limit(limit)
            .all()
        )

        if not orders:
            logger.info("ℹ️ 没有新的Shopify订单需要处理", tenant_id=tenant_id)
            return {
                "success": True,
                "message": "没有新的订单需要处理",
                "processed_count": 0,
            }

        processed_count = 0
        errors = []

        for order in orders:
            try:
                # 创建订单路由服务
                routing_service = OrderRoutingService(db)

                # 执行订单路由 - 需要先获取路由配置
                from app.models.routing_rule import RoutingRule
                from app.schemas.routing import OrderRoutingConfig

                # 获取默认路由配置
                routing_config = OrderRoutingConfig(
                    routing_strategy="auto",
                    target_systems=["PRINTIFY"],
                    priority_rules=[],
                )

                # 路由订单到SCM
                scm_orders = await routing_service.route_order_to_scm(
                    order, routing_config, tenant_id
                )

                if scm_orders:
                    # 为每个SCM订单创建Printify订单
                    for scm_order in scm_orders:
                        if scm_order.target_system_type == "PRINTIFY":
                            await _create_printify_order_for_scm(
                                db, scm_order, tenant_id
                            )

                    processed_count += 1
                    logger.info(
                        f"✅ 订单 {order.id} 处理成功",
                        order_number=order.order_number,
                        scm_orders_count=len(scm_orders),
                    )
                else:
                    error_msg = f"订单 {order.id} 路由失败: 未生成SCM订单"
                    errors.append(error_msg)
                    logger.error(f"❌ {error_msg}")

            except Exception as e:
                error_msg = f"订单 {order.id} 处理异常: {str(e)}"
                errors.append(error_msg)
                logger.error(f"❌ {error_msg}")

        result = {
            "success": len(errors) == 0,
            "processed_count": processed_count,
            "total_orders": len(orders),
            "errors": errors,
        }

        logger.info(
            "✅ Shopify订单处理完成",
            tenant_id=tenant_id,
            processed_count=processed_count,
            total_orders=len(orders),
            error_count=len(errors),
        )

        return result

    except Exception as e:
        logger.error("❌ 处理Shopify订单失败", tenant_id=tenant_id, error=str(e))
        if self:
            self.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True)
async def sync_printify_orders_status(self, tenant_id: int, limit: int = 100):
    """
    同步Printify订单状态到SCM
    """
    try:
        logger.info("🔍 开始同步Printify订单状态", tenant_id=tenant_id, limit=limit)

        # 使用同步数据库会话
        from app.core.database import get_sync_db

        db = next(get_sync_db())

        # 获取有Printify订单ID的SCM订单
        scm_orders = (
            db.query(SCMOrder)
            .filter(
                and_(
                    SCMOrder.tenant_id == tenant_id,
                    SCMOrder.target_system_type == "PRINTIFY",
                    SCMOrder.printify_order_id.isnot(None),
                    SCMOrder.status.in_(["created", "processing"]),
                )
            )
            .limit(limit)
            .all()
        )

        if not scm_orders:
            logger.info("ℹ️ 没有需要同步的Printify订单", tenant_id=tenant_id)
            return {"success": True, "message": "没有需要同步的订单", "synced_count": 0}

        synced_count = 0
        errors = []

        for scm_order in scm_orders:
            try:
                # 创建状态同步服务
                sync_service = OrderStatusSyncService(db)

                # 同步Printify状态到SCM
                success = await sync_service.sync_printify_to_scm(
                    scm_order.printify_order_id, tenant_id
                )

                if success:
                    synced_count += 1
                    logger.info(f"✅ SCM订单 {scm_order.id} 状态同步成功")
                else:
                    error_msg = f"SCM订单 {scm_order.id} 状态同步失败"
                    errors.append(error_msg)
                    logger.error(f"❌ {error_msg}")

            except Exception as e:
                error_msg = f"SCM订单 {scm_order.id} 状态同步异常: {str(e)}"
                errors.append(error_msg)
                logger.error(f"❌ {error_msg}")

        result = {
            "success": len(errors) == 0,
            "synced_count": synced_count,
            "total_orders": len(scm_orders),
            "errors": errors,
        }

        logger.info(
            "✅ Printify订单状态同步完成",
            tenant_id=tenant_id,
            synced_count=synced_count,
            total_orders=len(scm_orders),
            error_count=len(errors),
        )

        return result

    except Exception as e:
        logger.error("❌ 同步Printify订单状态失败", tenant_id=tenant_id, error=str(e))
        if self:
            self.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True)
async def sync_scm_to_shopify_fulfillment(self, tenant_id: int, limit: int = 100):
    """
    同步SCM订单状态到Shopify履约
    """
    try:
        logger.info("🔍 开始同步SCM订单到Shopify履约", tenant_id=tenant_id, limit=limit)

        # 使用同步数据库会话
        from app.core.database import get_sync_db

        db = next(get_sync_db())

        # 创建状态同步服务
        sync_service = OrderStatusSyncService(db)

        # 批量同步待处理的订单
        result = await sync_service.batch_sync_pending_orders(tenant_id, limit)

        logger.info(
            "✅ SCM订单到Shopify履约同步完成", tenant_id=tenant_id, result=result
        )

        return result

    except Exception as e:
        logger.error(
            "❌ 同步SCM订单到Shopify履约失败", tenant_id=tenant_id, error=str(e)
        )
        if self:
            self.update_state(state="FAILURE", meta={"error": str(e)})
        raise


async def _create_printify_order_for_scm(db, scm_order: SCMOrder, tenant_id: int):
    """为SCM订单创建Printify订单"""
    try:
        logger.info(
            "🔍 开始为SCM订单创建Printify订单",
            scm_order_id=scm_order.id,
            tenant_id=tenant_id,
        )

        # 获取Printify凭据
        from app.services.external_system_service import ExternalSystemService

        service = ExternalSystemService(db)
        printify_systems = await service.get_external_systems_by_type(
            tenant_id, "PRINTIFY"
        )

        if not printify_systems:
            logger.error("❌ 未找到Printify外部系统", tenant_id=tenant_id)
            return False

        printify_system = printify_systems[0]
        credentials = printify_system.get("credentials", {})

        # 解密凭据
        access_token = decrypt_data(credentials.get("access_token", ""))
        shop_id = credentials.get("shop_id", "")

        if not access_token or not shop_id:
            logger.error("❌ Printify凭据不完整", tenant_id=tenant_id)
            return False

        # 创建Printify服务
        printify_service = PrintifyService(db)

        # 构建Printify订单数据
        # 使用Shopify订单ID作为external_id，这样Printify订单就能关联回Shopify
        shopify_order_id = None
        if scm_order.source_order_id:
            # 从源订单获取Shopify订单ID
            from app.models.order import Order

            source_order = (
                db.query(Order).filter(Order.id == scm_order.source_order_id).first()
            )
            if source_order:
                shopify_order_id = source_order.shopify_order_id
        elif scm_order.shopify_order_id:
            # 直接从SCM订单获取Shopify订单ID
            shopify_order_id = scm_order.shopify_order_id

        order_data = {
            "external_id": shopify_order_id or f"SCM-{scm_order.scm_order_number}",
            "line_items": scm_order.line_items,
            "shipping_method": 1,
            "send_shipping_notification": True,
            "status": "pending",
            "address_to": {
                "first_name": (
                    scm_order.customer_name.split(" ")[0]
                    if scm_order.customer_name
                    else "Customer"
                ),
                "last_name": (
                    " ".join(scm_order.customer_name.split(" ")[1:])
                    if scm_order.customer_name
                    and len(scm_order.customer_name.split(" ")) > 1
                    else ""
                ),
                "email": scm_order.customer_email,
                "phone": scm_order.customer_phone or "",
                "country": scm_order.shipping_address.get("country", "US"),
                "region": scm_order.shipping_address.get("province", ""),
                "city": scm_order.shipping_address.get("city", ""),
                "address1": scm_order.shipping_address.get("address1", ""),
                "address2": scm_order.shipping_address.get("address2", ""),
                "zip": scm_order.shipping_address.get("zip", ""),
            },
        }

        # 调用Printify API创建订单
        printify_result = await printify_service.create_order(
            shop_id, order_data, access_token
        )

        if printify_result.get("success"):
            printify_order_id = printify_result.get("order_id")

            # 更新SCM订单的Printify信息
            routing_service = OrderRoutingService(db)
            await routing_service.update_scm_order_with_printify_info(
                scm_order.id, printify_order_id, shop_id, tenant_id
            )

            logger.info(
                "✅ Printify订单创建成功",
                scm_order_id=scm_order.id,
                printify_order_id=printify_order_id,
            )

            return True
        else:
            logger.error(
                "❌ Printify订单创建失败",
                scm_order_id=scm_order.id,
                error=printify_result.get("error"),
            )
            return False

    except Exception as e:
        logger.error(
            "❌ 为SCM订单创建Printify订单失败", scm_order_id=scm_order.id, error=str(e)
        )
        return False


# 定时任务配置
@celery_app.task
def scheduled_process_shopify_orders():
    """定时处理Shopify订单任务"""
    # 获取所有租户
    from app.core.database import get_sync_db

    db = next(get_sync_db())

    from app.models.tenant import Tenant

    tenants = db.query(Tenant).all()

    for tenant in tenants:
        try:
            # 异步处理每个租户的订单
            process_new_shopify_orders.delay(tenant.id, 50)
        except Exception as e:
            logger.error(f"❌ 启动租户 {tenant.id} 订单处理任务失败", error=str(e))


@celery_app.task
def scheduled_sync_printify_status():
    """定时同步Printify状态任务"""
    from app.core.database import get_sync_db

    db = next(get_sync_db())

    from app.models.tenant import Tenant

    tenants = db.query(Tenant).all()

    for tenant in tenants:
        try:
            sync_printify_orders_status.delay(tenant.id, 100)
        except Exception as e:
            logger.error(
                f"❌ 启动租户 {tenant.id} Printify状态同步任务失败", error=str(e)
            )


@celery_app.task
def scheduled_sync_shopify_fulfillment():
    """定时同步Shopify履约任务"""
    from app.core.database import get_sync_db

    db = next(get_sync_db())

    from app.models.tenant import Tenant

    tenants = db.query(Tenant).all()

    for tenant in tenants:
        try:
            sync_scm_to_shopify_fulfillment.delay(tenant.id, 100)
        except Exception as e:
            logger.error(
                f"❌ 启动租户 {tenant.id} Shopify履约同步任务失败", error=str(e)
            )
