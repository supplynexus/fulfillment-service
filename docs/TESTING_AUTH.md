# 认证测试指南

## 概述

本系统使用统一的时间戳签名认证方式，在所有环境（开发、测试、生产）中保持一致。

## 认证方式

### 时间戳签名认证 (所有环境)

所有环境都使用相同的时间戳签名认证：

```bash
# 使用时间戳签名认证
curl -X GET "http://localhost:8000/api/v1/orders" \
  -H "X-Signature: <包含所有信息的签名>"
```

## 测试工具

### 使用签名生成器

```bash
# 快速测试
cd backend
python tests/tools/quick_test.py

# 完整工具
python tests/tools/signature_generator.py
```

### 示例输出

**签名认证：**
```
X-Signature: eyJ0aW1lc3RhbXAiOiAxNzU0OTc3ODE2LCAibm9uY2UiOiAiZWU3ZjgyMmU4YjY0ZTVmZmJkZjI3YWY2ZTcwYTQzNjUiLCAidGVuYW50X2lkIjogMSwgInVzZXJfaWQiOiAxLCAic2lnbmF0dXJlIjogImM1MDEwM2U1Yjk5NjFhZGZiNjMxM2I5NjAwMjAwOTExNzYyZWRjNTBjMzIwZjMwYWVjMWY1YmU0OWUxMzg4YzcyNDg1OWI1ZjJiOTJiZTA4YWY1ZWUzODFkODU4MDA0NTgwODc0YWZlZmI3NDU2M2FhMjk0MzgwNjk4NjBjMjJhZTMwYzY3Mjg1YjJlOTBlZTFiMzUzYzc3ZWRkNzY4OGIyNGI0ZDk5MGZjM2QxNmM4ZGVlMDZkNmUzZjMyZGUwMzk4Yzc1MjY1MGIxM2I0MGE1Nzg0NjIwMTk1MzVkNTUyMWVkMzVjYzdiNmE0MTgyYjQ4ZmQwNzNiZTYzM2JmOGM3NDg1MjI5YTE0MDc2YjE4ODM0ODI2MDFjMmQ5NjYxY2M0NmNmYzAyY2YyZjc5NzdlZGRmZGRlYjYyNGYzMDFmNDUwMTFkZjdkOTExOGU4MzZiOGE1Yjk2ZjgwMTQ3N2VlZTY1ZjBlMTA1MGQyMzc3MTM0NTkwMGNhY2RkOWRkODk3NDBlOWZjZGUyMzllM2U5MGMxZGFjMzAyYzNhM2JhMzIwMzI1NTM5MTdjZjZjYTU2OTE2ODQyZjBiMDBmZDNmY2M4YjQ0NGI2OGJhNzllZmJjODg3ODYyZDJkODBlYjExMzIyNjg3Y2E5NjFmNjMxMmQxYmFlYjFhMGFmZTQ0IiwgImtleV9pZCI6ICJ0ZXN0X2tleV8wMDEifQ==
```

**Curl命令：**
```bash
curl -X GET 'http://localhost:8000/api/v1/orders' \
  -H 'X-Signature: eyJ0aW1lc3RhbXAiOiAxNzU0OTc3ODE2LCAibm9uY2UiOiAiZWU3ZjgyMmU4YjY0ZTVmZmJkZjI3YWY2ZTcwYTQzNjUiLCAidGVuYW50X2lkIjogMSwgInVzZXJfaWQiOiAxLCAic2lnbmF0dXJlIjogImM1MDEwM2U1Yjk5NjFhZGZiNjMxM2I5NjAwMjAwOTExNzYyZWRjNTBjMzIwZjMwYWVjMWY1YmU0OWUxMzg4YzcyNDg1OWI1ZjJiOTJiZTA4YWY1ZWUzODFkODU4MDA0NTgwODc0YWZlZmI3NDU2M2FhMjk0MzgwNjk4NjBjMjJhZTMwYzY3Mjg1YjJlOTBlZTFiMzUzYzc3ZWRkNzY4OGIyNGI0ZDk5MGZjM2QxNmM4ZGVlMDZkNmUzZjMyZGUwMzk4Yzc1MjY1MGIxM2I0MGE1Nzg0NjIwMTk1MzVkNTUyMWVkMzVjYzdiNmE0MTgyYjQ4ZmQwNzNiZTYzM2JmOGM3NDg1MjI5YTE0MDc2YjE4ODM0ODI2MDFjMmQ5NjYxY2M0NmNmYzAyY2YyZjc5NzdlZGRmZGRlYjYyNGYzMDFmNDUwMTFkZjdkOTExOGU4MzZiOGE1Yjk2ZjgwMTQ3N2VlZTY1ZjBlMTA1MGQyMzc3MTM0NTkwMGNhY2RkOWRkODk3NDBlOWZjZGUyMzllM2U5MGMxZGFjMzAyYzNhM2JhMzIwMzI1NTM5MTdjZjZjYTU2OTE2ODQyZjBiMDBmZDNmY2M4YjQ0NGI2OGJhNzllZmJjODg3ODYyZDJkODBlYjExMzIyNjg3Y2E5NjFmNjMxMmQxYmFlYjFhMGFmZTQ0IiwgImtleV9pZCI6ICJ0ZXN0X2tleV8wMDEifQ=='
```

## 统一认证机制

系统在所有环境中都使用相同的时间戳签名认证：

1. **所有环境** → 使用时间戳签名认证
2. **无认证头** → 拒绝请求

## 测试场景

### 基本API测试

```bash
# 测试获取订单
cd backend
python tests/tools/quick_test.py

# 使用生成的curl命令测试
curl -X GET 'http://localhost:8000/api/v1/orders' \
  -H 'X-Signature: <生成的签名>'
```

### 多租户测试

```bash
# 测试租户1
python tests/tools/signature_generator.py

# 修改tenant_id参数测试不同租户
```

### 认证失败测试

```bash
# 测试无认证头
curl -X GET "http://localhost:8000/api/v1/orders"

# 测试无效签名
curl -X GET "http://localhost:8000/api/v1/orders" \
  -H "X-Signature: invalid_signature"
```

## 环境配置

所有环境使用相同的配置：

```python
# settings.py
HASHIDS_SALT = "your-hashids-salt-here"
HASHIDS_MIN_LENGTH = 8
```

## 安全注意事项

1. **所有环境都使用相同的时间戳签名认证**
2. **签名包含时间戳，5分钟内有效**
3. **每个nonce只能使用一次（防重放攻击）**
4. **定期轮换密钥和更新认证机制**

## 故障排除

### 常见错误

1. **"Missing required authentication header: X-Signature"**
   - 确保提供了X-Signature头

2. **"Invalid signature format"**
   - 检查签名格式是否正确

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
