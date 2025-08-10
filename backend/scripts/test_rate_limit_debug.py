#!/usr/bin/env python3
"""
调试频率限制功能
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

async def test_rate_limit():
    """测试频率限制功能"""
    try:
        from app.core.health_auth import HealthCheckAuth
        from app.core.config import settings
        
        print("🔍 调试频率限制功能...")
        print("=" * 50)
        print(f"配置:")
        print(f"  HEALTH_CHECK_RATE_LIMIT: {settings.HEALTH_CHECK_RATE_LIMIT}")
        print(f"  HEALTH_CHECK_RATE_WINDOW: {settings.HEALTH_CHECK_RATE_WINDOW}")
        print(f"  REDIS_URL: {settings.REDIS_URL}")
        print()
        
        # 创建认证实例
        auth = HealthCheckAuth()
        
        # 测试 Redis 连接
        print("📡 测试 Redis 连接...")
        try:
            redis_client = await auth.get_redis_client()
            await redis_client.ping()
            print("✅ Redis 连接成功")
        except Exception as e:
            print(f"❌ Redis 连接失败: {e}")
            return
        
        # 测试频率限制
        print("\n🔒 测试频率限制...")
        identifier = "test:12345678"
        
        # 清理之前的测试数据
        await redis_client.delete(f"health_check_rate_limit:{identifier}")
        
        # 测试前10次（应该都成功）
        print("  测试前10次请求:")
        for i in range(1, 11):
            result = await auth.check_rate_limit(identifier)
            print(f"    请求 {i}: {'✅ 通过' if result else '❌ 被限制'}")
        
        # 测试第11次（应该被限制）
        print("\n  测试第11次请求:")
        result = await auth.check_rate_limit(identifier)
        print(f"    请求 11: {'✅ 通过' if result else '❌ 被限制'}")
        
        # 检查 Redis 中的数据
        print("\n📊 检查 Redis 中的数据:")
        count = await redis_client.zcard(f"health_check_rate_limit:{identifier}")
        print(f"  当前记录数: {count}")
        
        # 显示所有记录
        records = await redis_client.zrange(f"health_check_rate_limit:{identifier}", 0, -1, withscores=True)
        print(f"  记录详情: {records}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_rate_limit())
