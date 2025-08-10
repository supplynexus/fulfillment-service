#!/usr/bin/env python3
"""
环境配置文件设置脚本
用于在 backend/ 目录下创建 .env.local 文件
"""

import os
import shutil
from pathlib import Path

def setup_env_file():
    """设置环境配置文件"""
    backend_dir = Path(__file__).parent.parent
    env_local_path = backend_dir / ".env.local"
    env_example_path = backend_dir / ".env.example"
    
    # 检查是否已存在 .env.local
    if env_local_path.exists():
        print(f"⚠️  {env_local_path} 已存在，跳过创建")
        return
    
    # 创建 .env.example 文件
    env_example_content = """# =================================================================
# SupplyNexus Backend Environment Configuration
# =================================================================

# Application Settings
PROJECT_NAME="SupplyNexus Fulfillment Service"
ENVIRONMENT=development
SECRET_KEY=your-super-secret-key-change-this-in-production
API_V1_STR=/api/v1

# Database Configuration
DATABASE_URL=postgresql+asyncpg://supplynexus_admin:your-password@localhost:5433/supplynexus

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Shopify API Configuration
SHOPIFY_API_KEY=your-shopify-api-key
SHOPIFY_API_SECRET=your-shopify-api-secret
SHOPIFY_API_VERSION=2023-10

# Printify API Configuration
PRINTIFY_API_TOKEN=your-printify-api-token
PRINTIFY_API_BASE_URL=https://api.printify.com/v1

# Security Settings
WEBHOOK_SECRET=your-webhook-secret-for-shopify-and-printify
ACCESS_TOKEN_EXPIRE_MINUTES=10080  # 7 days
ALGORITHM=HS256

# CORS Settings
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
ALLOWED_HOSTS=localhost,127.0.0.1

# Monitoring (Optional)
SENTRY_DSN=your-sentry-dsn-for-error-tracking

# =================================================================
# Health Check Configuration (Required)
# =================================================================
# IMPORTANT: You MUST configure these values for security
HEALTH_CHECK_API_KEY=your-secure-health-check-api-key-here
HEALTH_CHECK_RATE_LIMIT=10  # Requests per minute
HEALTH_CHECK_RATE_WINDOW=60  # Time window in seconds

# =================================================================
# Production Environment Overrides
# =================================================================
# For production, update the following:
# - Change SECRET_KEY to a strong random key
# - Update DATABASE_URL to production database
# - Update REDIS_URL to production Redis
# - Set real Shopify and Printify API credentials
# - Configure proper ALLOWED_ORIGINS and ALLOWED_HOSTS
# - Set up Sentry DSN for error tracking
# - Generate a strong HEALTH_CHECK_API_KEY
"""
    
    # 创建 .env.local 文件（基于根目录的 environment.local）
    env_local_content = """# 本地开发环境配置
DATABASE_URL=postgresql+asyncpg://supplynexus_admin:IVzrm2bKlWyxWzhU3KVJUOdwU6IEwG32@localhost:5433/supplynexus
REDIS_URL=redis://localhost:6379/0

# Alembic 使用的同步数据库 URL  
DATABASE_URL_SYNC=postgresql://supplynexus_admin:IVzrm2bKlWyxWzhU3KVJUOdwU6IEwG32@localhost:5433/supplynexus

# API 密钥（开发环境）
SHOPIFY_API_KEY=dev-shopify-api-key
SHOPIFY_API_SECRET=dev-shopify-api-secret
PRINTIFY_API_TOKEN=dev-printify-api-token
WEBHOOK_SECRET=dev-webhook-secret

# JWT 配置
SECRET_KEY=dev-jwt-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALGORITHM=HS256

# 开发环境设置
ENVIRONMENT=development
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
ALLOWED_HOSTS=localhost,127.0.0.1

# 健康检查配置（重要：必须配置安全的 API Key）
HEALTH_CHECK_API_KEY=your-secure-health-check-api-key-here
HEALTH_CHECK_RATE_LIMIT=10
HEALTH_CHECK_RATE_WINDOW=60
"""
    
    try:
        # 写入 .env.example
        with open(env_example_path, 'w', encoding='utf-8') as f:
            f.write(env_example_content)
        print(f"✅ 创建了 {env_example_path}")
        
        # 写入 .env.local
        with open(env_local_path, 'w', encoding='utf-8') as f:
            f.write(env_local_content)
        print(f"✅ 创建了 {env_local_path}")
        
        print("\n📝 下一步操作：")
        print("1. 检查并修改 .env.local 中的配置")
        print("2. 生成并配置 HEALTH_CHECK_API_KEY（重要！）")
        print("3. 确保 SECRET_KEY 在生产环境中使用强密钥")
        print("4. 将 .env.local 添加到 .gitignore 中")
        
        print("\n🔐 安全提醒：")
        print("- HEALTH_CHECK_API_KEY 必须配置，不能使用缺省值")
        print("- 建议使用强随机密钥：openssl rand -hex 32")
        print("- 不同环境使用不同的 API Key")
        
    except Exception as e:
        print(f"❌ 创建环境文件时出错: {e}")

if __name__ == "__main__":
    setup_env_file()
