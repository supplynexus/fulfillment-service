"""
Shopify 相关的 Celery 异步任务
用于批量处理订单数据
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from celery import current_task
from sqlalchemy.orm import Session

from app.tasks.celery_app import celery_app
from app.core.database import get_sync_db
from app.services.shopify.client import create_shopify_client
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
    db = next(get_db())
    
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
            if task and orders_count % 10 == 0:
                progress = min(90, (orders_count / (max_orders or 1000)) * 100)
                task.update_state(
                    state='PROGRESS',
                    meta={
                        'status': f'已处理 {orders_count} 个订单',
                        'progress': progress,
                        'orders_saved': saved_count
                    }
                )
    
    finally:
        db.close()
    
    return {
        'orders_count': orders_count,
        'saved_count': saved_count,
        'errors': errors
    }


def _convert_shopify_order_to_schema(order_data: Dict[str, Any]) -> OrderCreate:
    """将 Shopify 订单数据转换为数据库模式"""
    
    # 提取基本信息
    shopify_id = order_data.get('id', '').split('/')[-1]  # 从 GID 中提取 ID
    
    # 提取价格信息
    total_price_data = order_data.get('totalPriceSet', {}).get('shopMoney', {})
    subtotal_price_data = order_data.get('subtotalPriceSet', {}).get('shopMoney', {})
    total_tax_data = order_data.get('totalTaxSet', {}).get('shopMoney', {})
    
    # 提取客户信息
    customer_data = order_data.get('customer', {})
    
    # 提取地址信息
    shipping_address = order_data.get('shippingAddress', {})
    billing_address = order_data.get('billingAddress', {})
    
    # 提取订单项
    line_items_data = order_data.get('lineItems', {}).get('edges', [])
    line_items = []
    for edge in line_items_data:
        item = edge.get('node', {})
        line_items.append({
            'shopify_line_item_id': item.get('id', '').split('/')[-1],
            'title': item.get('title'),
            'quantity': item.get('quantity'),
            'variant_title': item.get('variantTitle'),
            'vendor': item.get('vendor'),
            'sku': item.get('sku'),
            'product_id': item.get('productId'),
            'variant_id': item.get('variantId'),
            'price': float(item.get('originalUnitPriceSet', {}).get('shopMoney', {}).get('amount', '0')),
            'fulfillment_status': item.get('fulfillmentStatus')
        })
    
    return OrderCreate(
        shopify_order_id=shopify_id,
        order_name=order_data.get('name'),
        email=order_data.get('email'),
        phone=order_data.get('phone'),
        financial_status=order_data.get('displayFinancialStatus'),
        fulfillment_status=order_data.get('displayFulfillmentStatus'),
        total_price=float(total_price_data.get('amount', '0')),
        subtotal_price=float(subtotal_price_data.get('amount', '0')),
        total_tax=float(total_tax_data.get('amount', '0')),
        currency=total_price_data.get('currencyCode', 'USD'),
        
        # 客户信息
        customer_shopify_id=customer_data.get('id', '').split('/')[-1] if customer_data.get('id') else None,
        customer_email=customer_data.get('email'),
        customer_phone=customer_data.get('phone'),
        customer_name=customer_data.get('displayName'),
        
        # 地址信息
        shipping_address=shipping_address,
        billing_address=billing_address,
        
        # 其他信息
        note=order_data.get('note'),
        tags=order_data.get('tags', []),
        
        # 时间信息
        created_at=datetime.fromisoformat(order_data.get('createdAt', '').replace('Z', '+00:00')),
        updated_at=datetime.fromisoformat(order_data.get('updatedAt', '').replace('Z', '+00:00')),
        processed_at=datetime.fromisoformat(order_data.get('processedAt', '').replace('Z', '+00:00')) if order_data.get('processedAt') else None,
        
        # 订单项
        line_items=line_items
    )


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
