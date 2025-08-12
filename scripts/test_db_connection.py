#!/usr/bin/env python3
"""
简单的数据库连接测试脚本
"""

import asyncio
import asyncpg

async def test_connection():
    """测试数据库连接"""
    try:
        # 连接数据库
        conn = await asyncpg.connect(
            host='localhost',
            port=5433,
            user='supplynexus_admin',
            password='IVzrm2bKlWyxWzhU3KVJUOdwU6IEwG32',
            database='supplynexus'
        )
        
        print("✅ 数据库连接成功！")
        
        # 测试查询
        result = await conn.fetchval("SELECT 1")
        print(f"✅ 查询测试成功: {result}")
        
        # 检查tenants表
        count = await conn.fetchval("SELECT COUNT(*) FROM tenants")
        print(f"✅ tenants表记录数: {count}")
        
        # 尝试插入数据
        await conn.execute("""
            INSERT INTO tenants (name, display_name, settings) 
            VALUES ($1, $2, $3)
        """, 'impeach', 'Impeach Store', '{}')
        
        print("✅ 数据插入成功！")
        
        # 验证插入
        count = await conn.fetchval("SELECT COUNT(*) FROM tenants")
        print(f"✅ 插入后tenants表记录数: {count}")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
