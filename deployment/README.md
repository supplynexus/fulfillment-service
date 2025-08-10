# SupplyNexus Fulfillment Service - 部署指南

## 🚀 快速开始

### 新的部署方式（推荐）

```bash
# 启动开发环境
./deployment/scripts/deploy.sh development start

# 运行数据库迁移
./deployment/scripts/deploy.sh development db-upgrade

# 查看服务状态
./deployment/scripts/deploy.sh development db-status

# 查看日志
./deployment/scripts/deploy.sh development logs

# 停止服务
./deployment/scripts/deploy.sh development stop
```

### 环境配置

1. **复制环境配置文件**：
```bash
cp deployment/environments/env.example deployment/environments/env.development
cp deployment/environments/env.example deployment/environments/env.staging
cp deployment/environments/env.example deployment/environments/env.production
```

2. **编辑配置文件**：
```bash
vim deployment/environments/env.development
```

3. **关键配置项**：
```bash
# 数据库配置
DATABASE_URL=postgresql+asyncpg://username:password@host:port/database
DATABASE_URL_SYNC=postgresql://username:password@host:port/database

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

- **development** - 开发环境
- **staging** - 测试环境
- **production** - 生产环境

## 🔧 完整部署流程

### 1. 首次部署

```bash
# 1. 拉取代码
git pull origin develop

# 2. 配置环境文件
cp deployment/environments/env.example deployment/environments/env.development
# 编辑配置文件...

# 3. 启动基础设施（PostgreSQL, Redis）
cd deployment/docker/postgresql && ./deploy.sh dev
cd deployment/docker/redis && ./deploy.sh dev

# 4. 运行数据库迁移
./deployment/scripts/deploy.sh development db-upgrade

# 5. 启动应用服务
./deployment/scripts/deploy.sh development start
```

### 2. 日常部署

```bash
# 1. 拉取最新代码
git pull origin develop

# 2. 运行数据库迁移（如果有）
./deployment/scripts/deploy.sh development db-upgrade

# 3. 重启服务
./deployment/scripts/deploy.sh development restart
```

### 3. 生产环境部署

```bash
# 1. 切换到生产分支
git checkout main
git pull origin main

# 2. 运行生产环境迁移
./deployment/scripts/deploy.sh production db-upgrade

# 3. 启动生产服务
./deployment/scripts/deploy.sh production start
```

## 🔍 故障排查

### 查看服务状态
```bash
# 查看所有服务日志
./deployment/scripts/deploy.sh development logs

# 查看特定服务日志
./deployment/scripts/deploy.sh development logs backend
```

### 数据库问题
```bash
# 检查迁移状态
./deployment/scripts/deploy.sh development db-status

# 查看迁移历史
./deployment/scripts/deploy.sh development db-history
```

### 重置数据库（谨慎使用）
```bash
cd backend
source .venv/bin/activate
python deployment/scripts/db.py reset
```

## 📝 注意事项

1. **环境文件安全**：不要将包含真实密码的环境文件提交到 git
2. **备份数据库**：在生产环境执行迁移前，建议先备份数据库
3. **测试迁移**：在 staging 环境测试迁移后再部署到生产环境
4. **权限检查**：确保脚本有执行权限：`chmod +x deployment/scripts/deploy.sh`

## 🔄 旧版本兼容性

旧的部署方式仍然支持：

```bash
# 旧方式（仍然可用）
ENV_FILE=env.development ./deployment/scripts/deploy.sh start
ENV_FILE=env.development ./deployment/scripts/deploy.sh db-upgrade
```

## 📞 支持

如果遇到问题，请检查：
1. 环境配置文件是否正确
2. 数据库和 Redis 服务是否正常运行
3. 网络连接是否正常
4. 查看服务日志获取详细错误信息
