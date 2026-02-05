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
def sync_printify_orders_status(self, tenant_id: int, limit: int = 100, ignore_flags: bool = False):
    """
    从printify_orders本地表同步发货信息到SCM订单
    对应步骤: sync_fulfillment_status
    
    注意：此任务已改为从本地表读取，不再直接从API读取
    实际的API同步由 sync_printify_orders_to_local 任务完成
    
    Args:
        tenant_id: 租户ID
        limit: 每次处理的订单数量限制
        ignore_flags: 是否忽略处理标志（手动处理时使用）
    """
    try:
        logger.info("🔍 开始从Printify本地表同步发货信息到SCM订单", tenant_id=tenant_id, limit=limit)

        # 使用同步数据库会话
        from app.core.database import get_sync_db
        from app.models.printify_order import PrintifyOrder
        from app.models.scm_order import SCMOrder
        from datetime import datetime

        db = next(get_sync_db())

        # 查询有发货信息且关联了SCM订单的Printify订单
        # 如果 ignore_flags=False，且 auto_synced_fulfillment_to_scm=False（避免重复处理）
        filter_conditions = [
            PrintifyOrder.tenant_id == tenant_id,
            PrintifyOrder.scm_order_id.isnot(None),
            PrintifyOrder.tracking_number.isnot(None),  # 有跟踪号才需要同步
        ]
        if not ignore_flags:
            filter_conditions.append(PrintifyOrder.auto_synced_fulfillment_to_scm == False)
        
        printify_orders = db.query(PrintifyOrder).filter(
            and_(*filter_conditions)
        ).limit(limit).all()

        if not printify_orders:
            logger.info("ℹ️ 没有需要同步的Printify订单", tenant_id=tenant_id)
            return {
                "success": True,
                "message": "没有需要同步的订单",
                "synced_count": 0,
            }

        synced_count = 0
        errors = []

        for printify_order in printify_orders:
            try:
                scm_order = printify_order.scm_order
                if not scm_order:
                    continue

                needs_update = False

                # 检查跟踪号
                if printify_order.tracking_number and scm_order.tracking_number != printify_order.tracking_number:
                    scm_order.tracking_number = printify_order.tracking_number
                    needs_update = True

                # 检查跟踪链接
                if printify_order.tracking_url and scm_order.tracking_url != printify_order.tracking_url:
                    scm_order.tracking_url = printify_order.tracking_url
                    needs_update = True

                # 检查承运商
                if printify_order.carrier and scm_order.carrier != printify_order.carrier:
                    scm_order.carrier = printify_order.carrier
                    needs_update = True

                # 检查发货时间
                if printify_order.shipped_at and (not scm_order.shipped_at or scm_order.shipped_at != printify_order.shipped_at):
                    scm_order.shipped_at = printify_order.shipped_at
                    needs_update = True

                # 检查送达时间
                if printify_order.delivered_at and (not scm_order.delivered_at or scm_order.delivered_at != printify_order.delivered_at):
                    scm_order.delivered_at = printify_order.delivered_at
                    needs_update = True

                # 更新订单状态
                if printify_order.status == 'shipped' and scm_order.fulfillment_status != 'shipped':
                    scm_order.fulfillment_status = 'shipped'
                    needs_update = True
                elif printify_order.status == 'delivered' and scm_order.fulfillment_status != 'delivered':
                    scm_order.fulfillment_status = 'delivered'
                    needs_update = True

                if needs_update:
                    scm_order.updated_at = datetime.now()
                    # 标记Printify订单为已自动同步发货信息到SCM
                    printify_order.auto_synced_fulfillment_to_scm = True
                    # 标记SCM订单为已自动同步发货信息从Printify
                    scm_order.auto_synced_fulfillment_from_printify = True
                    db.commit()
                    synced_count += 1
                    logger.info(f"✅ 同步发货信息成功: Printify订单 {printify_order.id} -> SCM订单 {scm_order.id}")

            except Exception as e:
                db.rollback()
                error_msg = f"同步订单 {printify_order.id} 失败: {str(e)}"
                errors.append(error_msg)
                logger.error(f"❌ {error_msg}")

        return {
            "success": True,
            "synced_count": synced_count,
            "total_orders": len(printify_orders),
            "errors": errors,
        }

    except Exception as e:
        import traceback
        error_type = type(e).__name__
        error_message = str(e)
        error_traceback = traceback.format_exc()
        
        logger.error(
            "❌ 从Printify本地表同步发货信息到SCM订单失败", tenant_id=tenant_id, error=error_message
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
def sync_scm_to_shopify_fulfillment(self, tenant_id: int, limit: int = 100, ignore_flags: bool = False):
    """
    同步SCM订单状态到Shopify履约
    
    Args:
        tenant_id: 租户ID
        limit: 每次处理的订单数量限制
        ignore_flags: 是否忽略处理标志（手动处理时使用）
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
        result = sync_service.batch_sync_pending_orders_sync(tenant_id, limit, ignore_flags)

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
    """为SCM订单创建Printify订单（与手动流程保持一致）"""
    try:
        logger.info(
            "🔍 开始为SCM订单创建Printify订单",
            scm_order_id=scm_order.id,
            tenant_id=tenant_id,
        )

        # 获取租户对象
        from app.models.tenant import Tenant
        tenant_result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = tenant_result.scalar_one_or_none()
        
        if not tenant:
            logger.error("❌ 未找到租户", tenant_id=tenant_id)
            return False

        # 检查是否已经存在 Printify 订单（避免重复创建）
        from app.models.printify_order import PrintifyOrder
        existing_printify_order_result = await db.execute(
            select(PrintifyOrder).where(
                and_(
                    PrintifyOrder.scm_order_id == scm_order.id,
                    PrintifyOrder.tenant_id == tenant_id
                )
            )
        )
        existing_printify_order = existing_printify_order_result.scalar_one_or_none()
        
        if existing_printify_order:
            logger.info(
                f"ℹ️ SCM订单 {scm_order.id} 已经存在 Printify 订单: external_order_id={existing_printify_order.external_order_id}"
            )
            # 更新 SCM 订单的 Printify 信息
            from datetime import datetime
            if not scm_order.routing_metadata:
                scm_order.routing_metadata = {}
            scm_order.routing_metadata['printify_order_id'] = existing_printify_order.external_order_id
            scm_order.routing_metadata['printify_status'] = existing_printify_order.status
            scm_order.printify_order_id = existing_printify_order.external_order_id
            
            # 获取 Printify 外部系统以获取 shop_id
            from app.models.external_system import ExternalSystem, ExternalSystemType
            external_system_result = await db.execute(
                select(ExternalSystem).where(
                    and_(
                        ExternalSystem.tenant_id == tenant_id,
                        ExternalSystem.system_type == ExternalSystemType.PRINTIFY
                    )
                )
            )
            external_system = external_system_result.scalar_one_or_none()
            if external_system:
                scm_order.printify_shop_id = external_system.external_system_id
            
            logger.info(
                "✅ 使用已存在的 Printify 订单",
                scm_order_id=scm_order.id,
                printify_order_id=existing_printify_order.external_order_id,
            )
            return True
        
        # 使用 PrintifyFulfillmentService（与手动 generate-printify 流程保持一致）
        from app.services.printify_fulfillment_service import PrintifyFulfillmentService
        from types import SimpleNamespace

        fulfillment_service = PrintifyFulfillmentService()

        # 预增强 line_items：通过 core_variant_id 或 SKU 查找 Printify 映射；无时通过 source_order_id + source_line_item_id 从 OrderItem 解析（与手动创建逻辑一致）
        enriched_line_items = await fulfillment_service.enrich_line_items_with_printify_mapping(
            scm_order.line_items or [],
            db,
            tenant_id,
            source_order_id=getattr(scm_order, "source_order_id", None),
        )
        # 与手动 generate-printify 流程一致：传递 _build_fulfillment_data 所需的全部字段
        scm_order_for_fulfillment = SimpleNamespace(
            id=scm_order.id,
            tenant_id=scm_order.tenant_id,
            scm_order_number=scm_order.scm_order_number,
            line_items=enriched_line_items,
            shipping_address=scm_order.shipping_address,
            customer_email=scm_order.customer_email,
            customer_name=getattr(scm_order, "customer_name", None),
            customer_phone=getattr(scm_order, "customer_phone", None),
        )

        # 调用 create_fulfillment_order 方法（与手动流程完全一致）
        try:
            printify_result = await fulfillment_service.create_fulfillment_order(
                scm_order=scm_order_for_fulfillment,
                tenant=tenant,
                db=db
            )
        except Exception as e:
            error_str = str(e)
            # 检查是否是订单已存在的错误
            if "already exists" in error_str.lower() or "unique_id" in error_str.lower():
                logger.warning(
                    f"⚠️ Printify 订单已存在（可能在 Printify 中但未同步到本地数据库），尝试查找: scm_order_id={scm_order.id}"
                )
                # 尝试通过 external_id 查找（external_id 格式是 scm_{scm_order.id}）
                external_id = f"scm_{scm_order.id}"
                # 由于我们无法直接查询 Printify API，这里只能记录日志
                # 实际应该通过 Printify API 查询订单，但为了简化，我们直接返回 False
                logger.error(
                    f"❌ Printify 订单已存在但未在本地数据库中找到，可能需要手动同步: external_id={external_id}"
                )
                return False
            else:
                # 其他错误，直接抛出
                raise
        
        if not printify_result:
            logger.error("❌ Printify订单创建失败: 返回结果为空", scm_order_id=scm_order.id)
            return False
        
        # 检查是否有错误
        if printify_result.get("error"):
            logger.error(
                "❌ Printify订单创建失败",
                scm_order_id=scm_order.id,
                error=printify_result.get("error"),
            )
            return False

        # 获取 Printify 订单 ID
        printify_order_id = printify_result.get("fulfillment_id") or printify_result.get("order_id")
        
        if not printify_order_id:
            logger.error("❌ Printify订单创建失败: 未返回订单ID", scm_order_id=scm_order.id)
            return False

        # 更新SCM订单的Printify信息（与手动流程保持一致）
        from datetime import datetime
        if not scm_order.routing_metadata:
            scm_order.routing_metadata = {}
        scm_order.routing_metadata['printify_order_id'] = printify_order_id
        scm_order.routing_metadata['printify_status'] = printify_result.get('status', 'pending')
        scm_order.routing_metadata['generated_at'] = datetime.utcnow().isoformat()
        
        # 更新 SCM 订单的 printify_order_id 字段
        scm_order.printify_order_id = printify_order_id
        
        # 获取 Printify 外部系统以获取 shop_id
        from app.models.external_system import ExternalSystem, ExternalSystemType
        external_system_result = await db.execute(
            select(ExternalSystem).where(
                and_(
                    ExternalSystem.tenant_id == tenant_id,
                    ExternalSystem.system_type == ExternalSystemType.PRINTIFY
                )
            )
        )
        external_system = external_system_result.scalar_one_or_none()
        
        if external_system:
            scm_order.printify_shop_id = external_system.external_system_id
        
        # 创建 PrintifyOrder 记录并保存到数据库（与手动流程保持一致）
        from app.models.printify_order import PrintifyOrder
        
        # 检查是否已存在 PrintifyOrder 记录
        existing_order_result = await db.execute(
            select(PrintifyOrder).where(
                and_(
                    PrintifyOrder.tenant_id == tenant_id,
                    PrintifyOrder.external_order_id == printify_order_id
                )
            )
        )
        existing_order = existing_order_result.scalar_one_or_none()
        
        if not existing_order:
            # 创建新的 PrintifyOrder 记录
            printify_order = PrintifyOrder(
                tenant_id=tenant_id,
                external_system_id=external_system.id if external_system else None,
                external_order_id=printify_order_id,
                scm_order_id=scm_order.id,
                status=printify_result.get('status', 'pending'),
                total_price=printify_result.get('total_price', 0),
                currency=printify_result.get('currency', scm_order.currency or 'USD'),
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
            logger.info(f"✅ Printify 订单已保存到数据库: external_order_id={printify_order_id}, scm_order_id={scm_order.id}")
        else:
            logger.info(f"ℹ️ Printify 订单已存在: external_order_id={printify_order_id}")

        logger.info(
            "✅ Printify订单创建成功",
            scm_order_id=scm_order.id,
            printify_order_id=printify_order_id,
        )

        return True

    except Exception as e:
        logger.error(
            "❌ 为SCM订单创建Printify订单失败", scm_order_id=scm_order.id, error=str(e)
        )
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        return False


@celery_app.task(bind=True)
def process_new_orders_to_scm(self, tenant_id: int, limit: int = 50, ignore_flags: bool = False):
    """
    处理新的核心订单，自动路由到SCM系统
    这是一个通用任务，适用于所有来源的订单（Shopify、Amazon、Printify等）
    不限制订单来源，只查询还没有创建SCM订单的核心订单
    
    Args:
        tenant_id: 租户ID
        limit: 每次处理的订单数量限制
        ignore_flags: 是否忽略处理标志（手动处理时使用）
    """
    try:
        logger.info("🔍 开始处理新的核心订单，路由到SCM系统", tenant_id=tenant_id, limit=limit)

        async def _process_orders():
            from app.core.database import AsyncSessionLocal

            async with AsyncSessionLocal() as db:
                from sqlalchemy.orm import selectinload
                
                # 获取所有未处理的订单（不限制来源），并加载 items 关系
                # 只查询还没有创建SCM订单的核心订单
                # 如果 ignore_flags=False，且 auto_routed_to_scm=False（避免重复处理）
                # 检查 ScmOrderSource 表（实际关联表）和 SCMOrder.source_order_id（兼容旧数据）
                filter_conditions = [Order.tenant_id == tenant_id]
                if not ignore_flags:
                    filter_conditions.append(Order.auto_routed_to_scm == False)
                
                # 只处理还没有创建SCM订单的订单
                # 检查 ScmOrderSource 表（主要关联表）
                filter_conditions.append(
                    ~Order.id.in_(
                        select(ScmOrderSource.source_order_id).where(
                            ScmOrderSource.tenant_id == tenant_id
                        )
                    )
                )
                # 同时检查 SCMOrder.source_order_id（兼容旧数据）
                filter_conditions.append(
                    ~Order.id.in_(
                        select(SCMOrder.source_order_id).where(
                            and_(
                                SCMOrder.source_order_id.isnot(None),
                                SCMOrder.tenant_id == tenant_id
                            )
                        )
                    )
                )
                
                result = await db.execute(
                    select(Order)
                    .options(selectinload(Order.items))  # 加载订单项
                    .filter(and_(*filter_conditions))
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
                            # 注意：不再在这里自动创建Printify订单
                            # Printify订单的创建由单独的定时任务 create_printify_orders_from_scm 处理
                            # 这样可以更好地控制流程，并且可以在画面上单独控制开关
                            
                            # 标记订单为已自动路由到SCM（手动处理时也标记，避免下次自动处理）
                            if not ignore_flags:
                                order.auto_routed_to_scm = True
                            await db.commit()
                            
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
def sync_shopify_orders_to_core(self, tenant_id: int, limit: int = 50, ignore_flags: bool = False):
    """
    自动将Shopify订单同步到核心订单表
    对应步骤: sync_to_core_orders
    
    Args:
        tenant_id: 租户ID
        limit: 每次处理的订单数量限制
        ignore_flags: 是否忽略处理标志（手动处理时使用）
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
        # 如果 ignore_flags=False，只处理 auto_synced_to_core=False 的订单（避免重复处理）
        filter_conditions = [ShopifyOrder.tenant_id == tenant_id]
        if not ignore_flags:
            filter_conditions.append(ShopifyOrder.auto_synced_to_core == False)
        
        unsynced_shopify_orders = db.query(ShopifyOrder).filter(
            and_(*filter_conditions)
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
                    # 标记为已自动同步（手动处理时也标记，避免下次自动处理）
                    if not ignore_flags:
                        shopify_order.auto_synced_to_core = True
                    db.commit()
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


@celery_app.task(bind=True)
def create_printify_orders_from_scm(self, tenant_id: int, limit: int = 50, ignore_flags: bool = False):
    """
    从SCM订单批量创建Printify订单
    对应步骤: create_printify_orders_from_scm
    
    Args:
        tenant_id: 租户ID
        limit: 每次处理的订单数量限制
        ignore_flags: 是否忽略处理标志（手动处理时使用）
    """
    import threading
    import asyncio
    
    # 用于在线程间传递结果和异常
    result_container = {}
    exception_container = {}
    
    def run_in_thread():
        """在新线程中运行异步代码，避免事件循环冲突"""
        try:
            # 创建新的事件循环（在新线程中）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result_container['result'] = loop.run_until_complete(_create_printify_orders())
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
    
    async def _create_printify_orders():
        from app.core.database import AsyncSessionLocal
        from app.models.printify_order import PrintifyOrder

        async with AsyncSessionLocal() as db:
                # 查询还没有创建Printify订单的SCM订单
                # 只查询routing_metadata中target_system_type为PRINTIFY的订单
                # 如果 ignore_flags=False，且 auto_created_printify_order=False（避免重复处理）
                from sqlalchemy import text
                
                filter_conditions = [
                    SCMOrder.tenant_id == tenant_id,
                    # 从 routing_metadata JSON 字段中检查 target_system_type
                    # 使用 PostgreSQL JSON 操作符查询 (->> 返回文本，-> 返回 JSON)
                    # 注意：使用 UPPER() 处理大小写不敏感，因为可能存储为 'printify' 或 'PRINTIFY'
                    SCMOrder.routing_metadata.isnot(None),  # 确保 routing_metadata 不为空
                    text("UPPER(scm_orders.routing_metadata->>'target_system_type') = 'PRINTIFY'"),
                ]
                if not ignore_flags:
                    filter_conditions.append(SCMOrder.auto_created_printify_order == False)
                
                # 检查是否已经有Printify订单
                filter_conditions.append(
                    ~SCMOrder.id.in_(
                        select(PrintifyOrder.scm_order_id).where(
                            PrintifyOrder.tenant_id == tenant_id,
                            PrintifyOrder.scm_order_id.isnot(None)
                        )
                    )
                )
                
                result = await db.execute(
                    select(SCMOrder)
                    .filter(and_(*filter_conditions))
                    .limit(limit)
                )
                scm_orders = result.scalars().all()

                if not scm_orders:
                    # 添加详细日志，帮助诊断为什么没有订单
                    logger.info("ℹ️ 没有需要创建Printify订单的SCM订单", tenant_id=tenant_id)
                    
                    # 查询所有SCM订单，检查它们为什么不匹配条件
                    all_scm_orders_result = await db.execute(
                        select(SCMOrder).where(SCMOrder.tenant_id == tenant_id).limit(10)
                    )
                    all_scm_orders = all_scm_orders_result.scalars().all()
                    
                    logger.info(f"🔍 诊断信息: 租户 {tenant_id} 共有 {len(all_scm_orders)} 个SCM订单（前10个）")
                    for order in all_scm_orders:
                        routing_metadata = order.routing_metadata or {}
                        target_system_type = routing_metadata.get("target_system_type", "N/A")
                        has_printify_order = order.printify_order_id is not None
                        logger.info(
                            f"  订单 {order.scm_order_number or order.id}: "
                            f"target_system_type={target_system_type}, "
                            f"auto_created_printify_order={order.auto_created_printify_order}, "
                            f"has_printify_order={has_printify_order}, "
                            f"routing_metadata={'存在' if order.routing_metadata else 'NULL'}"
                        )
                    
                    return {
                        "success": True,
                        "message": "没有需要处理的订单",
                        "processed_count": 0,
                    }

                processed_count = 0
                success_count = 0
                error_count = 0
                errors = []

                for scm_order in scm_orders:
                    try:
                        # 使用现有的函数创建Printify订单
                        success = await _create_printify_order_for_scm(db, scm_order, tenant_id)
                        
                        if success:
                            # 标记为已自动创建Printify订单（手动处理时也标记，避免下次自动处理）
                            if not ignore_flags:
                                scm_order.auto_created_printify_order = True
                            await db.commit()
                            success_count += 1
                            logger.info(
                                f"✅ SCM订单 {scm_order.id} 的Printify订单创建成功"
                            )
                        else:
                            error_count += 1
                            errors.append(f"SCM订单 {scm_order.id} 创建Printify订单失败")
                            logger.warning(
                                f"⚠️ SCM订单 {scm_order.id} 创建Printify订单失败"
                            )
                        
                        processed_count += 1
                    except Exception as e:
                        error_count += 1
                        error_msg = f"SCM订单 {scm_order.id} 处理失败: {str(e)}"
                        errors.append(error_msg)
                        logger.error(f"❌ {error_msg}")

                return {
                    "success": True,
                    "processed_count": processed_count,
                    "success_count": success_count,
                    "error_count": error_count,
                    "errors": errors,
                }
    
    try:
        logger.info("🔍 开始从SCM订单创建Printify订单", tenant_id=tenant_id, limit=limit)
        
        # 在独立线程中运行
        thread = threading.Thread(target=run_in_thread, daemon=False)
        thread.start()
        thread.join()
        
        # 检查是否有异常
        if 'error' in exception_container:
            error = exception_container['error']
            error_type = exception_container.get('error_type', type(error).__name__)
            error_message = exception_container.get('error_message', str(error))
            error_traceback = exception_container.get('error_traceback', '')
            
            logger.error(f"❌ 从SCM订单创建Printify订单任务失败: {error_type}: {error_message}")
            logger.error(f"   异常堆栈: {error_traceback}")
            
            if self:
                self.update_state(
                    state="FAILURE",
                    meta={
                        "error": error_message,
                        "error_type": error_type,
                        "traceback": error_traceback
                    }
                )
            raise error
        
        # 返回结果
        if 'result' in result_container:
            return result_container['result']
        else:
            raise RuntimeError("任务执行完成但没有返回结果")
            
    except Exception as e:
        logger.error(f"❌ 从SCM订单创建Printify订单任务失败: {e}")
        if self:
            self.update_state(
                state="FAILURE",
                meta={"error": str(e)}
            )
        raise


@celery_app.task(bind=True)
def sync_printify_orders_to_local(self, tenant_id: int, limit: int = 100, ignore_flags: bool = False):
    """
    从Printify API同步订单到printify_orders本地表
    对应步骤: sync_printify_orders_to_local
    
    Args:
        tenant_id: 租户ID
        limit: 每次处理的订单数量限制
        ignore_flags: 是否忽略处理标志（手动处理时使用，此任务通常每次都会更新，所以标志主要用于标记）
    """
    try:
        logger.info("🔍 开始从Printify API同步订单到本地表", tenant_id=tenant_id, limit=limit)

        async def _sync_printify_orders():
            from app.core.database import AsyncSessionLocal
            from app.models.printify_order import PrintifyOrder
            from app.models.external_system import ExternalSystem, ExternalSystemType
            from app.services.external_system_service import ExternalSystemService
            from datetime import datetime, timedelta, timezone

            async with AsyncSessionLocal() as db:
                # 获取Printify外部系统
                service = ExternalSystemService(db)
                printify_systems = await service.get_external_systems_by_type(
                    tenant_id, "PRINTIFY"
                )

                if not printify_systems:
                    logger.error("❌ 未找到Printify外部系统", tenant_id=tenant_id)
                    return {
                        "success": False,
                        "message": "未找到Printify外部系统",
                        "orders_synced": 0,
                    }

                printify_system = printify_systems[0]
                external_system_id = printify_system.id
                # printify_system 是 ExternalSystem 对象，不是字典
                credentials = printify_system.credentials or {}

                # 解密凭据
                access_token = decrypt_data(credentials.get("access_token", "")) if credentials.get("access_token") else None
                shop_id = decrypt_data(credentials.get("shop_id", "")) if credentials.get("shop_id") else None

                if not access_token or not shop_id:
                    logger.error("❌ Printify凭据不完整", tenant_id=tenant_id)
                    return {
                        "success": False,
                        "message": "Printify凭据不完整",
                        "orders_synced": 0,
                    }

                # 创建Printify服务
                printify_service = PrintifyService(access_token)

                # 获取Printify订单（只获取最近一周的订单）
                orders_result = await printify_service.get_orders(shop_id, limit=limit, page=1)

                if not orders_result.get("success"):
                    logger.error("❌ 获取Printify订单失败", error=orders_result.get("message"))
                    return {
                        "success": False,
                        "message": orders_result.get("message", "获取订单失败"),
                        "orders_synced": 0,
                    }

                orders_data = orders_result.get("orders", [])
                logger.info(f"📦 从Printify API获取到 {len(orders_data)} 个订单")

                orders_synced = 0
                orders_updated = 0
                errors = []

                # 过滤最近一周的订单
                one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
                
                for order_data in orders_data:
                    try:
                        # 检查订单创建时间
                        created_at_str = order_data.get("created_at")
                        if created_at_str:
                            try:
                                if isinstance(created_at_str, str):
                                    if created_at_str.endswith('Z'):
                                        created_at_str = created_at_str.replace('Z', '+00:00')
                                    created_at = datetime.fromisoformat(created_at_str)
                                else:
                                    created_at = created_at_str

                                if created_at.tzinfo is None:
                                    created_at = created_at.replace(tzinfo=timezone.utc)

                                # 如果订单创建时间早于一周前，跳过
                                if created_at < one_week_ago:
                                    continue
                            except Exception as e:
                                logger.warning(f"⚠️ 无法解析订单创建时间，继续处理: {e}")

                        external_order_id = str(order_data.get("id", ""))

                        # 检查是否已存在
                        result = await db.execute(
                            select(PrintifyOrder).where(
                                and_(
                                    PrintifyOrder.tenant_id == tenant_id,
                                    PrintifyOrder.external_order_id == external_order_id
                                )
                            )
                        )
                        existing_order = result.scalar_one_or_none()

                        # 提取订单信息
                        shipments = order_data.get("shipments", [])
                        tracking_number = None
                        tracking_url = None
                        carrier = None
                        shipped_at = None
                        delivered_at = None

                        if shipments and len(shipments) > 0:
                            shipment = shipments[0]
                            tracking_number = shipment.get("tracking_number")
                            tracking_url = shipment.get("tracking_url")
                            carrier = shipment.get("carrier")
                            if shipment.get("shipped_at"):
                                try:
                                    shipped_at = datetime.fromisoformat(
                                        shipment["shipped_at"].replace('Z', '+00:00')
                                    )
                                except:
                                    pass
                            if shipment.get("delivered_at"):
                                try:
                                    delivered_at = datetime.fromisoformat(
                                        shipment["delivered_at"].replace('Z', '+00:00')
                                    )
                                except:
                                    pass

                        order_dict = {
                            "tenant_id": tenant_id,
                            "external_system_id": external_system_id,
                            "external_order_id": external_order_id,
                            "status": order_data.get("status", "pending"),
                            "total_price": order_data.get("total_price"),
                            "currency": order_data.get("currency", "USD"),
                            "customer_email": order_data.get("address_to", {}).get("email"),
                            "customer_name": f"{order_data.get('address_to', {}).get('first_name', '')} {order_data.get('address_to', {}).get('last_name', '')}".strip(),
                            "shipping_address": order_data.get("address_to"),
                            "billing_address": order_data.get("address_to"),  # Printify通常使用相同地址
                            "printify_data": order_data,
                            "external_data": {
                                "tracking_number": tracking_number,
                                "tracking_url": tracking_url,
                                "carrier": carrier,
                                "shipments": shipments,
                            },
                            "tracking_number": tracking_number,
                            "tracking_url": tracking_url,
                            "carrier": carrier,
                            "shipped_at": shipped_at,
                            "delivered_at": delivered_at,
                        }

                        if existing_order:
                            # 更新现有订单
                            for key, value in order_dict.items():
                                if key != "tenant_id" and hasattr(existing_order, key):
                                    setattr(existing_order, key, value)
                            existing_order.updated_at = datetime.now(timezone.utc)
                            # 如果之前没有标记，现在标记为已自动同步
                            if not existing_order.auto_synced_from_api:
                                existing_order.auto_synced_from_api = True
                            orders_updated += 1
                            logger.info(f"✅ 更新Printify订单: {external_order_id}")
                        else:
                            # 创建新订单
                            new_order = PrintifyOrder(**order_dict)
                            new_order.auto_synced_from_api = True  # 标记为已自动同步
                            db.add(new_order)
                            orders_synced += 1
                            logger.info(f"✅ 创建Printify订单: {external_order_id}")

                        await db.commit()

                    except Exception as e:
                        await db.rollback()
                        error_msg = f"处理订单 {order_data.get('id')} 时出错: {e}"
                        errors.append(error_msg)
                        logger.error(f"❌ {error_msg}")

                return {
                    "success": True,
                    "orders_synced": orders_synced,
                    "orders_updated": orders_updated,
                    "errors": errors,
                }

        # 运行异步函数
        result = asyncio.run(_sync_printify_orders())
        return result

    except Exception as e:
        logger.error(f"❌ 从Printify API同步订单到本地表失败: {e}")
        if self:
            self.update_state(
                state="FAILURE",
                meta={"error": str(e)}
            )
        raise


@celery_app.task(bind=True)
def sync_printify_local_to_scm(self, tenant_id: int, limit: int = 100, ignore_flags: bool = False):
    """
    从printify_orders本地表同步发货信息到SCM订单
    对应步骤: sync_printify_local_to_scm
    
    注意：这是修改后的版本，从本地表读取而不是直接从API
    
    Args:
        tenant_id: 租户ID
        limit: 每次处理的订单数量限制
        ignore_flags: 是否忽略处理标志（手动处理时使用）
    """
    try:
        logger.info("🔍 开始从Printify本地表同步发货信息到SCM订单", tenant_id=tenant_id, limit=limit)

        from app.core.database import get_sync_db
        from app.models.printify_order import PrintifyOrder
        from app.models.scm_order import SCMOrder
        from datetime import datetime

        db = next(get_sync_db())

        # 查询有发货信息且关联了SCM订单的Printify订单
        # 如果 ignore_flags=False，且 auto_synced_fulfillment_to_scm=False（避免重复处理）
        filter_conditions = [
            PrintifyOrder.tenant_id == tenant_id,
            PrintifyOrder.scm_order_id.isnot(None),
            PrintifyOrder.tracking_number.isnot(None),  # 有跟踪号才需要同步
        ]
        if not ignore_flags:
            filter_conditions.append(PrintifyOrder.auto_synced_fulfillment_to_scm == False)
        
        printify_orders = db.query(PrintifyOrder).filter(
            and_(*filter_conditions)
        ).limit(limit).all()

        if not printify_orders:
            logger.info("ℹ️ 没有需要同步的Printify订单", tenant_id=tenant_id)
            return {
                "success": True,
                "message": "没有需要同步的订单",
                "synced_count": 0,
            }

        synced_count = 0
        errors = []

        for printify_order in printify_orders:
            try:
                scm_order = printify_order.scm_order
                if not scm_order:
                    continue

                needs_update = False

                # 检查跟踪号
                if printify_order.tracking_number and scm_order.tracking_number != printify_order.tracking_number:
                    scm_order.tracking_number = printify_order.tracking_number
                    needs_update = True

                # 检查跟踪链接
                if printify_order.tracking_url and scm_order.tracking_url != printify_order.tracking_url:
                    scm_order.tracking_url = printify_order.tracking_url
                    needs_update = True

                # 检查承运商
                if printify_order.carrier and scm_order.carrier != printify_order.carrier:
                    scm_order.carrier = printify_order.carrier
                    needs_update = True

                # 检查发货时间
                if printify_order.shipped_at and (not scm_order.shipped_at or scm_order.shipped_at != printify_order.shipped_at):
                    scm_order.shipped_at = printify_order.shipped_at
                    needs_update = True

                # 检查送达时间
                if printify_order.delivered_at and (not scm_order.delivered_at or scm_order.delivered_at != printify_order.delivered_at):
                    scm_order.delivered_at = printify_order.delivered_at
                    needs_update = True

                # 更新订单状态
                if printify_order.status == 'shipped' and scm_order.fulfillment_status != 'shipped':
                    scm_order.fulfillment_status = 'shipped'
                    needs_update = True
                elif printify_order.status == 'delivered' and scm_order.fulfillment_status != 'delivered':
                    scm_order.fulfillment_status = 'delivered'
                    needs_update = True

                if needs_update:
                    scm_order.updated_at = datetime.now()
                    # 标记Printify订单为已自动同步发货信息到SCM（手动处理时也标记，避免下次自动处理）
                    if not ignore_flags:
                        printify_order.auto_synced_fulfillment_to_scm = True
                        # 标记SCM订单为已自动同步发货信息从Printify
                        scm_order.auto_synced_fulfillment_from_printify = True
                    db.commit()
                    synced_count += 1
                    logger.info(f"✅ 同步发货信息成功: Printify订单 {printify_order.id} -> SCM订单 {scm_order.id}")

            except Exception as e:
                db.rollback()
                error_msg = f"同步订单 {printify_order.id} 失败: {str(e)}"
                errors.append(error_msg)
                logger.error(f"❌ {error_msg}")

        return {
            "success": True,
            "synced_count": synced_count,
            "total_orders": len(printify_orders),
            "errors": errors,
        }

    except Exception as e:
        logger.error(f"❌ 从Printify本地表同步发货信息到SCM订单失败: {e}")
        if self:
            self.update_state(
                state="FAILURE",
                meta={"error": str(e)}
            )
        raise


@celery_app.task(bind=True)
def sync_shopify_fulfillment_to_local(self, tenant_id: int, limit: int = 100, ignore_flags: bool = False):
    """
    从Shopify API同步发货信息到shopify_orders本地表
    对应步骤: sync_shopify_fulfillment_to_local
    
    Args:
        tenant_id: 租户ID
        limit: 每次处理的订单数量限制
        ignore_flags: 是否忽略处理标志（手动处理时使用）
    """
    try:
        logger.info("🔍 开始从Shopify API同步发货信息到本地表", tenant_id=tenant_id, limit=limit)

        async def _sync_fulfillment():
            from app.core.database import AsyncSessionLocal
            from app.models.shopify_order import ShopifyOrder
            from app.services.shopify.order_service import ShopifyOrderService
            from datetime import datetime, timedelta, timezone

            async with AsyncSessionLocal() as db:
                order_service = ShopifyOrderService(db)

                # 获取Shopify凭据
                credentials = await order_service.get_shopify_credentials(tenant_id)
                if not credentials:
                    return {
                        "success": False,
                        "message": "无法获取Shopify凭据",
                        "orders_updated": 0,
                    }

                access_token = credentials.get("access_token")
                store_url = credentials.get("store_url", "")
                shop_name = store_url.replace("https://", "").replace(".myshopify.com", "")

                # 创建Shopify客户端
                from app.services.shopify.client import ShopifyGraphQLClient
                client = ShopifyGraphQLClient(shop_name, access_token)

                # 查询最近一周有发货信息的订单（只查询已发货的订单）
                one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
                since_time_iso = one_week_ago.isoformat().replace('+00:00', 'Z')
                query_filter = f"fulfillment_status:fulfilled AND updated_at:>={since_time_iso}"

                # 获取需要更新的shopify_orders，且 auto_synced_fulfillment_from_api=False（避免重复处理）
                result = await db.execute(
                    select(ShopifyOrder).where(
                        and_(
                            ShopifyOrder.tenant_id == tenant_id,
                            # 只查询有shopify_order_id的订单
                            ShopifyOrder.shopify_order_id.isnot(None),
                            ShopifyOrder.auto_synced_fulfillment_from_api == False  # 只处理未自动同步的订单
                        )
                    ).limit(limit)
                )
                shopify_orders = result.scalars().all()

                if not shopify_orders:
                    logger.info("ℹ️ 没有需要同步发货信息的Shopify订单", tenant_id=tenant_id)
                    return {
                        "success": True,
                        "message": "没有需要同步的订单",
                        "orders_updated": 0,
                    }

                orders_updated = 0
                errors = []

                # 批量获取订单的履行信息
                order_ids = [order.shopify_order_id for order in shopify_orders]
                
                # 使用GraphQL查询获取订单的履行信息
                query = """
                query getOrders($ids: [ID!]!) {
                    nodes(ids: $ids) {
                        ... on Order {
                            id
                            fulfillments {
                                id
                                status
                                trackingInfo {
                                    number
                                    url
                                    company
                                }
                                updatedAt
                            }
                        }
                    }
                }
                """

                # 分批查询（GraphQL有查询限制）
                batch_size = 50
                all_fulfillments = {}

                for i in range(0, len(order_ids), batch_size):
                    batch_ids = order_ids[i:i+batch_size]
                    try:
                        response = await client._make_request(query, {"ids": batch_ids})
                        nodes = response.get("nodes", [])
                        
                        for node in nodes:
                            if node and "fulfillments" in node:
                                order_id = node.get("id")
                                fulfillments = node.get("fulfillments", [])
                                all_fulfillments[order_id] = fulfillments
                    except Exception as e:
                        logger.error(f"❌ 批量获取履行信息失败: {e}")
                        errors.append(f"批量查询失败: {str(e)}")

                # 更新shopify_orders表的fulfillments字段
                for shopify_order in shopify_orders:
                    try:
                        fulfillments = all_fulfillments.get(shopify_order.shopify_order_id, [])
                        if fulfillments:
                            # 更新fulfillments字段
                            shopify_order.fulfillments = fulfillments
                            shopify_order.last_synced_at = datetime.now(timezone.utc)
                            # 标记为已自动同步发货信息从API（手动处理时也标记，避免下次自动处理）
                            if not ignore_flags:
                                shopify_order.auto_synced_fulfillment_from_api = True
                            orders_updated += 1
                            logger.info(f"✅ 更新Shopify订单发货信息: {shopify_order.shopify_order_id}")
                    except Exception as e:
                        error_msg = f"更新订单 {shopify_order.id} 失败: {e}"
                        errors.append(error_msg)
                        logger.error(f"❌ {error_msg}")

                await db.commit()

                return {
                    "success": True,
                    "orders_updated": orders_updated,
                    "total_orders": len(shopify_orders),
                    "errors": errors,
                }

        # 运行异步函数
        result = asyncio.run(_sync_fulfillment())
        return result

    except Exception as e:
        logger.error(f"❌ 从Shopify API同步发货信息到本地表失败: {e}")
        if self:
            self.update_state(
                state="FAILURE",
                meta={"error": str(e)}
            )
        raise


@celery_app.task(bind=True)
def sync_shopify_local_fulfillment_to_core(self, tenant_id: int, limit: int = 100, ignore_flags: bool = False):
    """
    从shopify_orders本地表同步发货信息到核心订单表
    对应步骤: sync_shopify_local_fulfillment_to_core
    
    Args:
        tenant_id: 租户ID
        limit: 每次处理的订单数量限制
        ignore_flags: 是否忽略处理标志（手动处理时使用）
    """
    try:
        logger.info("🔍 开始从Shopify本地表同步发货信息到核心订单表", tenant_id=tenant_id, limit=limit)

        from app.core.database import get_sync_db
        from app.models.shopify_order import ShopifyOrder
        from app.models.order import Order
        from datetime import datetime

        db = next(get_sync_db())

        # 查询有发货信息且关联了核心订单的Shopify订单，且 auto_synced_fulfillment_to_core=False（避免重复处理）
        shopify_orders = db.query(ShopifyOrder).filter(
            and_(
                ShopifyOrder.tenant_id == tenant_id,
                ShopifyOrder.fulfillments.isnot(None),  # 有发货信息
                ShopifyOrder.shopify_order_id.isnot(None),
                ShopifyOrder.auto_synced_fulfillment_to_core == False  # 只处理未自动同步的订单
            )
        ).limit(limit).all()

        if not shopify_orders:
            logger.info("ℹ️ 没有需要同步发货信息的Shopify订单", tenant_id=tenant_id)
            return {
                "success": True,
                "message": "没有需要同步的订单",
                "orders_updated": 0,
            }

        orders_updated = 0
        errors = []

        for shopify_order in shopify_orders:
            try:
                # 查找对应的核心订单
                core_order = db.query(Order).filter(
                    and_(
                        Order.tenant_id == tenant_id,
                        Order.external_order_id == shopify_order.shopify_order_id
                    )
                ).first()

                if not core_order:
                    continue

                # 提取最新的发货信息
                fulfillments = shopify_order.fulfillments or []
                if not fulfillments:
                    continue

                # 取第一个履行信息（通常是最新的）
                fulfillment = fulfillments[0] if fulfillments else {}
                tracking_info = fulfillment.get("trackingInfo", [])
                
                needs_update = False

                # 更新跟踪号
                if tracking_info and len(tracking_info) > 0:
                    tracking = tracking_info[0]
                    tracking_number = tracking.get("number")
                    tracking_url = tracking.get("url")
                    carrier = tracking.get("company")

                    if tracking_number and core_order.tracking_number != tracking_number:
                        core_order.tracking_number = tracking_number
                        needs_update = True

                    if tracking_url and core_order.tracking_url != tracking_url:
                        core_order.tracking_url = tracking_url
                        needs_update = True

                # 更新fulfillment_status
                fulfillment_status = fulfillment.get("status", "")
                if fulfillment_status and core_order.fulfillment_status != fulfillment_status:
                    core_order.fulfillment_status = fulfillment_status
                    needs_update = True

                # 更新external_data中的fulfillments
                if not core_order.external_data:
                    core_order.external_data = {}
                core_order.external_data["fulfillments"] = fulfillments
                needs_update = True

                if needs_update:
                    core_order.updated_at = datetime.now()
                    # 标记Shopify订单为已自动同步发货信息到核心订单（手动处理时也标记，避免下次自动处理）
                    if not ignore_flags:
                        shopify_order.auto_synced_fulfillment_to_core = True
                    db.commit()
                    orders_updated += 1
                    logger.info(f"✅ 同步发货信息成功: Shopify订单 {shopify_order.id} -> 核心订单 {core_order.id}")

            except Exception as e:
                db.rollback()
                error_msg = f"同步订单 {shopify_order.id} 失败: {str(e)}"
                errors.append(error_msg)
                logger.error(f"❌ {error_msg}")

        return {
            "success": True,
            "orders_updated": orders_updated,
            "total_orders": len(shopify_orders),
            "errors": errors,
        }

    except Exception as e:
        logger.error(f"❌ 从Shopify本地表同步发货信息到核心订单表失败: {e}")
        if self:
            self.update_state(
                state="FAILURE",
                meta={"error": str(e)}
            )
        raise
