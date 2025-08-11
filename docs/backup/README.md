# SupplyNexus Fulfillment Service - 部署指南

## 🚀 快速开始

### 新的部署方式（推荐）

```bash
# 启动本地环境
./deployment/scripts/deploy.sh local start

# 启动开发环境
./deployment/scripts/deploy.sh dev start

# 运行数据库迁移
./deployment/scripts/deploy.sh local db-upgrade

# 查看服务状态
./deployment/scripts/deploy.sh local status

# 查看日志
./deployment/scripts/deploy.sh local logs

# 停止服务
./deployment/scripts/deploy.sh local stop
```

### 环境配置

1. **复制环境配置文件**：
```bash
cp deployment/environments/env.example deployment/environments/env.local
cp deployment/environments/env.example deployment/environments/env.dev
cp deployment/environments/env.example deployment/environments/env.stg
cp deployment/environments/env.example deployment/environments/env.prod
```

2. **编辑配置文件**：
```bash
vim deployment/environments/env.local
```

3. **关键配置项**：
```bash
# 本地环境配置 (端口: 5432)
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/database
DATABASE_URL_SYNC=postgresql://username:password@localhost:5432/database

# 开发环境配置 (端口: 5433)
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5433/database
DATABASE_URL_SYNC=postgresql://username:password@localhost:5433/database

# Redis 配置
REDIS_URL=redis://:password@host:port/0
CELERY_BROKER_URL=redis://:password@host:port/1
CELERY_RESULT_BACKEND=redis://:password@host:port/2

# API 密钥
SHOPIFY_API_KEY=your-shopify-api-key
SHOPIFY_API_SECRET=your-shopify-api-secret
PRINTIFY_API_TOKEN=your-printify-api-token
```

## 📋 可用命令

### 服务管理
- `start` - 启动所有服务
- `stop` - 停止所有服务
- `restart` - 重启所有服务
- `logs [service]` - 查看日志（可选指定服务名）

### 数据库管理
- `db-upgrade` - 运行数据库迁移
- `db-status` - 检查迁移状态
- `db-history` - 查看迁移历史

## 🌍 环境说明

- **local** - 本地开发环境（端口 5432）
- **dev** - 开发服务器环境（端口 5433）
- **staging** - 测试环境
- **production** - 生产环境

## 🔧 完整部署流程

### 1. 首次部署

```bash
# 1. 拉取代码
git pull origin develop

# 2. 配置环境文件
cp deployment/environments/env.example deployment/environments/env.dev
# 编辑配置文件...

# 3. 启动基础设施（PostgreSQL, Redis）
cd deployment/docker/postgresql && ./deploy.sh dev
cd deployment/docker/redis && ./deploy.sh dev

# 4. 运行数据库迁移
./deployment/scripts/deploy.sh dev db-upgrade

# 5. 启动应用服务
./deployment/scripts/deploy.sh dev start
```

### 2. 日常部署

```bash
# 1. 拉取最新代码
git pull origin develop

# 2. 运行数据库迁移（如果有）
./deployment/scripts/deploy.sh dev db-upgrade

# 3. 重启服务
./deployment/scripts/deploy.sh dev restart
```

### 3. 生产环境部署

```bash
# 1. 切换到生产分支
git checkout main
git pull origin main

# 2. 运行生产环境迁移
./deployment/scripts/deploy.sh prod db-upgrade

# 3. 启动生产服务
./deployment/scripts/deploy.sh prod start
```

## 📚 更多信息

- [主项目文档](../README.md)
- [系统架构文档](./ARCHITECTURE.md)
- [环境配置指南](./ENVIRONMENTS.md)
- [数据库设置指南](./DATABASE_SETUP.md)
