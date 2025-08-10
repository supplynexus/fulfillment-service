#!/usr/bin/env python3
"""
健康检查测试脚本
用于测试新添加的健康检查端点
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

async def test_health_checks():
    """测试健康检查端点"""
    try:
        from app.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        print("🔍 测试健康检查端点...")
        print("=" * 50)
        
        # 测试基本健康检查
        print("1. 测试基本健康检查 /api/v1/health")
        response = client.get("/api/v1/health")
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
        print()
        
        # 测试数据库健康检查（需要 API Key）
        print("2. 测试数据库健康检查 /api/v1/health/db")
        print("   注意: 此端点需要 API Key 认证")
        response = client.get("/api/v1/health/db")
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
        print()
        
        # 测试 Redis 健康检查（需要 API Key）
        print("3. 测试 Redis 健康检查 /api/v1/health/redis")
        print("   注意: 此端点需要 API Key 认证")
        response = client.get("/api/v1/health/redis")
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
        print()
        
        # 测试完整健康检查（需要 API Key）
        print("4. 测试完整健康检查 /api/v1/health/full")
        print("   注意: 此端点需要 API Key 认证")
        response = client.get("/api/v1/health/full")
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
        print()
        
        # 测试带 API Key 的认证
        print("5. 测试带 API Key 的认证")
        from app.core.config import settings
        api_key = settings.HEALTH_CHECK_API_KEY
        if api_key:
            headers = {"X-API-Key": api_key}
            response = client.get("/api/v1/health/db", headers=headers)
            print(f"   状态码: {response.status_code}")
            print(f"   响应: {response.json()}")
        else:
            print("   ⚠️  HEALTH_CHECK_API_KEY 未配置")
        print()
        
        print("✅ 健康检查测试完成！")
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请确保已安装所有依赖: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    asyncio.run(test_health_checks())
