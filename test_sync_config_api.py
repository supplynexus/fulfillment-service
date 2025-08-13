#!/usr/bin/env python3
"""
测试同步配置API的脚本
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

from app.core.database import get_async_db
from app.models.external_system import ExternalSystem, ExternalSystemType
from app.models.sync_config import SyncConfig, SyncType, SyncFrequency
from sqlalchemy import select


async def test_sync_config_api():
    """测试同步配置API"""
    
    print("🧪 测试同步配置API...")
    
    async for db in get_async_db():
        try:
            # 1. 检查现有的外部系统
            print("\n1️⃣ 检查外部系统...")
            result = await db.execute(
                select(ExternalSystem).where(
                    ExternalSystem.tenant_id == 1,
                    ExternalSystem.system_type == ExternalSystemType.SHOPIFY
                )
            )
            shopify_system = result.scalar_one_or_none()
            
            if shopify_system:
                print(f"✅ 找到 Shopify 系统: {shopify_system.name}")
                print(f"  - ID: {shopify_system.id}")
                print(f"  - 类型: {shopify_system.system_type.value}")
                print(f"  - 是否激活: {shopify_system.is_active}")
            else:
                print("❌ 未找到 Shopify 系统")
                return
            
            # 2. 检查现有的同步配置
            print("\n2️⃣ 检查现有同步配置...")
            result = await db.execute(
                select(SyncConfig).where(
                    SyncConfig.tenant_id == 1
                )
            )
            existing_configs = result.scalars().all()
            
            if existing_configs:
                print(f"✅ 找到 {len(existing_configs)} 个同步配置:")
                for config in existing_configs:
                    print(f"  - {config.name} ({config.sync_type.value})")
                    print(f"    状态: {'启用' if config.is_active else '禁用'}")
                    print(f"    频率: {config.frequency.value}")
                    print(f"    总运行次数: {config.total_runs}")
            else:
                print("ℹ️ 暂无同步配置")
            
            # 3. 创建测试配置
            print("\n3️⃣ 创建测试同步配置...")
            
            # 检查是否已存在产品同步配置
            existing_product_config = await db.execute(
                select(SyncConfig).where(
                    SyncConfig.tenant_id == 1,
                    SyncConfig.external_system_id == shopify_system.id,
                    SyncConfig.sync_type == SyncType.PRODUCTS
                )
            )
            existing_product_config = existing_product_config.scalar_one_or_none()
            
            if existing_product_config:
                print(f"ℹ️ 产品同步配置已存在: {existing_product_config.name}")
                product_config = existing_product_config
            else:
                # 创建新的产品同步配置
                product_config = SyncConfig(
                    tenant_id=1,
                    external_system_id=shopify_system.id,
                    name="Shopify 产品同步",
                    sync_type=SyncType.PRODUCTS,
                    is_active=True,
                    frequency=SyncFrequency.HOURLY,
                    sync_params={
                        "incremental": True,
                        "max_products": 50
                    },
                    start_time=datetime.utcnow()
                )
                db.add(product_config)
                await db.commit()
                await db.refresh(product_config)
                print(f"✅ 创建产品同步配置: {product_config.name}")
            
            # 检查是否已存在订单同步配置
            existing_order_config = await db.execute(
                select(SyncConfig).where(
                    SyncConfig.tenant_id == 1,
                    SyncConfig.external_system_id == shopify_system.id,
                    SyncConfig.sync_type == SyncType.ORDERS
                )
            )
            existing_order_config = existing_order_config.scalar_one_or_none()
            
            if existing_order_config:
                print(f"ℹ️ 订单同步配置已存在: {existing_order_config.name}")
                order_config = existing_order_config
            else:
                # 创建新的订单同步配置
                order_config = SyncConfig(
                    tenant_id=1,
                    external_system_id=shopify_system.id,
                    name="Shopify 订单同步",
                    sync_type=SyncType.ORDERS,
                    is_active=True,
                    frequency=SyncFrequency.DAILY,
                    sync_params={
                        "incremental": True,
                        "max_orders": 100
                    },
                    start_time=datetime.utcnow() + timedelta(hours=1)
                )
                db.add(order_config)
                await db.commit()
                await db.refresh(order_config)
                print(f"✅ 创建订单同步配置: {order_config.name}")
            
            # 4. 显示所有配置
            print("\n4️⃣ 显示所有同步配置...")
            result = await db.execute(
                select(SyncConfig).where(
                    SyncConfig.tenant_id == 1
                ).order_by(SyncConfig.created_at)
            )
            all_configs = result.scalars().all()
            
            for config in all_configs:
                print(f"\n📋 配置: {config.name}")
                print(f"  - ID: {config.id}")
                print(f"  - 类型: {config.sync_type.value}")
                print(f"  - 频率: {config.frequency.value}")
                print(f"  - 状态: {'启用' if config.is_active else '禁用'}")
                print(f"  - 参数: {config.sync_params}")
                print(f"  - 开始时间: {config.start_time}")
                print(f"  - 下次运行: {config.next_run_at}")
                print(f"  - 总运行次数: {config.total_runs}")
                print(f"  - 成功次数: {config.successful_runs}")
                print(f"  - 失败次数: {config.failed_runs}")
                print(f"  - 处理项目数: {config.total_items_processed}")
            
            print("\n✅ 同步配置API测试完成!")
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            break


async def test_api_endpoints():
    """测试API端点（需要启动服务器）"""
    
    print("\n🌐 测试API端点...")
    print("注意: 需要先启动后端服务器 (python -m uvicorn app.main:app --reload)")
    
    # 这里可以添加实际的HTTP请求测试
    # 例如使用 httpx 或 requests 库
    
    print("📝 API端点列表:")
    print("  GET    /api/v1/sync-configs/                    - 获取同步配置列表")
    print("  POST   /api/v1/sync-configs/                    - 创建同步配置")
    print("  PUT    /api/v1/sync-configs/{config_id}         - 更新同步配置")
    print("  DELETE /api/v1/sync-configs/{config_id}         - 删除同步配置")
    print("  POST   /api/v1/sync-configs/{config_id}/trigger - 手动触发同步")
    print("  GET    /api/v1/sync-configs/{config_id}/jobs    - 获取同步任务历史")
    print("  GET    /api/v1/sync-configs/stats               - 获取同步统计信息")


if __name__ == "__main__":
    print("🚀 开始测试同步配置系统...")
    
    # 测试数据库操作
    asyncio.run(test_sync_config_api())
    
    # 测试API端点
    asyncio.run(test_api_endpoints())
    
    print("\n✨ 测试完成!")
