# 认证测试工具

这个目录包含了用于测试认证系统的工具。

## 文件说明

- `signature_generator.py` - 完整的签名生成器工具
- `quick_test.py` - 快速测试脚本
- `README.md` - 本说明文件

## 使用方法

### 1. 安装依赖

```bash
cd backend
pip install hashids cryptography
```

### 2. 快速测试

```bash
python tests/tools/quick_test.py
```

这会生成一个测试签名和curl命令。

### 3. 完整工具

```bash
python tests/tools/signature_generator.py
```

这会：
- 生成RSA密钥对
- 保存密钥到文件
- 生成测试签名
- 显示Hashids编码的ID
- 生成curl测试命令

## 生成的文件

- `test_private_key.pem` - 测试私钥
- `test_public_key.pem` - 测试公钥

## 测试场景

### 租户级API（推荐）

大部分API只需要租户信息：

```bash
curl -X GET 'http://localhost:8000/api/v1/orders' \
  -H 'X-Tenant-ID: <租户hashid>' \
  -H 'X-Signature: <签名>'
```

### 用户级API

需要用户信息的API：

```bash
curl -X GET 'http://localhost:8000/api/v1/user/profile' \
  -H 'X-Tenant-ID: <租户hashid>' \
  -H 'X-Signature: <签名>'
```

### 所有环境统一认证

所有环境（开发、测试、生产）都使用相同的签名认证：

```bash
curl -X GET 'http://localhost:8000/api/v1/orders' \
  -H 'X-Signature: <签名>'
```

## Hashids编码

- Tenant ID 1 -> Hashid: `PoRpOk2e`
- User ID 1 -> Hashid: `PoRpOk2e`

## 环境变量

确保在 `.env` 文件中设置：

```env
HASHIDS_SALT=your-hashids-salt-here
HASHIDS_MIN_LENGTH=8
```

## 注意事项

1. 这些工具仅用于测试，不要在生产环境使用
2. 生成的密钥对仅用于测试
3. 签名包含时间戳，5分钟内有效
4. 每个nonce只能使用一次（防重放攻击）
5. 所有环境都使用相同的签名认证机制
