#!/usr/bin/env python3
"""
更新租户公钥的简单脚本
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings

async def update_tenant_public_key():
    """更新租户公钥"""
    
    # 读取公钥文件
    public_key_path = "../frontend/keys/tenant_public_key.pem"
    with open(public_key_path, 'r') as f:
        public_key = f.read()
    
    print(f"🔑 读取公钥文件: {public_key_path}")
    print(f"📄 公钥内容: {public_key[:100]}...")
    
    # 创建数据库连接
    engine = create_engine(settings.DATABASE_URL.replace("+asyncpg", ""))
    
    with engine.connect() as conn:
        # 更新租户公钥
        result = conn.execute(text("""
            UPDATE tenants 
            SET public_key = :public_key,
                key_type = 'rsa',
                key_size = 2048
            WHERE name = 'impeach'
        """), {"public_key": public_key})
        
        conn.commit()
        
        print(f"✅ 租户公钥更新成功")
        
        # 验证更新
        result = conn.execute(text("""
            SELECT name, key_type, key_size, 
                   CASE WHEN public_key IS NOT NULL THEN '已设置' ELSE '未设置' END as key_status
            FROM tenants 
            WHERE name = 'impeach'
        """))
        
        row = result.fetchone()
        if row:
            print(f"📊 租户信息:")
            print(f"   名称: {row[0]}")
            print(f"   密钥类型: {row[1]}")
            print(f"   密钥大小: {row[2]} bits")
            print(f"   公钥状态: {row[3]}")

if __name__ == "__main__":
    asyncio.run(update_tenant_public_key())
