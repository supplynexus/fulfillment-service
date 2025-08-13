#!/usr/bin/env python3
"""
将同步配置改为1分钟间隔（用于测试）
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

from app.core.database import get_async_db
from app.models.sync_config import SyncConfig
from sqlalchemy import select

async def update_sync_to_1min():
    """将同步配置改为1分钟间隔"""
    
    print("🔄 更新同步配置为1分钟间隔（测试用）...")
    
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
                print(f"  - 间隔: {config.custom_interval_minutes} 分钟")
                print(f"  - 下次运行: {config.next_run_at}")
                
                # 更新配置
                config.custom_interval_minutes = 1
                config.name = 'Shopify 产品同步 (1分钟测试)'
                config.next_run_at = datetime.utcnow() + timedelta(minutes=1)
                
                await db.commit()
                
                print(f"✅ 配置已更新:")
                print(f"  - 名称: {config.name}")
                print(f"  - 间隔: {config.custom_interval_minutes} 分钟")
                print(f"  - 下次运行: {config.next_run_at}")
                print(f"  - 频率: {config.frequency.value}")
                
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
    asyncio.run(update_sync_to_1min())
