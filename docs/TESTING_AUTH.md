# 认证测试指南

## 概述

本系统支持多种认证方式，在开发和生产环境中提供不同的测试便利性。

## 认证方式

### 1. 开发环境认证 (推荐用于测试)

在开发环境中，可以使用简化的认证方式：

```bash
# 使用开发认证头
curl -X GET "http://localhost:8000/api/v1/orders" \
  -H "X-Dev-User-ID: 1" \
  -H "X-Dev-Tenant-ID: 1"
```

### 2. 时间戳签名认证 (生产环境)

在生产环境中，使用完整的时间戳签名认证：

```bash
# 使用时间戳签名认证
curl -X GET "http://localhost:8000/api/v1/orders" \
  -H "X-Signature: abc123def456..." \
  -H "X-Timestamp: 1640995200" \
  -H "X-Nonce: random_nonce_123" \
  -H "X-User-ID: 1" \
  -H "X-Key-ID: user_key_456"
```

## 测试工具

### 使用测试辅助脚本

```bash
# 生成开发环境认证头
python scripts/test_auth_helper.py --method GET --path /api/v1/orders

# 生成curl命令
python scripts/test_auth_helper.py --method GET --path /api/v1/orders --format curl

# 生成JSON格式的认证头
python scripts/test_auth_helper.py --method GET --path /api/v1/orders --format json

# 使用生产模式认证
python scripts/test_auth_helper.py --method GET --path /api/v1/orders --dev-mode false
```

### 示例输出

**开发模式认证头：**
```
Headers:
X-Dev-User-ID: 1
X-Dev-Tenant-ID: 1
Content-Type: application/json
```

**Curl命令：**
```bash
curl -X GET 'http://localhost:8000/api/v1/orders' \
  -H 'X-Dev-User-ID: 1' \
  -H 'X-Dev-Tenant-ID: 1' \
  -H 'Content-Type: application/json'
```

## 智能认证选择

系统会自动根据请求头选择合适的认证方式：

1. **开发环境 + 开发头** → 使用开发认证
2. **生产环境 + 时间戳签名** → 使用时间戳签名认证
3. **开发环境 + 无认证头** → 尝试开发认证
4. **生产环境 + 无认证头** → 拒绝请求

## 测试场景

### 基本API测试

```bash
# 测试获取订单
python scripts/test_auth_helper.py --method GET --path /api/v1/orders --format curl | bash

# 测试创建订单
python scripts/test_auth_helper.py --method POST --path /api/v1/orders --body '{"order_id": 123}' --format curl | bash
```

### 多租户测试

```bash
# 测试租户1
python scripts/test_auth_helper.py --user-id 1 --tenant-id 1 --format curl

# 测试租户2
python scripts/test_auth_helper.py --user-id 2 --tenant-id 2 --format curl
```

### 认证失败测试

```bash
# 测试无认证头
curl -X GET "http://localhost:8000/api/v1/orders"

# 测试无效用户ID
curl -X GET "http://localhost:8000/api/v1/orders" \
  -H "X-Dev-User-ID: 999" \
  -H "X-Dev-Tenant-ID: 1"
```

## 环境配置

### 开发环境

```python
# settings.py
DEBUG = True
```

### 生产环境

```python
# settings.py
DEBUG = False
```

## 安全注意事项

1. **开发认证只在DEBUG=True时有效**
2. **生产环境必须使用时间戳签名认证**
3. **开发认证头不应在生产环境中使用**
4. **定期轮换密钥和更新认证机制**

## 故障排除

### 常见错误

1. **"Development authentication not allowed in production"**
   - 确保DEBUG=True或使用时间戳签名认证

2. **"Missing required authentication headers"**
   - 检查是否提供了必要的认证头

3. **"Timestamp expired"**
   - 检查系统时间是否同步
   - 时间戳有效期通常为5分钟

4. **"Nonce already used"**
   - 每个随机数只能使用一次
   - 生成新的随机数重试

### 调试技巧

1. **查看认证日志**
2. **检查Redis中的nonce缓存**
3. **验证密钥是否正确**
4. **确认用户和租户关系**
