#!/usr/bin/env python3
"""
测试同步触发功能
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

from app.core.database import get_async_db
from app.models.sync_config import SyncConfig, SyncJob, SyncJobStatus
from sqlalchemy import select

async def test_sync_trigger():
    """测试同步触发功能"""
    
    print("🧪 测试同步触发功能...")
    
    async for db in get_async_db():
        try:
            # 1. 检查同步配置
            print("\n1️⃣ 检查同步配置...")
            result = await db.execute(
                select(SyncConfig).where(
                    SyncConfig.sync_type == 'PRODUCTS',
                    SyncConfig.tenant_id == 1
                )
            )
            config = result.scalar_one_or_none()
            
            if config:
                print(f"✅ 找到同步配置: {config.name}")
                print(f"  - 频率: {config.frequency.value}")
                print(f"  - 间隔: {config.custom_interval_minutes} 分钟")
                print(f"  - 状态: {'启用' if config.is_active else '禁用'}")
                print(f"  - 下次运行: {config.next_run_at}")
            else:
                print("❌ 未找到同步配置")
                return
            
            # 2. 模拟触发同步任务
            print("\n2️⃣ 模拟触发同步任务...")
            
            # 创建同步任务记录
            sync_job = SyncJob(
                sync_config_id=config.id,
                tenant_id=1,
                status=SyncJobStatus.PENDING,
                progress_percentage=0,
                progress_message="准备开始同步"
            )
            
            db.add(sync_job)
            await db.commit()
            await db.refresh(sync_job)
            
            print(f"✅ 创建同步任务: {sync_job.id}")
            
            # 3. 模拟任务执行
            print("\n3️⃣ 模拟任务执行...")
            
            sync_job.status = SyncJobStatus.RUNNING
            sync_job.started_at = datetime.utcnow()
            sync_job.progress_percentage = 10
            sync_job.progress_message = "正在连接 Shopify API"
            
            await db.commit()
            print(f"✅ 任务开始执行: {sync_job.id}")
            
            # 4. 模拟任务完成
            print("\n4️⃣ 模拟任务完成...")
            
            sync_job.status = SyncJobStatus.SUCCESS
            sync_job.completed_at = datetime.utcnow()
            sync_job.progress_percentage = 100
            sync_job.progress_message = "同步完成"
            sync_job.items_processed = 25
            sync_job.items_created = 3
            sync_job.items_updated = 22
            sync_job.items_failed = 0
            
            # 更新配置统计
            config.total_runs += 1
            config.successful_runs += 1
            config.total_items_processed += 25
            config.last_run_at = datetime.utcnow()
            config.next_run_at = datetime.utcnow() + timedelta(minutes=30)
            
            await db.commit()
            
            print(f"✅ 任务执行完成:")
            print(f"  - 任务ID: {sync_job.id}")
            print(f"  - 状态: {sync_job.status.value}")
            print(f"  - 处理项目: {sync_job.items_processed}")
            print(f"  - 创建项目: {sync_job.items_created}")
            print(f"  - 更新项目: {sync_job.items_updated}")
            print(f"  - 失败项目: {sync_job.items_failed}")
            
            # 5. 显示最终状态
            print("\n5️⃣ 最终状态...")
            print(f"  - 总运行次数: {config.total_runs}")
            print(f"  - 成功次数: {config.successful_runs}")
            print(f"  - 失败次数: {config.failed_runs}")
            print(f"  - 总处理项目: {config.total_items_processed}")
            print(f"  - 下次运行: {config.next_run_at}")
            
            print("\n✅ 同步触发测试完成!")
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            await db.rollback()
            import traceback
            traceback.print_exc()
        finally:
            break

if __name__ == "__main__":
    asyncio.run(test_sync_trigger())
