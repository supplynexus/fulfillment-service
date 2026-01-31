#!/usr/bin/env python3
"""
完全重新同步脚本
用于手动触发Shopify订单和商品的完全重新同步
"""

import asyncio
import logging
import argparse
from datetime import datetime
from typing import Optional

from app.core.database import AsyncSessionLocal
from app.services.shopify.order_service import ShopifyOrderService
from app.services.shopify.product_service import ShopifyProductService
from app.models.external_system import ExternalSystem, ExternalSystemType
from sqlalchemy import select

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def get_active_tenants() -> list[int]:
    """获取所有活跃的租户ID"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ExternalSystem.tenant_id)
            .where(
                ExternalSystem.system_type == ExternalSystemType.SHOPIFY,
                ExternalSystem.is_active == True
            )
            .distinct()
        )
        tenant_ids = result.scalars().all()
        return list(tenant_ids)


async def full_sync_orders(tenant_id: int, max_orders: Optional[int] = None) -> dict:
    """完全重新同步订单"""
    logger.info(f"🔄 开始完全重新同步订单 (tenant_id: {tenant_id})")
    
    async with AsyncSessionLocal() as db:
        order_service = ShopifyOrderService(db)
        
        start_time = datetime.now()
        result = await order_service.sync_orders(
            tenant_id=tenant_id,
            sync_recent_only=False,  # 完全重新同步
            max_orders=max_orders
        )
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"✅ 订单同步完成 (tenant_id: {tenant_id})")
        logger.info(f"   耗时: {duration:.2f} 秒")
        logger.info(f"   获取: {result.get('orders_fetched', 0)} 个订单")
        logger.info(f"   新增: {result.get('orders_saved', 0)} 个订单")
        logger.info(f"   更新: {result.get('orders_updated', 0)} 个订单")
        logger.info(f"   错误: {len(result.get('errors', []))} 个")
        
        if result.get('errors'):
            for error in result['errors'][:5]:  # 只显示前5个错误
                logger.error(f"   ❌ {error}")
            if len(result['errors']) > 5:
                logger.error(f"   ... 还有 {len(result['errors']) - 5} 个错误")
        
        return result


async def full_sync_products(tenant_id: int, max_products: Optional[int] = None) -> dict:
    """完全重新同步商品"""
    logger.info(f"🔄 开始完全重新同步商品 (tenant_id: {tenant_id})")
    
    async with AsyncSessionLocal() as db:
        product_service = ShopifyProductService(db)
        
        start_time = datetime.now()
        result = await product_service.sync_products(
            tenant_id=tenant_id,
            sync_recent_only=False,  # 完全重新同步
            max_products=max_products
        )
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"✅ 商品同步完成 (tenant_id: {tenant_id})")
        logger.info(f"   耗时: {duration:.2f} 秒")
        logger.info(f"   获取: {result.get('products_fetched', 0)} 个商品")
        logger.info(f"   新增: {result.get('products_saved', 0)} 个商品")
        logger.info(f"   更新: {result.get('products_updated', 0)} 个商品")
        logger.info(f"   错误: {len(result.get('errors', []))} 个")
        
        if result.get('errors'):
            for error in result['errors'][:5]:  # 只显示前5个错误
                logger.error(f"   ❌ {error}")
            if len(result['errors']) > 5:
                logger.error(f"   ... 还有 {len(result['errors']) - 5} 个错误")
        
        return result


async def full_resync_all(
    sync_orders: bool = True,
    sync_products: bool = True,
    max_orders: Optional[int] = None,
    max_products: Optional[int] = None,
    tenant_id: Optional[int] = None
):
    """完全重新同步所有数据"""
    logger.info("🚀 开始完全重新同步")
    logger.info(f"   同步订单: {sync_orders}")
    logger.info(f"   同步商品: {sync_products}")
    logger.info(f"   最大订单数: {max_orders or '无限制'}")
    logger.info(f"   最大商品数: {max_products or '无限制'}")
    
    # 获取租户列表
    if tenant_id:
        tenant_ids = [tenant_id]
        logger.info(f"   指定租户: {tenant_id}")
    else:
        tenant_ids = await get_active_tenants()
        logger.info(f"   活跃租户: {tenant_ids}")
    
    if not tenant_ids:
        logger.error("❌ 未找到活跃的租户")
        return
    
    total_start_time = datetime.now()
    
    for tenant_id in tenant_ids:
        logger.info(f"\n📋 处理租户 {tenant_id}")
        
        # 同步订单
        if sync_orders:
            try:
                await full_sync_orders(tenant_id, max_orders)
            except Exception as e:
                logger.error(f"❌ 租户 {tenant_id} 订单同步失败: {e}")
        
        # 同步商品
        if sync_products:
            try:
                await full_sync_products(tenant_id, max_products)
            except Exception as e:
                logger.error(f"❌ 租户 {tenant_id} 商品同步失败: {e}")
    
    total_end_time = datetime.now()
    total_duration = (total_end_time - total_start_time).total_seconds()
    
    logger.info(f"\n🎉 完全重新同步完成")
    logger.info(f"   总耗时: {total_duration:.2f} 秒")
    logger.info(f"   处理租户: {len(tenant_ids)} 个")


def main():
    parser = argparse.ArgumentParser(description="完全重新同步Shopify数据")
    parser.add_argument(
        "--orders", 
        action="store_true", 
        help="同步订单"
    )
    parser.add_argument(
        "--products", 
        action="store_true", 
        help="同步商品"
    )
    parser.add_argument(
        "--all", 
        action="store_true", 
        help="同步订单和商品（默认）"
    )
    parser.add_argument(
        "--max-orders", 
        type=int, 
        help="最大订单数量"
    )
    parser.add_argument(
        "--max-products", 
        type=int, 
        help="最大商品数量"
    )
    parser.add_argument(
        "--tenant-id", 
        type=int, 
        help="指定租户ID"
    )
    
    args = parser.parse_args()
    
    # 默认同步所有
    if not args.orders and not args.products and not args.all:
        args.all = True
    
    if args.all:
        args.orders = True
        args.products = True
    
    asyncio.run(full_resync_all(
        sync_orders=args.orders,
        sync_products=args.products,
        max_orders=args.max_orders,
        max_products=args.max_products,
        tenant_id=args.tenant_id
    ))


if __name__ == "__main__":
    main()
