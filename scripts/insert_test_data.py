#!/usr/bin/env python3
"""
插入测试数据脚本
用于创建impeach租户和leo用户
"""

import asyncio
import asyncpg
import bcrypt


async def insert_test_data():
    """插入测试数据"""
    try:
        # 连接数据库
        conn = await asyncpg.connect(
            host='localhost',
            port=5433,
            user='supplynexus_admin',
            password='IVzrm2bKlWyxWzhU3KVJUOdwU6IEwG32',
            database='supplynexus'
        )
        
        # 1. 创建impeach租户
        print("1. 创建impeach租户...")
        await conn.execute("""
            INSERT INTO tenants (name, display_name, description, settings, is_active) 
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (name) DO NOTHING
        """, 'impeach', 'Impeach Store', 'Impeach online store tenant', '{}', True)
        
        # 2. 创建leo用户 (密码: leo123)
        print("2. 创建leo用户...")
        leo_password_hash = bcrypt.hashpw("leo123".encode(), bcrypt.gensalt()).decode()
        await conn.execute("""
            INSERT INTO users (email, hashed_password, full_name, is_active, is_superuser) 
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (email) DO NOTHING
        """, 'leo@impeach.com', leo_password_hash, 'Leo Chen', True, False)
        
        # 3. 创建frontend用户
        print("3. 创建frontend用户...")
        frontend_password_hash = bcrypt.hashpw("frontend123".encode(), bcrypt.gensalt()).decode()
        await conn.execute("""
            INSERT INTO users (email, hashed_password, full_name, is_active, is_superuser) 
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (email) DO NOTHING
        """, 'frontend@supplynexus.store', frontend_password_hash, 'Frontend Server', True, False)
        
        # 4. 创建leo和impeach的关联关系
        print("4. 创建用户-租户关联关系...")
        await conn.execute("""
            INSERT INTO user_tenants (user_id, tenant_id, role, is_active)
            SELECT 
                (SELECT id FROM users WHERE email = $1),
                (SELECT id FROM tenants WHERE name = $2),
                $3,
                $4
            ON CONFLICT DO NOTHING
        """, 'leo@impeach.com', 'impeach', 'OWNER', True)
        
        # 5. 插入frontend公钥
        print("5. 插入frontend公钥...")
        frontend_public_key = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAnFe1apracDJQOa1X3siF
Sfk47yPp2L2LvOpAb1I8ORMx3Sm6uIzyUP6HP/3V31Meqa10UsjyWN77HcsmCKaT
7V6pG0BlUNy4pLp92YreaO2ikApOQyi+j7Izgb1AAA5npe8a6L/4diAtLwDoiHYP
wKnB+i+72aYX2pkCOgkQgNZ3C+0UrYuGU+5m0cKsW+9oeStY2L7Ti7Z3IwehG7fC
C5TR0lDvr9+znJx3RimITr98Lg1rWBd59JgZ1RJTpUBgrSwQdk8z7cs1XqMDZoI0
Lf/vSYKnwt82skZH5UV1xuqcDMLIW84RvJlw6h7G09yRamIyyEJYiFrM6ciEoBFC
nwIDAQAB
-----END PUBLIC KEY-----"""
        
        await conn.execute("""
            INSERT INTO user_keys (user_id, key_id, public_key, key_type, name, description, is_active, is_primary)
            SELECT 
                (SELECT id FROM users WHERE email = $1),
                $2,
                $3,
                $4,
                $5,
                $6,
                $7,
                $8
            ON CONFLICT (key_id) DO NOTHING
        """, 'frontend@supplynexus.store', 'frontend-server-1', frontend_public_key, 'rsa', 
             'Frontend Server Key', 'Frontend server public key for API authentication', True, True)
        
        print("✅ 测试数据插入成功！")
        
        # 6. 验证插入结果
        print("\n📊 验证插入结果:")
        
        # 检查租户
        tenants = await conn.fetch("SELECT id, name, display_name FROM tenants")
        print(f"租户数量: {len(tenants)}")
        for tenant in tenants:
            print(f"  - {tenant['name']}: {tenant['display_name']}")
        
        # 检查用户
        users = await conn.fetch("SELECT id, email, full_name FROM users")
        print(f"用户数量: {len(users)}")
        for user in users:
            print(f"  - {user['email']}: {user['full_name']}")
        
        # 检查用户-租户关系
        relationships = await conn.fetch("""
            SELECT 
                u.email,
                t.name as tenant_name,
                ut.role
            FROM user_tenants ut
            JOIN users u ON ut.user_id = u.id
            JOIN tenants t ON ut.tenant_id = t.id
        """)
        print(f"用户-租户关系数量: {len(relationships)}")
        for rel in relationships:
            print(f"  - {rel['email']} -> {rel['tenant_name']} ({rel['role']})")
        
        # 检查frontend密钥
        keys = await conn.fetch("""
            SELECT 
                uk.key_id,
                uk.name,
                uk.is_active,
                uk.is_primary
            FROM user_keys uk
            JOIN users u ON uk.user_id = u.id
            WHERE u.email = $1
        """, 'frontend@supplynexus.store')
        print(f"Frontend密钥数量: {len(keys)}")
        for key in keys:
            print(f"  - {key['key_id']}: {key['name']} (active: {key['is_active']}, primary: {key['is_primary']})")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ 插入数据失败: {e}")
        raise


if __name__ == "__main__":
    print("🚀 开始插入测试数据...")
    asyncio.run(insert_test_data())
    print("✅ 完成！")
