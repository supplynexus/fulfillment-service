#!/usr/bin/env python3
"""
测试应用配置脚本
"""

import os
import sys
import requests
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

def test_app_config():
    """测试应用配置"""
    print("🔍 测试应用配置...")
    print("=" * 50)
    
    # 检查应用是否运行
    try:
        response = requests.get("http://localhost:8000/api/v1/health", timeout=5)
        print(f"✅ 应用正在运行，状态码: {response.status_code}")
    except Exception as e:
        print(f"❌ 应用未运行: {e}")
        return
    
    # 测试配置加载
    print("\n📋 配置测试:")
    try:
        from app.core.config import settings
        print(f"   HEALTH_CHECK_API_KEY: {settings.HEALTH_CHECK_API_KEY}")
        print(f"   HEALTH_CHECK_RATE_LIMIT: {settings.HEALTH_CHECK_RATE_LIMIT}")
        print(f"   HEALTH_CHECK_RATE_WINDOW: {settings.HEALTH_CHECK_RATE_WINDOW}")
    except Exception as e:
        print(f"   ❌ 配置加载失败: {e}")
    
    # 测试 API Key 验证
    print("\n🔑 API Key 验证测试:")
    api_key = "dev-health-check-api-key-123456"
    
    try:
        from app.core.health_auth import HealthCheckAuth
        auth = HealthCheckAuth()
        result = auth.verify_api_key(api_key)
        print(f"   本地验证: {'✅ 有效' if result else '❌ 无效'}")
    except Exception as e:
        print(f"   本地验证失败: {e}")
    
    # 测试 HTTP 请求
    print("\n🌐 HTTP 请求测试:")
    headers = {"X-API-Key": api_key}
    
    try:
        response = requests.get("http://localhost:8000/api/v1/health/db", headers=headers, timeout=5)
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.text}")
        
        if response.status_code == 200:
            print("   ✅ API Key 认证成功")
        elif response.status_code == 401:
            print("   ❌ API Key 认证失败")
        else:
            print(f"   ⚠️  意外状态码: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")

if __name__ == "__main__":
    test_app_config()
