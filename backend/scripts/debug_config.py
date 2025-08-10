#!/usr/bin/env python3
"""
调试配置加载脚本
"""

import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

def debug_config():
    """调试配置加载"""
    print("🔍 调试配置加载...")
    print("=" * 50)
    
    # 检查环境变量
    print("1. 环境变量检查:")
    print(f"   ENV_FILE: {os.getenv('ENV_FILE', 'Not set')}")
    print(f"   HEALTH_CHECK_API_KEY: {os.getenv('HEALTH_CHECK_API_KEY', 'Not set')}")
    print()
    
    # 检查配置文件
    print("2. 配置文件检查:")
    env_files = [
        "../environment.local",
        ".env",
        "../environment.example"
    ]
    
    for env_file in env_files:
        if os.path.exists(env_file):
            print(f"   ✅ {env_file} 存在")
            with open(env_file, 'r') as f:
                content = f.read()
                if "HEALTH_CHECK_API_KEY" in content:
                    print(f"   ✅ {env_file} 包含 HEALTH_CHECK_API_KEY")
                else:
                    print(f"   ❌ {env_file} 不包含 HEALTH_CHECK_API_KEY")
        else:
            print(f"   ❌ {env_file} 不存在")
    print()
    
    # 尝试加载配置
    print("3. 配置加载测试:")
    try:
        from app.core.config import settings
        print(f"   ✅ 配置加载成功")
        print(f"   HEALTH_CHECK_API_KEY: {settings.HEALTH_CHECK_API_KEY}")
        print(f"   HEALTH_CHECK_RATE_LIMIT: {settings.HEALTH_CHECK_RATE_LIMIT}")
        print(f"   HEALTH_CHECK_RATE_WINDOW: {settings.HEALTH_CHECK_RATE_WINDOW}")
    except Exception as e:
        print(f"   ❌ 配置加载失败: {e}")
    print()
    
    # 测试 API Key 验证
    print("4. API Key 验证测试:")
    try:
        from app.core.health_auth import HealthCheckAuth
        auth = HealthCheckAuth()
        
        test_key = "dev-health-check-api-key-123456"
        result = auth.verify_api_key(test_key)
        print(f"   测试 API Key '{test_key}': {'✅ 有效' if result else '❌ 无效'}")
        
        wrong_key = "wrong-key"
        result = auth.verify_api_key(wrong_key)
        print(f"   错误 API Key '{wrong_key}': {'✅ 有效' if result else '❌ 无效'}")
        
    except Exception as e:
        print(f"   ❌ API Key 验证测试失败: {e}")

if __name__ == "__main__":
    debug_config()
