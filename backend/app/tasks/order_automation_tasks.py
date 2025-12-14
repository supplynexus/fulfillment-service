"""
订单自动化任务
用于自动化处理订单流程
"""

import asyncio
from app.core.logging import get_logger
from app.models.order import Order
from app.models.scm_order import SCMOrder, ScmOrderSource
from app.services.order_routing_service import OrderRoutingService
from app.services.printify_service import PrintifyService
from app.core.security import decrypt_data
from app.tasks.celery_app import celery_app
from sqlalchemy import and_, select

logger = get_logger(__name__)


@celery_app.task(bind=True)
def sync_printify_orders_status(self, tenant_id: int, limit: int = 100):
    """
    同步Printify订单状态到SCM (批量优化版本)
    """
    try:
        logger.info("🔍 开始批量同步Printify订单状态", tenant_id=tenant_id, limit=limit)

        # 使用同步数据库会话
        from app.core.database import get_sync_db
        from app.services.order_status_sync_service import OrderStatusSyncService

        db = next(get_sync_db())

        # 创建状态同步服务
        sync_service = OrderStatusSyncService(db)

        # 使用批量同步方法
        result = sync_service.batch_sync_printify_to_scm_sync(tenant_id, limit)

        logger.info(
            "✅ Printify订单状态批量同步完成",
            tenant_id=tenant_id,
            result=result,
        )

        return result

    except Exception as e:
        import traceback
        error_type = type(e).__name__
        error_message = str(e)
        error_traceback = traceback.format_exc()
        
        logger.error(
            "❌ 批量同步Printify订单状态失败", tenant_id=tenant_id, error=error_message
        )
        logger.error(f"异常类型: {error_type}")
        logger.error(f"异常堆栈:\n{error_traceback}")
        
        if self:
            self.update_state(
                state="FAILURE", 
                meta={
                    "error": error_message,
                    "error_type": error_type,
                    "traceback": error_traceback
                }
            )
        
        # 重新抛出异常，确保 Celery 可以正确处理
        raise RuntimeError(f"{error_type}: {error_message}") from e


