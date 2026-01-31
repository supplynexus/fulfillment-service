-- 初始化开发环境数据
-- 创建测试租户和用户

-- 创建测试租户
INSERT INTO tenants (name, display_name, description, settings, is_active, key_type, key_size, created_at)
VALUES (
    'impeach',
    'Impeach Test Tenant', 
    '用于测试的租户',
    '{}',
    true,
    'rsa',
    2048,
    NOW()
) ON CONFLICT (name) DO NOTHING;

-- 获取租户ID
-- 注意：这里需要手动替换租户ID
-- 或者使用子查询

-- 创建测试用户
INSERT INTO users (email, hashed_password, full_name, is_active, is_superuser, created_at)
VALUES (
    'test@impeach.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8QjK8K2', -- test123456
    'Test User',
    true,
    false,
    NOW()
) ON CONFLICT (email) DO NOTHING;

-- 创建用户-租户关联
-- 注意：这里需要手动替换用户ID和租户ID
-- 或者使用子查询

-- 显示创建的数据
SELECT 'Tenants:' as info;
SELECT id, name, display_name, is_active FROM tenants WHERE name = 'impeach';

SELECT 'Users:' as info;
SELECT id, email, full_name, is_active FROM users WHERE email = 'test@impeach.com';
