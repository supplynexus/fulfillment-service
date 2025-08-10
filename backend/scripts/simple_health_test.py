#!/usr/bin/env python3
"""
简单健康检查测试脚本
用于快速验证健康检查功能是否正常工作
"""

import requests
import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

def test_health_endpoints():
    """测试健康检查端点"""
    base_url = "http://localhost:8000"
    
    print("🔍 测试健康检查端点...")
    print("=" * 50)
    
    # 测试基本健康检查（无需认证）
    print("1. 测试基本健康检查 /api/v1/health")
    try:
        response = requests.get(f"{base_url}/api/v1/health", timeout=5)
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
        if response.status_code == 200:
            print("   ✅ 基本健康检查通过")
        else:
            print("   ❌ 基本健康检查失败")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
    print()
    
    # 测试需要认证的端点（应该返回 401）
    print("2. 测试需要认证的端点（无 API Key）")
    endpoints = ["/api/v1/health/db", "/api/v1/health/redis", "/api/v1/health/full"]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            print(f"   {endpoint}: {response.status_code}")
            if response.status_code == 401:
                print(f"   ✅ {endpoint} 正确返回 401（需要认证）")
            else:
                print(f"   ⚠️  {endpoint} 返回 {response.status_code}（预期 401）")
        except Exception as e:
            print(f"   ❌ {endpoint} 请求失败: {e}")
    print()
    
    # 测试带 API Key 的认证
    print("3. 测试带 API Key 的认证")
    api_key = "dev-health-check-api-key-123456"  # 开发环境默认值
    
    for endpoint in endpoints:
        try:
            headers = {"X-API-Key": api_key}
            response = requests.get(f"{base_url}{endpoint}", headers=headers, timeout=10)
            print(f"   {endpoint}: {response.status_code}")
            if response.status_code == 200:
                print(f"   ✅ {endpoint} 认证成功")
            elif response.status_code == 503:
                print(f"   ⚠️  {endpoint} 服务不可用（可能是数据库/Redis 未启动）")
            else:
                print(f"   ❌ {endpoint} 返回 {response.status_code}")
        except Exception as e:
            print(f"   ❌ {endpoint} 请求失败: {e}")
    print()
    
    print("✅ 健康检查测试完成！")
    print("\n📝 说明:")
    print("- 基本健康检查端点无需认证")
    print("- 详细健康检查端点需要 API Key 认证")
    print("- 如果返回 503，请检查数据库和 Redis 服务是否启动")

if __name__ == "__main__":
    test_health_endpoints()
