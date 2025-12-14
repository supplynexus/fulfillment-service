"""
检查 Shopify 订单同步状态
用于诊断为什么新订单没有被同步
"""
import sys
import os
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
from app.core.database import AsyncSessionLocal
from app.services.shopify.order_service import ShopifyOrderService
from app.models.order import Order
from sqlalchemy import select, func

async def check_sync_status(tenant_id: int = 1, order_number: str = None):
    """检查同步状态"""
    async with AsyncSessionLocal() as db:
        order_service = ShopifyOrderService(db)
        
        print(f"\n{'='*60}")
        print(f"Shopify 订单同步状态检查")
        print(f"{'='*60}\n")
        
        # 1. 检查数据库中的最新订单
        result = await db.execute(
            select(Order)
            .where(Order.tenant_id == tenant_id)
            .order_by(Order.updated_at.desc())
            .limit(5)
        )
        latest_orders = result.scalars().all()
        
        print(f"📦 数据库中的最新订单（租户 {tenant_id}）:")
        if latest_orders:
            for order in latest_orders:
                print(f"  - 订单号: {order.order_number or order.external_order_number}")
                print(f"    外部ID: {order.external_order_id}")
                print(f"    更新时间: {order.updated_at}")
                print(f"    创建时间: {order.created_at}")
                print()
        else:
            print("  ⚠️ 没有找到订单\n")
        
        # 2. 检查智能同步时间戳
        since_time = await order_service._get_smart_sync_timestamp(tenant_id, buffer_minutes=5)
        print(f"⏰ 智能同步时间戳: {since_time.isoformat()}")
        print(f"   时间范围: 从 {since_time.isoformat()} 到现在")
        print(f"   当前时间: {datetime.utcnow().isoformat()}")
        print()
        
        # 3. 如果指定了订单号，检查该订单是否存在
        if order_number:
            result = await db.execute(
                select(Order).where(
                    Order.tenant_id == tenant_id,
                    (Order.order_number == order_number) | 
                    (Order.external_order_number == order_number)
                )
            )
            order = result.scalar_one_or_none()
            if order:
                print(f"✅ 找到订单 {order_number}:")
                print(f"   ID: {order.id}")
                print(f"   外部ID: {order.external_order_id}")
                print(f"   更新时间: {order.updated_at}")
                print(f"   创建时间: {order.created_at}")
            else:
                print(f"❌ 未找到订单 {order_number}")
                print(f"   该订单可能还没有被同步")
            print()
        
        # 4. 检查 Shopify 凭据
        credentials = await order_service.get_shopify_credentials(tenant_id)
        if credentials:
            print(f"✅ Shopify 凭据已配置")
            print(f"   店铺: {credentials.get('store_url', 'N/A')}")
        else:
            print(f"❌ Shopify 凭据未配置")
        print()
        
        # 5. 建议手动同步
        print(f"💡 建议:")
        print(f"   1. 检查 Celery Beat 是否正在运行")
        print(f"   2. 检查 Celery Worker 是否正在运行")
        print(f"   3. 如果订单创建时间早于同步时间戳，可能需要手动触发全量同步")
        print(f"   4. 使用 API: POST /api/v1/orders/sync/full 进行全量同步")
        print()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="检查 Shopify 订单同步状态")
    parser.add_argument("--tenant-id", type=int, default=1, help="租户 ID")
    parser.add_argument("--order-number", type=str, help="要检查的订单号（如 1027）")
    args = parser.parse_args()
    
    asyncio.run(check_sync_status(args.tenant_id, args.order_number))