@celery_app.task(bind=True)
def sync_scm_to_shopify_fulfillment(self, tenant_id: int, limit: int = 100):
    """
    同步SCM订单状态到Shopify履约
    """
    try:
        logger.info("🔍 开始同步SCM订单到Shopify履约", tenant_id=tenant_id, limit=limit)

        # 使用同步数据库会话
        from app.core.database import get_sync_db
        from app.services.order_status_sync_service import OrderStatusSyncService

        db = next(get_sync_db())

        # 创建状态同步服务
        sync_service = OrderStatusSyncService(db)

        # 批量同步待处理的订单
        result = sync_service.batch_sync_pending_orders_sync(tenant_id, limit)

        logger.info(
            "✅ SCM订单到Shopify履约同步完成",
            tenant_id=tenant_id,
            result=result,
        )

        return result

    except Exception as e:
        import traceback
        error_type = type(e).__name__
        error_message = str(e)
        error_traceback = traceback.format_exc()
        
        logger.error(
            "❌ 同步SCM订单到Shopify履约失败", tenant_id=tenant_id, error=error_message
        )
        logger.error(f"异常类型: {error_type}")
        logger.error(f"异常堆栈:\n{error_traceback}")
        
        if self:
            self.update_state(
                state="FAILURE", 
                meta={
                    "error": error_message,
                    "error_type": error_type,
                    "traceback": error_traceback
                }
            )
        
        # 重新抛出异常，确保 Celery 可以正确处理
        raise RuntimeError(f"{error_type}: {error_message}") from e


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

            result = await db.execute(
                select(Order).where(Order.id == scm_order.source_order_id)
            )
            source_order = result.scalar_one_or_none()
            if source_order:
                shopify_order_id = source_order.shopify_order_id
        elif scm_order.shopify_order_id:
            # 直接从SCM订单获取Shopify订单ID
            shopify_order_id = scm_order.shopify_order_id

        order_data = {
            "external_id": (shopify_order_id or f"SCM-{scm_order.scm_order_number}"),
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


@celery_app.task(bind=True)
def process_new_orders_to_scm(self, tenant_id: int, limit: int = 50):
    """
    处理新的核心订单，自动路由到SCM系统
    这是一个通用任务，适用于所有来源的订单（Shopify、Amazon、Printify等）
    不限制订单来源，只查询还没有创建SCM订单的核心订单
    """
    try:
        logger.info("🔍 开始处理新的核心订单，路由到SCM系统", tenant_id=tenant_id, limit=limit)

        async def _process_orders():
            from app.core.database import AsyncSessionLocal

            async with AsyncSessionLocal() as db:
                from sqlalchemy.orm import selectinload
                
                # 获取所有未处理的订单（不限制来源），并加载 items 关系
                # 只查询还没有创建SCM订单的核心订单
                # 检查 ScmOrderSource 表（实际关联表）和 SCMOrder.source_order_id（兼容旧数据）
                result = await db.execute(
                    select(Order)
                    .options(selectinload(Order.items))  # 加载订单项
                    .filter(
                        and_(
                            Order.tenant_id == tenant_id,
                            # 只处理还没有创建SCM订单的订单
                            # 检查 ScmOrderSource 表（主要关联表）
                            ~Order.id.in_(
                                select(ScmOrderSource.source_order_id).where(
                                    ScmOrderSource.tenant_id == tenant_id
                                )
                            ),
                            # 同时检查 SCMOrder.source_order_id（兼容旧数据）
                            ~Order.id.in_(
                                select(SCMOrder.source_order_id).where(
                                    and_(
                                        SCMOrder.source_order_id.isnot(None),
                                        SCMOrder.tenant_id == tenant_id
                                    )
                                )
                            ),
                        )
                    )
                    .limit(limit)
                )
                orders = result.scalars().all()

                if not orders:
                    logger.info("ℹ️ 没有新的核心订单需要路由到SCM系统", tenant_id=tenant_id)
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
                        from app.schemas.scm_order import OrderRoutingConfig

                        # 获取默认路由配置（自动路由）
                        routing_config = OrderRoutingConfig(
                            routing_strategy="auto",
                            target_systems=[],  # 空列表表示使用自动路由规则
                            routing_rules={},
                            custom_metadata={},
                        )

                        # 路由订单到SCM
                        scm_orders = await routing_service.route_order_to_scm(
                            order, routing_config, tenant_id
                        )

                        if scm_orders:
                            # 为每个SCM订单创建对应的外部系统订单
                            for scm_order in scm_orders:
                                if scm_order.target_system_type == "PRINTIFY":
                                    await _create_printify_order_for_scm(
                                        db, scm_order, tenant_id
                                    )
                                # 可以在这里添加其他外部系统的处理逻辑
                                # elif scm_order.target_system_type == "AMAZON":
                                #     await _create_amazon_order_for_scm(...)

                            processed_count += 1
                            logger.info(
                                f"✅ 订单 {order.id} 路由成功",
                                order_number=order.order_number,
                                scm_orders_count=len(scm_orders),
                            )
                        else:
                            error_msg = f"订单 {order.id} 路由失败: 未生成SCM订单"
                            errors.append(error_msg)
                            logger.warning(f"⚠️ {error_msg}")

                    except Exception as e:
                        error_msg = f"订单 {order.id} 处理异常: {str(e)}"
                        errors.append(error_msg)
                        logger.error(f"❌ {error_msg}")
                        import traceback
                        logger.error(f"   异常堆栈: {traceback.format_exc()}")

                result = {
                    "success": len(errors) == 0,
                    "processed_count": processed_count,
                    "total_orders": len(orders),
                    "errors": errors,
                }

                logger.info(
                    "✅ 核心订单路由到SCM系统完成",
                    tenant_id=tenant_id,
                    processed_count=processed_count,
                    total_orders=len(orders),
                    error_count=len(errors),
                )

                return result

        # 使用线程隔离运行异步函数，避免事件循环冲突
        import threading
        import asyncio
        
        result_container = {}
        exception_container = {}
        
        def run_in_thread():
            """在独立线程中运行异步代码，使用新的事件循环"""
            try:
                # 创建新的事件循环
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(_process_orders())
                    result_container['result'] = result
                finally:
                    # 在关闭事件循环之前，确保所有数据库连接都被正确关闭
                    try:
                        # 等待所有未完成的任务完成
                        pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
                        if pending:
                            # 取消所有未完成的任务
                            for task in pending:
                                task.cancel()
                            # 等待所有任务完成（包括被取消的任务）
                            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    except Exception:
                        pass  # 忽略清理过程中的错误
                    
                    # 关闭数据库引擎的连接池（确保所有连接都被关闭）
                    try:
                        from app.core.database import async_engine
                        # 在事件循环中关闭引擎
                        if not loop.is_closed():
                            loop.run_until_complete(async_engine.dispose(close=True))
                    except Exception:
                        pass  # 忽略清理过程中的错误
                    
                    # 最后关闭事件循环
                    try:
                        if not loop.is_closed():
                            loop.close()
                    except Exception:
                        pass
            except Exception as e:
                import traceback
                exception_container['error'] = e
                exception_container['error_type'] = type(e).__name__
                exception_container['error_message'] = str(e)
                exception_container['error_traceback'] = traceback.format_exc()
        
        # 在独立线程中运行
        thread = threading.Thread(target=run_in_thread, daemon=False)
        thread.start()
        thread.join()
        
        # 检查是否有异常
        if 'error' in exception_container:
            error = exception_container['error']
            raise error
        
        # 返回结果
        return result_container.get('result', {"success": False, "message": "未返回结果"})

    except Exception as e:
        import traceback
        error_type = type(e).__name__
        error_message = str(e)
        error_traceback = traceback.format_exc()
        
        logger.error("❌ 处理核心订单路由到SCM系统失败", tenant_id=tenant_id, error=error_message)
        logger.error(f"异常类型: {error_type}")
        logger.error(f"异常堆栈:\n{error_traceback}")
        
        if self:
            self.update_state(
                state="FAILURE", 
                meta={
                    "error": error_message,
                    "error_type": error_type,
                    "traceback": error_traceback
                }
            )
        
        # 重新抛出异常，确保 Celery 可以正确处理
        raise RuntimeError(f"{error_type}: {error_message}") from e


# 定时任务配置
@celery_app.task
def scheduled_process_orders_to_scm():
    """定时处理核心订单，路由到SCM系统（通用任务）"""
    # 获取所有租户
    from app.core.database import get_sync_db

    db = next(get_sync_db())

    from app.models.tenant import Tenant

    tenants = db.query(Tenant).all()

    for tenant in tenants:
        try:
            # 异步处理每个租户的订单（通用任务，不限制订单来源）
            process_new_orders_to_scm.delay(tenant.id, 50)
        except Exception as e:
            logger.error(f"❌ 启动租户 {tenant.id} 核心订单路由任务失败", error=str(e))


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


@celery_app.task(bind=True)
def sync_shopify_orders_to_core(self, tenant_id: int, limit: int = 50):
    """
    自动将Shopify订单同步到核心订单表
    对应步骤: sync_to_core_orders
    
    Args:
        tenant_id: 租户ID
        limit: 每次处理的订单数量限制
    """
    from app.core.database import get_sync_db
    from app.models.shopify_order import ShopifyOrder
    from app.models.order import Order
    from app.models.tenant import Tenant
    from app.services.shopify_order_sync_service import sync_shopify_order_to_core_sync
    from sqlalchemy import and_, not_

    try:
        logger.info("🔍 开始同步Shopify订单到核心订单表", tenant_id=tenant_id, limit=limit)

        db = next(get_sync_db())
        
        # 获取租户
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            logger.error(f"❌ 租户不存在: tenant_id={tenant_id}")
            return {
                "success": False,
                "message": f"租户不存在: {tenant_id}",
                "processed_count": 0,
            }

        # 查询未同步的Shopify订单
        # 查找shopify_orders表中，shopify_order_id不在orders表的external_order_id中的订单
        synced_external_order_ids = [
            row[0] for row in db.query(Order.external_order_id).filter(
                and_(
                    Order.tenant_id == tenant_id,
                    Order.external_order_id.isnot(None)
                )
            ).all()
        ]
        
        unsynced_shopify_orders = db.query(ShopifyOrder).filter(
            and_(
                ShopifyOrder.tenant_id == tenant_id,
                ~ShopifyOrder.shopify_order_id.in_(synced_external_order_ids) if synced_external_order_ids else True
            )
        ).limit(limit).all()

        if not unsynced_shopify_orders:
            logger.info("ℹ️ 没有未同步的Shopify订单", tenant_id=tenant_id)
            return {
                "success": True,
                "message": "没有未同步的订单需要处理",
                "processed_count": 0,
            }

        processed_count = 0
        errors = []

        for shopify_order in unsynced_shopify_orders:
            try:
                result = sync_shopify_order_to_core_sync(db, shopify_order, tenant)
                if result.get("success"):
                    processed_count += 1
                    logger.info(
                        f"✅ Shopify订单同步成功: {shopify_order.name} -> core_order_id={result.get('core_order_id')}"
                    )
                else:
                    error_msg = f"订单 {shopify_order.name} 同步失败: {result.get('message')}"
                    errors.append(error_msg)
                    logger.error(f"❌ {error_msg}")
            except Exception as e:
                error_msg = f"订单 {shopify_order.name} 同步异常: {str(e)}"
                errors.append(error_msg)
                logger.error(f"❌ {error_msg}")
                import traceback
                logger.error(f"   异常堆栈: {traceback.format_exc()}")

        logger.info(
            f"✅ Shopify订单同步完成: 成功={processed_count}, 失败={len(errors)}, tenant_id={tenant_id}"
        )

        return {
            "success": True,
            "message": f"处理完成: 成功 {processed_count} 个，失败 {len(errors)} 个",
            "processed_count": processed_count,
            "error_count": len(errors),
            "errors": errors[:10] if errors else [],  # 只返回前10个错误
        }

    except Exception as e:
        logger.error(f"❌ 同步Shopify订单到核心订单表失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        return {
            "success": False,
            "message": f"同步失败: {str(e)}",
            "processed_count": 0,
        }
    finally:
        db.close()


@celery_app.task
def scheduled_sync_shopify_to_core():
    """定时同步Shopify订单到核心订单表任务"""
    from app.core.database import get_sync_db
    from app.models.tenant import Tenant

    db = next(get_sync_db())

    tenants = db.query(Tenant).all()

    for tenant in tenants:
        try:
            # 检查租户是否启用了此步骤的自动化
            from app.models.tenant_automation_config import TenantAutomationConfig
            config = db.query(TenantAutomationConfig).filter(
                and_(
                    TenantAutomationConfig.tenant_id == tenant.id,
                    TenantAutomationConfig.step_key == "sync_to_core_orders",
                    TenantAutomationConfig.is_enabled == True,
                    TenantAutomationConfig.is_active == True
                )
            ).first()
            
            if config:
                sync_shopify_orders_to_core.delay(tenant.id, 50)
                logger.info(f"✅ 启动租户 {tenant.id} Shopify订单同步到核心订单任务")
            else:
                logger.info(f"ℹ️ 租户 {tenant.id} 未启用sync_to_core_orders自动化，跳过")
        except Exception as e:
            logger.error(
                f"❌ 启动租户 {tenant.id} Shopify订单同步到核心订单任务失败", error=str(e)
            )
