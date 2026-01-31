"""
Shopify 相关的 Celery 异步任务
用于批量处理订单数据
"""
import asyncio
import threading
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from celery import current_task
from sqlalchemy.orm import Session

from app.tasks.celery_app import celery_app
from app.core.database import get_sync_db, get_async_db
from app.services.shopify.client import create_shopify_client
from app.services.shopify.order_service import ShopifyOrderService
from app.services.shopify.product_service import ShopifyProductService
from app.models.order import Order
from app.schemas.order import OrderCreate

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="fetch_shopify_orders")
def fetch_shopify_orders_task(
    self,
    shop_name: str,
    access_token: str,
    query_filter: Optional[str] = None,
    max_orders: Optional[int] = None
):
    """
    批量获取 Shopify 订单的 Celery 任务
    
    Args:
        shop_name: Shopify 商店名称
        access_token: API 访问令牌
        query_filter: 订单过滤条件
        max_orders: 最大订单数量
    """
    try:
        # 更新任务状态
        self.update_state(
            state='PROGRESS',
            meta={'status': '开始获取订单', 'progress': 0}
        )
        
        # 运行异步函数
        result = asyncio.run(_fetch_orders_async(
            shop_name=shop_name,
            access_token=access_token,
            query_filter=query_filter,
            max_orders=max_orders,
            task=self
        ))
        
        return {
            'status': '完成',
            'orders_fetched': result['orders_count'],
            'orders_saved': result['saved_count'],
            'errors': result['errors']
        }
        
    except Exception as e:
        logger.error(f"获取订单任务失败: {e}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise


@celery_app.task(bind=True, name="sync_shopify_orders")
def sync_shopify_orders_task(
    self,
    tenant_id: int,
    query_filter: Optional[str] = None,
    max_orders: Optional[int] = None,
    sync_recent_only: bool = True
):
    """
    同步 Shopify 订单的 Celery 任务
    
    Args:
        tenant_id: 租户 ID
        query_filter: 订单过滤条件
        max_orders: 最大订单数量
        sync_recent_only: 是否只同步最近的订单
    """
    try:
        # 更新任务状态
        self.update_state(
            state='PROGRESS',
            meta={'status': '开始同步订单', 'progress': 0}
        )
        
        # 运行异步函数
        result = asyncio.run(_sync_orders_async(
            tenant_id=tenant_id,
            query_filter=query_filter,
            max_orders=max_orders,
            sync_recent_only=sync_recent_only,
            task=self
        ))
        
        return result
        
    except Exception as e:
        logger.error(f"同步订单任务失败: {e}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise


@celery_app.task(bind=True, name="sync_shopify_orders_1min")
def sync_shopify_orders_1min_task(self, tenant_id: int = None):
    """
    每分钟同步 Shopify 订单的定时任务
    
    Args:
        tenant_id: 可选的租户ID。如果提供，只同步该租户的订单；否则同步所有活跃租户
    """
    try:
        logger.info("开始执行每分钟订单同步任务")
        
        # 获取所有活跃的租户
        db = next(get_sync_db())
        
        if tenant_id:
            # 如果指定了租户ID，只同步该租户
            tenant_ids = [tenant_id]
            logger.info(f"同步指定租户: {tenant_id}")
        else:
            # 这里需要根据你的租户模型来获取活跃租户
            # 暂时使用默认租户 ID 1
            tenant_ids = [1]
            logger.info(f"同步所有活跃租户: {tenant_ids}")
        
        db.close()
        
        # 使用单个事件循环处理所有租户，避免事件循环冲突
        async def _sync_all_tenants():
            from app.core.database import AsyncSessionLocal
            from app.services.shopify.order_service import ShopifyOrderService
            
            results = []
            for tenant_id in tenant_ids:
                try:
                    async with AsyncSessionLocal() as db:
                        # 使用 ShopifyOrderService 同步到 shopify_orders 表（步骤1）
                        order_service = ShopifyOrderService(db)
                        result = await order_service.sync_orders_to_shopify_table(
                            tenant_id=tenant_id,
                            sync_recent_only=True,
                            max_orders=100
                        )
                        results.append({
                            'tenant_id': tenant_id,
                            'result': result
                        })
                except Exception as e:
                    logger.error(f"租户 {tenant_id} 订单同步失败: {e}")
                    import traceback
                    logger.error(f"异常堆栈: {traceback.format_exc()}")
                    results.append({
                        'tenant_id': tenant_id,
                        'error': str(e)
                    })
            return results
        
        # 使用线程来隔离事件循环，避免连接池冲突
        # 这是最可靠的方法，因为每个线程有独立的事件循环
        result_container = {}
        exception_container = {}
        
        def run_in_thread():
            """在线程中运行异步任务"""
            # 在线程中创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                async def _sync_in_thread():
                    return await _sync_all_tenants()
                
                result_container['result'] = loop.run_until_complete(_sync_in_thread())
            except Exception as e:
                # 保存异常的类型和消息，确保可以被正确序列化
                import traceback
                exception_container['error_type'] = type(e).__name__
                exception_container['error_message'] = str(e)
                exception_container['error_traceback'] = traceback.format_exc()
                exception_container['error'] = e  # 保留原始异常用于日志
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
        
        # 在新线程中执行任务
        thread = threading.Thread(target=run_in_thread)
        thread.start()
        thread.join(timeout=300)  # 最多等待5分钟
        
        if thread.is_alive():
            logger.error("任务执行超时")
            raise TimeoutError("任务执行超时")
        
        if 'error' in exception_container:
            # 记录完整的异常信息
            error_type = exception_container.get('error_type', 'Exception')
            error_message = exception_container.get('error_message', 'Unknown error')
            error_traceback = exception_container.get('error_traceback', '')
            
            logger.error(f"任务执行失败: {error_type}: {error_message}")
            if error_traceback:
                logger.error(f"异常堆栈:\n{error_traceback}")
            
            # 重新抛出异常，确保 Celery 可以正确处理
            # 使用 RuntimeError 作为包装，确保异常类型可以被序列化
            raise RuntimeError(f"{error_type}: {error_message}") from exception_container.get('error')
        
        results = result_container.get('result', [])
        
        logger.info(f"每分钟订单同步任务完成: {results}")
        return {
            'status': '完成',
            'results': results
        }
        
    except Exception as e:
        logger.error(f"每分钟订单同步任务失败: {e}")
        raise


@celery_app.task(bind=True, name="sync_shopify_products")
def sync_shopify_products_task(
    self,
    tenant_id: int,
    query_filter: Optional[str] = None,
    max_products: Optional[int] = None,
    sync_recent_only: bool = True
):
    """
    同步 Shopify 商品的 Celery 任务
    
    Args:
        tenant_id: 租户 ID
        query_filter: 商品过滤条件
        max_products: 最大商品数量
        sync_recent_only: 是否只同步最近的商品
    """
    try:
        # 更新任务状态
        self.update_state(
            state='PROGRESS',
            meta={'status': '开始同步商品', 'progress': 0}
        )
        
        # 运行异步函数
        result = asyncio.run(_sync_products_async(
            tenant_id=tenant_id,
            query_filter=query_filter,
            max_products=max_products,
            sync_recent_only=sync_recent_only,
            task=self
        ))
        
        return result
        
    except Exception as e:
        logger.error(f"同步商品任务失败: {e}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise


@celery_app.task(bind=True, name="sync_shopify_products_1min")
def sync_shopify_products_1min_task(self, tenant_id: int = None):
    """
    每分钟同步 Shopify 商品的定时任务
    
    Args:
        tenant_id: 可选的租户ID。如果提供，只同步该租户的商品；否则同步所有活跃租户
    """
    try:
        logger.info("开始执行每分钟商品同步任务")
        
        # 获取所有活跃的租户
        db = next(get_sync_db())
        
        if tenant_id:
            # 如果指定了租户ID，只同步该租户
            tenant_ids = [tenant_id]
            logger.info(f"同步指定租户: {tenant_id}")
        else:
            # 这里需要根据你的租户模型来获取活跃租户
            # 暂时使用默认租户 ID 1
            tenant_ids = [1]
            logger.info(f"同步所有活跃租户: {tenant_ids}")
        
        db.close()
        
        # 使用单个事件循环处理所有租户，避免事件循环冲突
        async def _sync_all_tenants():
            results = []
            for tenant_id in tenant_ids:
                try:
                    result = await _sync_products_async(
                        tenant_id=tenant_id,
                        sync_recent_only=True,
                        max_products=100
                    )
                    results.append({
                        'tenant_id': tenant_id,
                        'result': result
                    })
                except Exception as e:
                    logger.error(f"租户 {tenant_id} 商品同步失败: {e}")
                    results.append({
                        'tenant_id': tenant_id,
                        'error': str(e)
                    })
            return results
        
        # 使用线程来隔离事件循环，避免连接池冲突
        # 这是最可靠的方法，因为每个线程有独立的事件循环
        result_container = {}
        exception_container = {}
        
        def run_in_thread():
            """在线程中运行异步任务"""
            # 在线程中创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                async def _sync_in_thread():
                    return await _sync_all_tenants()
                
                result_container['result'] = loop.run_until_complete(_sync_in_thread())
            except Exception as e:
                # 保存异常的类型和消息，确保可以被正确序列化
                import traceback
                exception_container['error_type'] = type(e).__name__
                exception_container['error_message'] = str(e)
                exception_container['error_traceback'] = traceback.format_exc()
                exception_container['error'] = e  # 保留原始异常用于日志
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
        
        # 在新线程中执行任务
        thread = threading.Thread(target=run_in_thread)
        thread.start()
        thread.join(timeout=300)  # 最多等待5分钟
        
        if thread.is_alive():
            logger.error("任务执行超时")
            raise TimeoutError("任务执行超时")
        
        if 'error' in exception_container:
            # 记录完整的异常信息
            error_type = exception_container.get('error_type', 'Exception')
            error_message = exception_container.get('error_message', 'Unknown error')
            error_traceback = exception_container.get('error_traceback', '')
            
            logger.error(f"任务执行失败: {error_type}: {error_message}")
            if error_traceback:
                logger.error(f"异常堆栈:\n{error_traceback}")
            
            # 重新抛出异常，确保 Celery 可以正确处理
            # 使用 RuntimeError 作为包装，确保异常类型可以被序列化
            raise RuntimeError(f"{error_type}: {error_message}") from exception_container.get('error')
        
        results = result_container.get('result', [])
        
        logger.info(f"每分钟商品同步任务完成: {results}")
        return {
            'status': '完成',
            'results': results
        }
        
    except Exception as e:
        logger.error(f"每分钟商品同步任务失败: {e}")
        raise


async def _sync_orders_async(
    tenant_id: int,
    query_filter: Optional[str] = None,
    max_orders: Optional[int] = None,
    sync_recent_only: bool = True,
    task=None
) -> Dict[str, Any]:
    """异步同步订单到 shopify_orders 表（步骤1：从 Shopify API 到本地 shopify_orders 表）"""
    
    # 获取数据库会话
    from app.core.database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        try:
            # 创建订单服务
            order_service = ShopifyOrderService(db)
            
            # 同步订单到 shopify_orders 表（不是直接到核心订单表）
            result = await order_service.sync_orders_to_shopify_table(
                tenant_id=tenant_id,
                query_filter=query_filter,
                max_orders=max_orders,
                sync_recent_only=sync_recent_only
            )
            
            # 更新任务进度
            if task:
                task.update_state(
                    state='PROGRESS',
                    meta={
                        'status': '同步完成',
                        'progress': 100,
                        'result': result
                    }
                )
            
            return result
            
        except Exception as e:
            logger.error(f"异步同步订单失败: {e}")
            await db.rollback()
            raise


async def _sync_products_async(
    tenant_id: int,
    query_filter: Optional[str] = None,
    max_products: Optional[int] = None,
    sync_recent_only: bool = True,
    task=None
) -> Dict[str, Any]:
    """异步同步商品的核心逻辑"""
    
    # 获取数据库会话
    from app.core.database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        try:
            # 创建商品服务
            product_service = ShopifyProductService(db)
            
            # 同步商品
            result = await product_service.sync_products(
                tenant_id=tenant_id,
                query_filter=query_filter,
                max_products=max_products,
                sync_recent_only=sync_recent_only
            )
            
            # 更新任务进度
            if task:
                task.update_state(
                    state='PROGRESS',
                    meta={
                        'status': '同步完成',
                        'progress': 100,
                        'result': result
                    }
                )
            
            return result
            
        except Exception as e:
            logger.error(f"异步同步商品失败: {e}")
            await db.rollback()
            raise


async def _fetch_orders_async(
    shop_name: str,
    access_token: str,
    query_filter: Optional[str] = None,
    max_orders: Optional[int] = None,
    task=None
) -> Dict[str, Any]:
    """异步获取订单的核心逻辑"""
    
    # 创建 Shopify 客户端
    client = create_shopify_client(shop_name, access_token)
    
    # 获取数据库会话
    db = next(get_sync_db())
    
    orders_count = 0
    saved_count = 0
    errors = []
    
    try:
        # 获取所有订单
        async for order_data in client.get_all_orders(
            query_filter=query_filter,
            max_orders=max_orders
        ):
            orders_count += 1
            
            try:
                # 转换为数据库模型
                order_create = _convert_shopify_order_to_schema(order_data)
                
                # 检查订单是否已存在
                existing_order = db.query(Order).filter(
                    Order.shopify_order_id == order_create.shopify_order_id
                ).first()
                
                if existing_order:
                    # 更新现有订单
                    for field, value in order_create.dict(exclude_unset=True).items():
                        setattr(existing_order, field, value)
                    logger.info(f"更新订单: {order_create.shopify_order_id}")
                else:
                    # 创建新订单
                    new_order = Order(**order_create.dict())
                    db.add(new_order)
                    logger.info(f"创建新订单: {order_create.shopify_order_id}")
                
                db.commit()
                saved_count += 1
                
            except Exception as e:
                logger.error(f"处理订单 {order_data.get('id')} 时出错: {e}")
                errors.append(f"订单 {order_data.get('id')}: {str(e)}")
                db.rollback()
            
            # 更新任务进度
            if task:
                progress = int((orders_count / (max_orders or 100)) * 100)
                task.update_state(
                    state='PROGRESS',
                    meta={
                        'status': f'已处理 {orders_count} 个订单',
                        'progress': progress,
                        'orders_count': orders_count,
                        'saved_count': saved_count
                    }
                )
        
        return {
            'orders_count': orders_count,
            'saved_count': saved_count,
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"获取订单失败: {e}")
        raise


def _convert_shopify_order_to_schema(order_data: Dict[str, Any]) -> OrderCreate:
    """将 Shopify 订单数据转换为 OrderCreate schema"""
    # 这个函数保持原有的实现，用于向后兼容
    # 新的实现已经在 ShopifyOrderService 中
    pass


@celery_app.task(name="fetch_recent_orders")
def fetch_recent_orders_task(shop_name: str, access_token: str, hours: int = 24):
    """获取最近几小时的订单"""
    query_filter = f"created_at:>={datetime.utcnow().isoformat()}T{24-hours}:00:00Z"
    
    return fetch_shopify_orders_task.delay(
        shop_name=shop_name,
        access_token=access_token,
        query_filter=query_filter
    )


@celery_app.task(name="fetch_unfulfilled_orders")
def fetch_unfulfilled_orders_task(shop_name: str, access_token: str):
    """获取未履约的订单"""
    return fetch_shopify_orders_task.delay(
        shop_name=shop_name,
        access_token=access_token,
        query_filter="fulfillment_status:unfulfilled"
    )


@celery_app.task(name="sync_all_orders")
def sync_all_orders_task(shop_name: str, access_token: str):
    """同步所有订单（用于初始数据导入）"""
    return fetch_shopify_orders_task.delay(
        shop_name=shop_name,
        access_token=access_token,
        max_orders=10000  # 限制最大数量避免过载
    )
