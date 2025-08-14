#!/usr/bin/env python3
"""
检查产品状态和同步配置
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_async_db
from app.models.product import Product
from app.models.sync_config import SyncConfig
from sqlalchemy import select
from datetime import datetime, timezone

async def check_status():
    async for db in get_async_db():
        try:
            # 检查产品状态
            result = await db.execute(
                select(Product).where(Product.external_id == '8127207866468')
            )
            product = result.scalar_one_or_none()
            
            if product:
                print(f"产品状态:")
                print(f"  ID: {product.id}")
                print(f"  标题: {product.title}")
                print(f"  描述: {product.description}")
                print(f"  最后同步: {product.last_synced_at}")
                print(f"  创建时间: {product.created_at}")
                print(f"  更新时间: {product.updated_at}")
            else:
                print("未找到产品 8127207866468")
            
            # 检查同步配置
            result = await db.execute(
                select(SyncConfig).where(
                    SyncConfig.sync_type == "PRODUCTS",
                    SyncConfig.is_active == True
                )
            )
            configs = result.scalars().all()
            
            print(f"\n同步配置:")
            for config in configs:
                print(f"  ID: {config.id}")
                print(f"  租户ID: {config.tenant_id}")
                print(f"  频率: {config.frequency}")
                print(f"  自定义间隔: {config.custom_interval_minutes} 分钟")
                print(f"  最后运行: {config.last_run_at}")
                print(f"  下次运行: {config.next_run_at}")
                print(f"  总运行次数: {config.total_runs}")
                print(f"  是否激活: {config.is_active}")
                print("  ---")
            
            # 检查当前时间
            now = datetime.now(timezone.utc)
            print(f"\n当前时间 (UTC): {now}")
            
        except Exception as e:
            print(f"错误: {e}")
        finally:
            break

if __name__ == "__main__":
    asyncio.run(check_status())
