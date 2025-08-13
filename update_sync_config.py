#!/usr/bin/env python3
"""
更新同步配置为30分钟间隔
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

from app.core.database import get_async_db
from app.models.sync_config import SyncConfig, SyncFrequency
from sqlalchemy import select

async def update_sync_config():
    """更新同步配置为30分钟间隔"""
    
    print("🔄 更新同步配置为30分钟间隔...")
    
    async for db in get_async_db():
        try:
            # 获取产品同步配置
            result = await db.execute(
                select(SyncConfig).where(
                    SyncConfig.sync_type == 'PRODUCTS',
                    SyncConfig.tenant_id == 1
                )
            )
            config = result.scalar_one_or_none()
            
            if config:
                print(f"📋 当前配置: {config.name}")
                print(f"  - 频率: {config.frequency.value}")
                print(f"  - 间隔: {config.custom_interval_minutes} 分钟")
                
                # 更新配置
                config.frequency = SyncFrequency.CUSTOM
                config.custom_interval_minutes = 30
                config.name = 'Shopify 产品同步 (30分钟)'
                config.sync_params = {
                    'incremental': True,
                    'max_products': 50
                }
                config.next_run_at = datetime.utcnow() + timedelta(minutes=30)
                
                await db.commit()
                
                print(f"✅ 配置已更新:")
                print(f"  - 名称: {config.name}")
                print(f"  - 频率: {config.frequency.value}")
                print(f"  - 间隔: {config.custom_interval_minutes} 分钟")
                print(f"  - 下次运行: {config.next_run_at}")
                print(f"  - 参数: {config.sync_params}")
                
            else:
                print("❌ 未找到产品同步配置")
                
        except Exception as e:
            print(f"❌ 更新失败: {e}")
            await db.rollback()
            import traceback
            traceback.print_exc()
        finally:
            break

if __name__ == "__main__":
    asyncio.run(update_sync_config())
