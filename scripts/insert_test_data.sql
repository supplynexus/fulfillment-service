-- 插入测试数据脚本
-- 用于创建impeach租户和leo用户

-- 1. 创建impeach租户
INSERT INTO tenants (name, display_name, description, settings, is_active) 
VALUES ('impeach', 'Impeach Store', 'Impeach online store tenant', '{}', true)
ON CONFLICT (name) DO NOTHING;

-- 2. 创建leo用户 (密码: leo123)
INSERT INTO users (email, hashed_password, full_name, is_active, is_superuser) 
VALUES ('leo@impeach.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3bp.gSJmWi', 'Leo Chen', true, false)
ON CONFLICT (email) DO NOTHING;

-- 3. 创建frontend用户 (用于存储frontend公钥)
INSERT INTO users (email, hashed_password, full_name, is_active, is_superuser) 
VALUES ('frontend@supplynexus.store', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3bp.gSJmWi', 'Frontend Server', true, false)
ON CONFLICT (email) DO NOTHING;

-- 4. 创建leo和impeach的关联关系
INSERT INTO user_tenants (user_id, tenant_id, role, is_active)
SELECT 
    (SELECT id FROM users WHERE email = 'leo@impeach.com'),
    (SELECT id FROM tenants WHERE name = 'impeach'),
    'OWNER',
    true
ON CONFLICT DO NOTHING;

-- 5. 插入frontend公钥 (需要手动更新公钥内容)
INSERT INTO user_keys (user_id, key_id, public_key, key_type, name, description, is_active, is_primary)
SELECT 
    (SELECT id FROM users WHERE email = 'frontend@supplynexus.store'),
    'frontend-server-1',
    '-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAnFe1apracDJQOa1X3siF
Sfk47yPp2L2LvOpAb1I8ORMx3Sm6uIzyUP6HP/3V31Meqa10UsjyWN77HcsmCKaT
7V6pG0BlUNy4pLp92YreaO2ikApOQyi+j7Izgb1AAA5npe8a6L/4diAtLwDoiHYP
wKnB+i+72aYX2pkCOgkQgNZ3C+0UrYuGU+5m0cKsW+9oeStY2L7Ti7Z3IwehG7fC
C5TR0lDvr9+znJx3RimITr98Lg1rWBd59JgZ1RJTpUBgrSwQdk8z7cs1XqMDZoI0
Lf/vSYKnwt82skZH5UV1xuqcDMLIW84RvJlw6h7G09yRamIyyEJYiFrM6ciEoBFC
nwIDAQAB
-----END PUBLIC KEY-----',
    'rsa',
    'Frontend Server Key',
    'Frontend server public key for API authentication',
    true,
    true
ON CONFLICT (key_id) DO NOTHING;

-- 6. 验证插入结果
SELECT 'Tenants:' as info;
SELECT id, name, display_name FROM tenants;

SELECT 'Users:' as info;
SELECT id, email, full_name FROM users;

SELECT 'User-Tenant Relationships:' as info;
SELECT 
    u.email,
    t.name as tenant_name,
    ut.role
FROM user_tenants ut
JOIN users u ON ut.user_id = u.id
JOIN tenants t ON ut.tenant_id = t.id;

SELECT 'Frontend Keys:' as info;
SELECT 
    uk.key_id,
    uk.name,
    uk.is_active,
    uk.is_primary
FROM user_keys uk
JOIN users u ON uk.user_id = u.id
WHERE u.email = 'frontend@supplynexus.store';
