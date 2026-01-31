"""
Order routing background tasks
"""

import logging
from typing import Dict, Any
from celery import current_task
from app.tasks.celery_app import celery_app
from app.services.order_routing_service import OrderRoutingService
from app.schemas.scm_order import OrderRoutingConfig

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def route_order_to_scm_task(self, order_id: int, tenant_id: int, routing_config: Dict[str, Any]):
    """后台异步将订单路由到SCM系统"""
    try:
        logger.info(f"开始后台路由订单 {order_id} 到SCM系统")
        
        # 更新任务进度
        if current_task:
            current_task.update_state(
                state="PROGRESS",
                meta={"current": 1, "total": 3, "status": "开始路由订单"}
            )
        
        # 这里需要数据库会话，在实际实现中需要处理
        # 由于Celery任务不能直接使用FastAPI的依赖注入，
        # 需要手动创建数据库会话
        from app.core.database import get_async_db_session
        
        async def _route_order():
            async with get_async_db_session() as db:
                # 获取订单
                from app.models.order import Order
                from sqlalchemy import select
                
                result = await db.execute(
                    select(Order).where(
                        Order.id == order_id,
                        Order.tenant_id == tenant_id
                    )
                )
                order = result.scalar_one_or_none()
                
                if not order:
                    raise Exception(f"Order {order_id} not found")
                
                # 更新任务进度
                if current_task:
                    current_task.update_state(
                        state="PROGRESS",
                        meta={"current": 2, "total": 3, "status": "应用路由规则"}
                    )
                
                # 创建路由配置
                config = OrderRoutingConfig(**routing_config)
                
                # 路由服务
                routing_service = OrderRoutingService(db)
                scm_orders = await routing_service.route_order_to_scm(
                    order, 
                    config,
                    tenant_id
                )
                
                # 更新任务进度
                if current_task:
                    current_task.update_state(
                        state="PROGRESS",
                        meta={"current": 3, "total": 3, "status": "路由完成"}
                    )
                
                return {
                    "status": "success",
                    "order_id": order_id,
                    "scm_orders_created": len(scm_orders),
                    "scm_order_ids": [so.id for so in scm_orders]
                }
        
        # 运行异步任务
        import asyncio
        result = asyncio.run(_route_order())
        
        logger.info(f"成功完成订单 {order_id} 的路由，创建了 {result['scm_orders_created']} 个SCM订单")
        return result
        
    except Exception as e:
        logger.error(f"后台路由订单 {order_id} 失败: {e}")
        if current_task:
            current_task.update_state(
                state="FAILURE",
                meta={"error": str(e)}
            )
        raise


@celery_app.task(bind=True)
def batch_route_orders_task(self, order_ids: list, tenant_id: int, routing_config: Dict[str, Any]):
    """批量后台路由订单到SCM系统"""
    try:
        logger.info(f"开始批量路由 {len(order_ids)} 个订单到SCM系统")
        
        results = []
        successful_count = 0
        failed_count = 0
        
        for i, order_id in enumerate(order_ids):
            try:
                # 更新任务进度
                if current_task:
                    current_task.update_state(
                        state="PROGRESS",
                        meta={
                            "current": i + 1, 
                            "total": len(order_ids), 
                            "status": f"处理订单 {order_id}"
                        }
                    )
                
                # 调用单个订单路由任务
                result = route_order_to_scm_task.apply(
                    args=[order_id, tenant_id, routing_config]
                ).get()
                
                results.append({
                    "order_id": order_id,
                    "success": True,
                    "result": result
                })
                successful_count += 1
                
            except Exception as e:
                logger.error(f"路由订单 {order_id} 失败: {e}")
                results.append({
                    "order_id": order_id,
                    "success": False,
                    "error": str(e)
                })
                failed_count += 1
        
        final_result = {
            "status": "completed",
            "total_orders": len(order_ids),
            "successful_count": successful_count,
            "failed_count": failed_count,
            "results": results
        }
        
        logger.info(f"批量路由完成: 成功 {successful_count}，失败 {failed_count}")
        return final_result
        
    except Exception as e:
        logger.error(f"批量路由任务失败: {e}")
        if current_task:
            current_task.update_state(
                state="FAILURE",
                meta={"error": str(e)}
            )
        raise


@celery_app.task(bind=True)
def auto_route_new_orders_task(self, tenant_id: int, hours: int = 24):
    """自动路由新订单到SCM系统"""
    try:
        logger.info(f"开始自动路由租户 {tenant_id} 过去 {hours} 小时的新订单")
        
        # 更新任务进度
        if current_task:
            current_task.update_state(
                state="PROGRESS",
                meta={"current": 1, "total": 3, "status": "查询新订单"}
            )
        
        from app.core.database import get_async_db_session
        from app.models.order import Order
        from sqlalchemy import select
        from datetime import datetime, timedelta
        
        async def _auto_route():
            async with get_async_db_session() as db:
                # 查询过去指定小时内的新订单
                cutoff_time = datetime.now() - timedelta(hours=hours)
                
                result = await db.execute(
                    select(Order).where(
                        Order.tenant_id == tenant_id,
                        Order.created_at >= cutoff_time,
                        Order.status == "pending"  # 只处理待处理订单
                    )
                )
                orders = result.scalars().all()
                
                logger.info(f"找到 {len(orders)} 个新订单需要自动路由")
                
                # 更新任务进度
                if current_task:
                    current_task.update_state(
                        state="PROGRESS",
                        meta={"current": 2, "total": 3, "status": f"开始路由 {len(orders)} 个订单"}
                    )
                
                # 获取租户的默认路由配置
                default_config = OrderRoutingConfig(
                    routing_strategy="auto",
                    routing_rules={
                        "auto_route_enabled": True,
                        "default_target_system": "printify"
                    }
                )
                
                # 路由服务
                routing_service = OrderRoutingService(db)
                
                routed_orders = 0
                for order in orders:
                    try:
                        scm_orders = await routing_service.route_order_to_scm(
                            order, 
                            default_config,
                            tenant_id
                        )
                        routed_orders += 1
                        logger.info(f"成功路由订单 {order.id}，创建了 {len(scm_orders)} 个SCM订单")
                    except Exception as e:
                        logger.error(f"路由订单 {order.id} 失败: {e}")
                
                # 更新任务进度
                if current_task:
                    current_task.update_state(
                        state="PROGRESS",
                        meta={"current": 3, "total": 3, "status": "自动路由完成"}
                    )
                
                return {
                    "status": "success",
                    "tenant_id": tenant_id,
                    "total_orders": len(orders),
                    "routed_orders": routed_orders,
                    "hours": hours
                }
        
        # 运行异步任务
        import asyncio
        result = asyncio.run(_auto_route())
        
        logger.info(f"自动路由完成: 处理了 {result['total_orders']} 个订单，成功路由 {result['routed_orders']} 个")
        return result
        
    except Exception as e:
        logger.error(f"自动路由任务失败: {e}")
        if current_task:
            current_task.update_state(
                state="FAILURE",
                meta={"error": str(e)}
            )
        raise
