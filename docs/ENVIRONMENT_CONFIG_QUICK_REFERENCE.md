# 环境配置快速参考

## 📋 概述

SupplyNexus 项目使用统一的环境配置管理，所有环境配置文件位于 `deployment/environments/` 目录。

## 🗂️ 配置文件结构

```
deployment/environments/
├── env.example          # 配置模板
├── env.local            # 本地环境
├── env.dev              # 开发环境
├── env.stg              # 测试环境
└── env.prod             # 生产环境
```

## 🚀 快速配置

### 1. 创建环境配置文件

```bash
# 复制配置模板
cp deployment/environments/env.example deployment/environments/env.local

# 编辑配置文件
vim deployment/environments/env.local
```

### 2. 必需的环境变量

```bash
# 数据库配置
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/database
DATABASE_URL_SYNC=postgresql://username:password@localhost:5432/database

# Redis配置
REDIS_URL=redis://:password@localhost:6379/0
CELERY_BROKER_URL=redis://:password@localhost:6379/1
CELERY_RESULT_BACKEND=redis://:password@localhost:6379/2

# 安全配置
SECRET_KEY=your-secret-key-change-in-prod
HEALTH_CHECK_API_KEY=your-health-check-api-key

# 应用配置
ENVIRONMENT=local
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 3. 可选的环境变量

```bash
# Shopify配置
SHOPIFY_API_KEY=your-shopify-api-key
SHOPIFY_API_SECRET=your-shopify-api-secret
SHOPIFY_ACCESS_TOKEN=your-shopify-access-token

# Printify配置
PRINTIFY_API_TOKEN=your-printify-api-token

# 其他配置
WEBHOOK_SECRET=your-webhook-secret
SENTRY_DSN=your-sentry-dsn
```

## 🔧 使用方式

### 本地开发

```bash
# 使用默认配置（deployment/environments/env.local）
python -m uvicorn app.main:app --reload

# 指定环境配置
export ENV_FILE=../deployment/environments/env.dev
python -m uvicorn app.main:app --reload
```

### 数据库操作

```bash
# 本地环境
./scripts/db/alembic.sh local upgrade

# 开发环境
./deployment/scripts/db-docker.sh dev upgrade

# 检查状态
./scripts/db/alembic.sh local current
```

### Celery服务

```bash
# 本地环境
export ENV_FILE=../deployment/environments/env.local
./backend/scripts/start_celery.sh

# 开发环境
export ENV_FILE=../deployment/environments/env.dev
./backend/scripts/start_celery.sh
```

### 环境配置检查

```bash
# 检查本地环境
./scripts/check_environment.sh local

# 检查开发环境
./scripts/check_environment.sh dev

# 检查生产环境
./scripts/check_environment.sh prod
```

## 🌍 环境差异

### 本地环境 (local)
- **端口**: PostgreSQL 5432, Redis 6379
- **用途**: 本地开发和测试
- **特点**: 有Python虚拟环境，可直接执行命令

### 开发环境 (dev)
- **端口**: PostgreSQL 5433, Redis 6380
- **用途**: 开发服务器环境
- **特点**: 只有Docker环境，使用容器化脚本

### 测试环境 (stg)
- **用途**: 测试和预发布
- **特点**: 生产环境配置，用于最终测试

### 生产环境 (prod)
- **用途**: 生产部署
- **特点**: 生产级配置，安全要求高

## 🔍 配置检查

### 使用检查脚本

```bash
# 检查环境配置
./scripts/check_environment.sh local

# 检查数据库连接
./scripts/check_environment.sh dev

# 检查生产配置
./scripts/check_environment.sh prod
```

### 手动检查

```bash
# 检查环境文件是否存在
ls -la deployment/environments/

# 检查必需变量
grep -E "^(DATABASE_URL|REDIS_URL|SECRET_KEY|HEALTH_CHECK_API_KEY)=" deployment/environments/env.local

# 检查数据库连接
psql $DATABASE_URL_SYNC -c "SELECT 1;"

# 检查Redis连接
redis-cli -u $REDIS_URL ping
```

## 🛠️ 故障排除

### 常见问题

#### 1. 环境文件不存在
```bash
# 错误: Environment file not found
# 解决: 创建环境文件
cp deployment/environments/env.example deployment/environments/env.local
```

#### 2. 数据库连接失败
```bash
# 错误: Database connection failed
# 解决: 检查数据库配置和连接
./scripts/check_environment.sh local
```

#### 3. Redis连接失败
```bash
# 错误: Redis connection failed
# 解决: 检查Redis配置和连接
redis-cli -u $REDIS_URL ping
```

#### 4. 环境变量未设置
```bash
# 错误: Missing required environment variables
# 解决: 设置必需的环境变量
vim deployment/environments/env.local
```

### 调试技巧

#### 1. 查看当前环境
```bash
echo $ENV_FILE
echo $ENVIRONMENT
```

#### 2. 查看配置内容
```bash
# 查看所有配置
cat deployment/environments/env.local

# 查看特定配置
grep "DATABASE_URL" deployment/environments/env.local
```

#### 3. 测试配置加载
```bash
# 测试配置加载
python -c "from app.core.config import settings; print(settings.DATABASE_URL)"
```

## 📝 最佳实践

### 1. 环境隔离
- 每个环境使用独立的配置文件
- 不要在生产环境使用开发配置
- 定期备份生产环境配置

### 2. 安全配置
- 使用强密码和密钥
- 定期轮换密钥
- 不要在代码中硬编码敏感信息

### 3. 配置管理
- 使用版本控制管理配置模板
- 不要提交实际的环境配置文件
- 使用环境变量覆盖敏感配置

### 4. 监控和日志
- 监控配置变更
- 记录配置加载日志
- 定期检查配置有效性

## 🔄 更新和维护

### 添加新配置项
1. 更新 `deployment/environments/env.example`
2. 更新 `backend/app/core/config.py`
3. 更新所有环境配置文件
4. 更新文档

### 配置迁移
1. 备份当前配置
2. 更新配置模板
3. 更新所有环境文件
4. 测试配置有效性

---

**文档版本**: v1.0  
**最后更新**: 2025年8月14日
