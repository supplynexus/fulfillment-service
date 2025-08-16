# 密钥对生成工具

## 概述

这个工具用于为租户生成 RSA 密钥对，支持保存到文件和数据库。

## 功能特性

- ✅ 生成 RSA 密钥对 (1024/2048/4096 bits)
- ✅ 保存密钥到文件
- ✅ 自动保存公钥到数据库
- ✅ 支持自定义输出目录
- ✅ 自动创建 .gitignore 文件
- ✅ 依赖检查和自动安装
- ✅ 彩色输出和详细日志

## 使用方法

### 基本用法

```bash
# 生成密钥对并保存到文件
./generate_keys.sh impeach

# 生成密钥对并保存到数据库
./generate_keys.sh impeach --save-db

# 生成 4096 bits 密钥对
./generate_keys.sh impeach --size 4096 --save-db

# 指定输出目录
./generate_keys.sh impeach --output-dir ./tenant_keys --save-db

# 显示生成的密钥
./generate_keys.sh impeach --display --save-db
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `tenant_name` | 租户名称 | 必需 |
| `--type` | 密钥类型 | `rsa` |
| `--size` | 密钥大小 (bits) | `2048` |
| `--save-db` | 保存公钥到数据库 | `false` |
| `--output-dir` | 输出目录 | `./keys` |
| `--display` | 显示密钥内容 | `false` |
| `--help` | 显示帮助 | - |

### 支持的密钥大小

- `1024` bits (不推荐用于生产环境)
- `2048` bits (推荐)
- `4096` bits (高安全性)

## 文件结构

生成的文件结构：

```
./keys/
├── .gitignore          # 自动创建，防止密钥文件提交到 Git
├── impeach_private_key.pem
└── impeach_public_key.pem
```

## 安全注意事项

### 1. 私钥安全

- 🔒 **私钥文件不应提交到版本控制系统**
- 🔒 **私钥文件应设置适当的文件权限** (600)
- 🔒 **在生产环境中使用更安全的密钥存储方式**

### 2. 文件权限

```bash
# 设置私钥文件权限
chmod 600 ./keys/*_private_key.pem

# 设置公钥文件权限
chmod 644 ./keys/*_public_key.pem
```

### 3. 目录权限

```bash
# 设置密钥目录权限
chmod 700 ./keys/
```

## 数据库集成

### 自动保存公钥

使用 `--save-db` 参数时，工具会：

1. 连接到数据库
2. 查找指定的租户
3. 更新租户的公钥字段
4. 显示更新结果

### 数据库要求

- 租户表必须存在
- 租户记录必须存在
- 公钥字段必须支持 TEXT 类型

## 错误处理

### 常见错误

1. **租户不存在**
   ```
   ❌ 租户 'impeach' 不存在
   ```

2. **数据库连接失败**
   ```
   ❌ 保存公钥到数据库失败: connection refused
   ```

3. **权限不足**
   ```
   ❌ 无法创建目录: Permission denied
   ```

### 故障排除

1. **检查虚拟环境**
   ```bash
   cd backend
   source .venv/bin/activate
   ```

2. **检查依赖**
   ```bash
   pip install cryptography sqlalchemy asyncpg
   ```

3. **检查数据库连接**
   ```bash
   # 检查环境变量
   echo $DATABASE_URL
   ```

## 示例工作流

### 为新租户生成密钥

```bash
# 1. 生成密钥对
./generate_keys.sh new_tenant --save-db --output-dir ./tenant_keys

# 2. 设置文件权限
chmod 600 ./tenant_keys/new_tenant_private_key.pem
chmod 644 ./tenant_keys/new_tenant_public_key.pem
chmod 700 ./tenant_keys/

# 3. 验证生成结果
ls -la ./tenant_keys/
```

### 更新现有租户密钥

```bash
# 1. 备份旧密钥
cp ./keys/impeach_private_key.pem ./keys/impeach_private_key.pem.backup

# 2. 生成新密钥
./generate_keys.sh impeach --save-db --size 4096

# 3. 测试新密钥
# (使用你的应用程序测试新密钥)
```

## 集成到部署流程

### 开发环境

```bash
# 在开发环境中生成密钥
./generate_keys.sh dev_tenant --save-db --output-dir ./dev_keys
```

### 生产环境

```bash
# 在生产环境中生成密钥
./generate_keys.sh prod_tenant --save-db --output-dir /secure/keys --size 4096
```

## 注意事项

1. **密钥轮换**: 定期更换密钥对
2. **备份**: 安全备份私钥文件
3. **监控**: 监控密钥使用情况
4. **审计**: 记录密钥生成和更新操作

## 相关文件

- `generate_keys.py` - Python 实现
- `generate_keys.sh` - Shell 脚本包装器
- `KEY_GENERATION.md` - 本文档
- `.gitignore` - 自动生成的 Git 忽略文件
