#!/usr/bin/env python3
"""
测试 Shopify 订单同步功能
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.services.shopify.order_service import ShopifyOrderService

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 数据库连接
engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def test_order_sync():
    """测试订单同步功能"""
    print("🚀 开始测试 Shopify 订单同步功能...")
    
    async with AsyncSessionLocal() as db:
        # 创建订单服务
        order_service = ShopifyOrderService(db)
        
        # 测试获取凭据
        print("📡 测试获取 Shopify 凭据...")
        credentials = await order_service.get_shopify_credentials(tenant_id=1)
        
        if credentials:
            print(f"✅ 成功获取凭据: {list(credentials.keys())}")
        else:
            print("❌ 无法获取凭据，使用默认配置")
        
        # 测试同步订单
        print("📦 测试同步订单...")
        result = await order_service.sync_orders(
            tenant_id=1,
            sync_recent_only=True,
            max_orders=10
        )
        
        print(f"📋 同步结果: {result}")
        
        if result['success']:
            print(f"✅ 同步成功!")
            print(f"   - 获取订单数: {result['orders_fetched']}")
            print(f"   - 保存订单数: {result['orders_saved']}")
            print(f"   - 更新订单数: {result['orders_updated']}")
            print(f"   - 错误数: {len(result['errors'])}")
        else:
            print(f"❌ 同步失败: {result.get('error')}")
        
        # 测试获取最近订单
        print("📋 测试获取最近订单...")
        recent_orders = await order_service.get_recent_orders(
            tenant_id=1,
            hours=24,
            limit=5
        )
        
        print(f"📋 找到 {len(recent_orders)} 个最近订单:")
        for order in recent_orders:
            print(f"   - {order.external_order_name} ({order.status}) - ¥{order.total_amount}")
        
        # 测试根据状态获取订单
        print("📋 测试根据状态获取订单...")
        pending_orders = await order_service.get_orders_by_status(
            tenant_id=1,
            status="pending",
            limit=5
        )
        
        print(f"📋 找到 {len(pending_orders)} 个待处理订单:")
        for order in pending_orders:
            print(f"   - {order.external_order_name} - ¥{order.total_amount}")


async def test_celery_task():
    """测试 Celery 任务"""
    print("🔄 测试 Celery 任务...")
    
    from app.tasks.shopify_tasks import sync_shopify_orders_task
    
    # 启动任务
    task = sync_shopify_orders_task.delay(
        tenant_id=1,
        sync_recent_only=True,
        max_orders=5
    )
    
    print(f"📋 任务已启动: {task.id}")
    
    # 等待任务完成
    result = task.get(timeout=60)
    print(f"📋 任务结果: {result}")


async def main():
    """主函数"""
    print("🧪 Shopify 订单同步功能测试")
    print("=" * 50)
    
    try:
        # 测试订单同步
        await test_order_sync()
        
        print("\n" + "=" * 50)
        
        # 测试 Celery 任务
        await test_celery_task()
        
        print("\n✅ 所有测试完成!")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
