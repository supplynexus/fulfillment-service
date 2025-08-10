# 数据库设置指南

## 🎯 快速开始

### 1. 创建环境配置文件

```bash
# 复制环境配置模板
cp deployment/environments/env.example deployment/environments/env.local
cp deployment/environments/env.example deployment/environments/env.staging
cp deployment/environments/env.example deployment/environments/env.production

# 编辑配置文件（手动编辑，不提交到 git）
vim deployment/environments/env.local
vim deployment/environments/env.staging
vim deployment/environments/env.production
```

### 2. 启动数据库

```bash
# 启动本地数据库
./deployment/scripts/db-setup.sh local start

# 启动测试环境数据库
./deployment/scripts/db-setup.sh staging start

# 启动生产环境数据库
./deployment/scripts/db-setup.sh prod start
```

### 3. 运行数据库迁移

```bash
# 本地环境迁移
ENV_FILE=deployment/environments/env.local python backend/scripts/db.py upgrade

# 测试环境迁移
ENV_FILE=deployment/environments/env.staging python backend/scripts/db.py upgrade

# 生产环境迁移
ENV_FILE=deployment/environments/env.production python backend/scripts/db.py upgrade
```

## 📋 详细说明

### 环境配置

| 环境 | 端口 | 数据库名 | 容器名 | 数据目录 |
|------|------|----------|--------|----------|
| local | 5433 | supplynexus_local | supplynexus-postgres-local | data-local |
| staging | 5434 | supplynexus_staging | supplynexus-postgres-staging | data-staging |
| prod | 5435 | supplynexus_prod | supplynexus-postgres-prod | data-prod |

### 数据库管理命令

```bash
# 查看使用帮助
./deployment/scripts/db-setup.sh

# 启动数据库
./deployment/scripts/db-setup.sh local start

# 停止数据库
./deployment/scripts/db-setup.sh local stop

# 重启数据库
./deployment/scripts/db-setup.sh local restart

# 查看状态
./deployment/scripts/db-setup.sh local status

# 查看日志
./deployment/scripts/db-setup.sh local logs

# 重置数据库（删除所有数据）
./deployment/scripts/db-setup.sh local reset

# 备份数据库
./deployment/scripts/db-setup.sh local backup

# 恢复数据库
./deployment/scripts/db-setup.sh local restore backup_local_20231201_120000.sql
```

### 环境文件配置

每个环境文件包含以下配置：

```bash
# 环境类型
ENVIRONMENT=local

# 数据库配置
DATABASE_URL=postgresql+asyncpg://supplynexus_admin:your_password@localhost:5433/supplynexus_local
DATABASE_URL_SYNC=postgresql://supplynexus_admin:your_password@localhost:5433/supplynexus_local

# Redis 配置
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# API 密钥
SHOPIFY_API_KEY=your-shopify-api-key
SHOPIFY_API_SECRET=your-shopify-api-secret
PRINTIFY_API_TOKEN=your-printify-api-token

# 安全配置
SECRET_KEY=your-secret-key-change-in-production
WEBHOOK_SECRET=your-webhook-secret-change-in-production

# 应用配置
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
ALLOWED_HOSTS=localhost,127.0.0.1
```

## 🔄 开发流程

### 本地开发

```bash
# 1. 启动本地数据库
./deployment/scripts/db-setup.sh local start

# 2. 修改模型文件
vim backend/app/models/user.py

# 3. 生成迁移文件
python backend/scripts/db.py autogen "添加新字段"

# 4. 应用迁移（仅影响本地）
python backend/scripts/db.py upgrade
```

### 环境部署

```bash
# 1. 提交迁移文件到 git
git add backend/migrations/versions/
git commit -m "Add new migration"
git push

# 2. 在目标环境执行迁移
ENV_FILE=deployment/environments/env.staging python backend/scripts/db.py upgrade
```

## 🔧 故障排除

### 常见问题

#### 1. 环境配置文件不存在

```bash
# 错误：Environment file not found
# 解决：创建环境文件
cp deployment/environments/env.example deployment/environments/env.local
vim deployment/environments/env.local
```

#### 2. 数据库连接失败

```bash
# 检查数据库状态
./deployment/scripts/db-setup.sh local status

# 查看数据库日志
./deployment/scripts/db-setup.sh local logs

# 检查端口是否被占用
lsof -i :5433
```

#### 3. 端口冲突

```bash
# 停止占用端口的服务
sudo lsof -ti:5433 | xargs kill -9

# 或使用不同端口
# 修改环境文件中的端口配置
```

#### 4. 权限问题

```bash
# 确保脚本有执行权限
chmod +x deployment/scripts/db-setup.sh

# 确保数据目录有写权限
chmod 755 deployment/docker/postgresql/data-local
```

### 重置环境

```bash
# 完全重置本地环境
./deployment/scripts/db-setup.sh local stop
./deployment/scripts/db-setup.sh local reset
./deployment/scripts/db-setup.sh local start
```

## 📊 监控和维护

### 数据备份

```bash
# 定期备份
./deployment/scripts/db-setup.sh local backup

# 备份文件命名格式：backup_local_YYYYMMDD_HHMMSS.sql
```

### 数据恢复

```bash
# 从备份恢复
./deployment/scripts/db-setup.sh local restore backup_local_20231201_120000.sql
```

### 性能监控

```bash
# 查看数据库状态
./deployment/scripts/db-setup.sh local status

# 查看实时日志
./deployment/scripts/db-setup.sh local logs
```

## 🔒 安全注意事项

1. **环境文件不提交到 git**：所有环境文件已添加到 `.gitignore`
2. **修改默认密码**：首次使用后立即修改默认密码 `aabbccdd`
3. **定期备份**：重要数据定期备份
4. **网络隔离**：生产环境使用独立网络
5. **访问控制**：限制数据库访问权限

## 📝 最佳实践

1. **环境隔离**：不同环境使用不同的数据库和端口
2. **配置管理**：敏感信息只存储在环境文件中
3. **迁移管理**：本地开发生成迁移，环境部署应用迁移
4. **监控日志**：定期检查数据库日志
5. **备份策略**：定期备份数据库和配置文件
6. **测试验证**：部署前在测试环境验证
