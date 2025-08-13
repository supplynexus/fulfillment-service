"""
Shopify 产品同步的 Celery 异步任务
用于批量同步产品数据，支持增量同步
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from celery import current_task
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.tasks.celery_app import celery_app
from app.core.database import get_sync_db, get_async_db
from app.services.shopify_product_service import ShopifyProductService
from app.services.product_mapper import ProductMapper
from app.models.external_system import ExternalSystem
from app.models.product import Product

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="sync_shopify_products")
def sync_shopify_products_task(
    self,
    tenant_id: int,
    incremental: bool = True,
    max_products: Optional[int] = None
):
    """
    同步 Shopify 产品的 Celery 任务
    
    Args:
        tenant_id: 租户 ID
        incremental: 是否增量同步（只同步更新过的产品）
        max_products: 最大产品数量限制
    """
    try:
        # 更新任务状态
        self.update_state(
            state='PROGRESS',
            meta={'status': '开始同步产品', 'progress': 0}
        )
        
        # 运行异步函数
        result = asyncio.run(_sync_products_async(
            tenant_id=tenant_id,
            incremental=incremental,
            max_products=max_products,
            task=self
        ))
        
        return {
            'status': '完成',
            'products_fetched': result['products_fetched'],
            'products_saved': result['products_saved'],
            'products_updated': result['products_updated'],
            'errors': result['errors'],
            'last_sync_time': result['last_sync_time'].isoformat() if result['last_sync_time'] else None
        }
        
    except Exception as e:
        logger.error(f"产品同步任务失败: {e}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise


async def _sync_products_async(
    tenant_id: int,
    incremental: bool = True,
    max_products: Optional[int] = None,
    task=None
) -> Dict[str, Any]:
    """异步同步产品的核心逻辑"""
    
    async for db in get_async_db():
        try:
            # 获取 Shopify 系统配置
            shopify_service = ShopifyProductService(db)
            shopify_system = await shopify_service.get_shopify_system(tenant_id)
            
            if not shopify_system:
                raise Exception(f"租户 {tenant_id} 的 Shopify 系统配置未找到")
            
            # 构建查询条件
            query_filter = None
            if incremental:
                # 获取上次同步时间
                last_sync_time = shopify_system.last_product_sync_at
                if last_sync_time:
                    # 转换为 Shopify 时间格式
                    shopify_time = last_sync_time.strftime("%Y-%m-%dT%H:%M:%SZ")
                    query_filter = f"updated_at:>={shopify_time}"
                    logger.info(f"增量同步，上次同步时间: {shopify_time}")
                else:
                    logger.info("首次同步，将同步所有产品")
            
            # 更新任务状态
            if task:
                task.update_state(
                    state='PROGRESS',
                    meta={'status': '正在获取产品数据', 'progress': 10}
                )
            
            # 获取产品数据
            products_fetched = 0
            products_saved = 0
            products_updated = 0
            errors = []
            
            # 分批获取产品
            limit = min(max_products or 50, 50)  # Shopify API 限制
            after = None
            
            while True:
                try:
                    # 获取产品列表
                    result = await shopify_service.fetch_products(
                        tenant_id=tenant_id,
                        limit=limit,
                        after=after,
                        query=query_filter
                    )
                    
                    products_data = result.get("data", {}).get("products", {})
                    products = products_data.get("nodes", [])
                    page_info = products_data.get("pageInfo", {})
                    
                    if not products:
                        break
                    
                    # 处理每个产品
                    for product_data in products:
                        products_fetched += 1
                        
                        try:
                            # 映射产品数据
                            mapped_product = ProductMapper.map_shopify_product(
                                product_data, tenant_id, shopify_system.id
                            )
                            
                            # 保存或更新产品
                            saved_product = await shopify_service._save_or_update_product(mapped_product)
                            
                            if saved_product:
                                products_saved += 1
                                logger.info(f"同步产品: {saved_product.title}")
                            
                        except Exception as e:
                            error_msg = f"处理产品 {product_data.get('title', 'Unknown')} 时出错: {e}"
                            logger.error(error_msg)
                            errors.append(error_msg)
                    
                    # 更新任务进度
                    if task:
                        progress = min(90, 10 + (products_fetched / (max_products or 1000)) * 80)
                        task.update_state(
                            state='PROGRESS',
                            meta={
                                'status': f'已处理 {products_fetched} 个产品',
                                'progress': progress,
                                'products_saved': products_saved
                            }
                        )
                    
                    # 检查是否还有更多页面
                    if not page_info.get("hasNextPage") or (max_products and products_fetched >= max_products):
                        break
                    
                    # 获取下一页的游标
                    after = page_info.get("endCursor")
                    
                except Exception as e:
                    error_msg = f"获取产品页面时出错: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    break
            
            # 更新外部系统的最后同步时间
            shopify_system.last_product_sync_at = datetime.utcnow()
            await db.commit()
            
            logger.info(f"产品同步完成: 获取 {products_fetched} 个，保存 {products_saved} 个")
            
            return {
                'products_fetched': products_fetched,
                'products_saved': products_saved,
                'products_updated': products_updated,
                'errors': errors,
                'last_sync_time': shopify_system.last_product_sync_at
            }
            
        except Exception as e:
            await db.rollback()
            logger.error(f"产品同步失败: {e}")
            raise
        finally:
            break


@celery_app.task(name="sync_shopify_products_incremental")
def sync_shopify_products_incremental_task(tenant_id: int):
    """增量同步 Shopify 产品（只同步更新过的产品）"""
    return sync_shopify_products_task.delay(
        tenant_id=tenant_id,
        incremental=True
    )


@celery_app.task(name="sync_shopify_products_full")
def sync_shopify_products_full_task(tenant_id: int):
    """全量同步 Shopify 产品（同步所有产品）"""
    return sync_shopify_products_task.delay(
        tenant_id=tenant_id,
        incremental=False
    )


@celery_app.task(name="sync_shopify_products_recent")
def sync_shopify_products_recent_task(tenant_id: int, hours: int = 24):
    """同步最近几小时更新的产品"""
    # 计算时间范围
    since_time = datetime.utcnow() - timedelta(hours=hours)
    
    # 这里可以添加自定义的时间过滤逻辑
    return sync_shopify_products_task.delay(
        tenant_id=tenant_id,
        incremental=True
    )


@celery_app.task(name="sync_all_tenants_products")
def sync_all_tenants_products_task(incremental: bool = True):
    """同步所有租户的产品"""
    async def _sync_all_tenants():
        async for db in get_async_db():
            try:
                # 获取所有 Shopify 系统
                result = await db.execute(
                    select(ExternalSystem).where(
                        ExternalSystem.system_type == "SHOPIFY",
                        ExternalSystem.is_active == True
                    )
                )
                shopify_systems = result.scalars().all()
                
                tasks = []
                for system in shopify_systems:
                    task = sync_shopify_products_task.delay(
                        tenant_id=system.tenant_id,
                        incremental=incremental
                    )
                    tasks.append(task)
                
                return {
                    'status': '已启动所有租户的产品同步任务',
                    'tenant_count': len(shopify_systems),
                    'task_ids': [task.id for task in tasks]
                }
                
            except Exception as e:
                logger.error(f"启动所有租户同步任务失败: {e}")
                raise
            finally:
                break
    
    return asyncio.run(_sync_all_tenants())


# 定时任务 - 每小时增量同步
@celery_app.task(name="schedule_shopify_products_sync")
def schedule_shopify_products_sync_task():
    """定时任务：每小时同步所有租户的产品"""
    return sync_all_tenants_products_task.delay(incremental=True)


# 定时任务 - 每天全量同步
@celery_app.task(name="schedule_shopify_products_full_sync")
def schedule_shopify_products_full_sync_task():
    """定时任务：每天全量同步所有租户的产品"""
    return sync_all_tenants_products_task.delay(incremental=False)
