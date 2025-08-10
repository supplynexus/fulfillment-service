# SupplyNexus 部署指南

## 🏗️ 架构概述

本项目采用**分层架构**，将基础设施和应用层完全分离：

```
┌─────────────────────────────────────────────────────────────┐
│                    应用层 (Application Layer)                │
├─────────────────────────────────────────────────────────────┤
│  Backend (Python/FastAPI)                                   │
│  - 使用已启动的基础设施服务                                  │
│  - 通过环境变量连接数据库和缓存                              │
│  - 支持 Alembic 数据库迁移                                   │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                  基础设施层 (Infrastructure Layer)           │
├─────────────────────────────────────────────────────────────┤
│  PostgreSQL (独立 Docker Compose)                           │
│  - 端口: local(5432), dev(5433), staging(5434), prod(5435)  │
│  - 独立的环境变量配置                                        │
│  - 独立的数据持久化                                          │
│                                                             │
│  Redis (独立 Docker Compose)                                │
│  - 端口: local(6379), dev(6380), staging(6381), prod(6382)  │
│  - 独立的环境变量配置                                        │
│  - 独立的数据持久化                                          │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 环境端口分配

| 环境 | PostgreSQL 端口 | Redis 端口 | 说明 |
|------|----------------|------------|------|
| local | 5432 | 6379 | 本地开发环境 |
| dev | 5433 | 6380 | 开发服务器环境 |
| staging | 5434 | 6381 | 测试服务器环境 |
| prod | 5435 | 6382 | 生产服务器环境 |

### 首次设置 Local 环境

#### 1. 设置 PostgreSQL

```bash
# 进入 PostgreSQL 目录
cd deployment/docker/postgresql

# 复制环境配置
cp environment.example environment.local

# 编辑配置文件
vim environment.local
# 修改 POSTGRES_PASSWORD=your-password

# 启动 PostgreSQL
./deploy.sh local
```

#### 2. 设置 Redis

```bash
# 进入 Redis 目录
cd ../redis

# 复制环境配置
cp environment.example environment.local

# 编辑配置文件
vim environment.local
# 修改 REDIS_PASSWORD=your-password

# 启动 Redis
./deploy.sh local
```

#### 3. 设置应用环境

```bash
# 回到项目根目录
cd ../../../

# 复制应用环境配置
cp deployment/environments/env.example deployment/environments/env.local

# 编辑应用配置
vim deployment/environments/env.local
# 修改数据库和 Redis 连接信息
```

#### 4. 运行数据库迁移

```bash
# 运行数据库迁移
ENV_FILE=deployment/environments/env.local python backend/scripts/db.py upgrade
```

## 🔧 管理命令

### 基础设施管理

#### 统一管理脚本
```bash
# 查看帮助
./deployment/scripts/infra.sh

# 启动所有基础设施
./deployment/scripts/infra.sh local all start

# 查看状态
./deployment/scripts/infra.sh local all status

# 停止服务
./deployment/scripts/infra.sh local postgres stop
./deployment/scripts/infra.sh local redis stop

# 重置数据
./deployment/scripts/infra.sh local all reset
```

#### 单独管理
```bash
# PostgreSQL 管理
cd deployment/docker/postgresql
./deploy.sh local start|stop|restart|status|logs

# Redis 管理
cd deployment/docker/redis
./deploy.sh local start|stop|restart|status|logs
```

### 应用管理

```bash
# 启动应用
ENV_FILE=deployment/environments/env.local ./deployment/scripts/deploy.sh start

# 数据库迁移
ENV_FILE=deployment/environments/env.local python backend/scripts/db.py upgrade

# 查看应用状态
ENV_FILE=deployment/environments/env.local ./deployment/scripts/deploy.sh status
```

## 📁 目录结构

```
deployment/
├── docker/                          # 基础设施 Docker 配置
│   ├── postgresql/                  # PostgreSQL 独立配置
│   │   ├── docker-compose.yml      # PostgreSQL Docker Compose
│   │   ├── deploy.sh               # PostgreSQL 部署脚本
│   │   ├── environment.example     # 环境配置模板
│   │   ├── environment.local       # 本地环境配置（不提交到 git）
│   │   ├── environment.dev         # 开发环境配置（不提交到 git）
│   │   ├── environment.staging     # 测试环境配置（不提交到 git）
│   │   ├── environment.prod        # 生产环境配置（不提交到 git）
│   │   └── data-*/                 # 数据持久化目录
│   │
│   └── redis/                      # Redis 独立配置
│       ├── docker-compose.yml      # Redis Docker Compose
│       ├── deploy.sh               # Redis 部署脚本
│       ├── environment.example     # 环境配置模板
│       ├── environment.local       # 本地环境配置（不提交到 git）
│       ├── environment.dev         # 开发环境配置（不提交到 git）
│       ├── environment.staging     # 测试环境配置（不提交到 git）
│       ├── environment.prod        # 生产环境配置（不提交到 git）
│       └── data-*/                 # 数据持久化目录
│
├── environments/                    # 应用层环境配置
│   ├── env.example                 # 应用环境配置模板
│   ├── env.local                   # 本地环境配置（不提交到 git）
│   ├── env.staging                 # 测试环境配置（不提交到 git）
│   └── env.production              # 生产环境配置（不提交到 git）
│
└── scripts/                        # 管理脚本
    ├── infra.sh                    # 基础设施管理脚本
    ├── deploy.sh                   # 应用部署脚本
    └── db.py                       # 数据库迁移脚本
```

## 🔒 安全配置

### 环境文件管理

所有包含敏感信息的配置文件都不会提交到 git：

#### 基础设施环境文件
```
deployment/docker/postgresql/environment.local
deployment/docker/postgresql/environment.dev
deployment/docker/postgresql/environment.staging
deployment/docker/postgresql/environment.prod
deployment/docker/redis/environment.local
deployment/docker/redis/environment.dev
deployment/docker/redis/environment.staging
deployment/docker/redis/environment.prod
```

#### 应用环境文件
```
deployment/environments/env.local
deployment/environments/env.development
deployment/environments/env.staging
deployment/environments/env.production
```

### 密码管理

- **PostgreSQL 密码**：在基础设施配置中设置
- **Redis 密码**：在基础设施配置中设置
- **应用密钥**：在应用环境配置中设置
- **所有密码**：手动编辑，不提交到 git

## 🔄 开发流程

### 日常开发

```bash
# 1. 基础设施已启动，无需重复启动

# 2. 修改代码
vim backend/app/models/user.py

# 3. 生成迁移
python backend/scripts/db.py autogen "添加新字段"

# 4. 应用迁移
ENV_FILE=deployment/environments/env.local python backend/scripts/db.py upgrade

# 5. 重启应用
ENV_FILE=deployment/environments/env.local ./deployment/scripts/deploy.sh restart
```

### 环境部署

```bash
# 1. 提交代码
git add backend/migrations/versions/
git commit -m "Add new migration"
git push

# 2. 在目标环境执行迁移
ENV_FILE=deployment/environments/env.staging python backend/scripts/db.py upgrade
```

## 🛠️ 故障排除

### 常见问题

#### 1. 端口冲突
```bash
# 检查端口占用
lsof -i :5432
lsof -i :6379

# 停止占用端口的服务
sudo lsof -ti:5432 | xargs kill -9
```

#### 2. 容器启动失败
```bash
# 查看容器日志
docker logs supplynexus-postgres-local
docker logs supplynexus-redis-local

# 检查容器状态
docker ps -a | grep supplynexus
```

#### 3. 数据库连接失败
```bash
# 测试 PostgreSQL 连接
docker exec supplynexus-postgres-local psql -U supplynexus_admin -d supplynexus

# 测试 Redis 连接
docker exec supplynexus-redis-local redis-cli -a your-password ping
```

#### 4. 权限问题
```bash
# 确保脚本有执行权限
chmod +x deployment/docker/postgresql/deploy.sh
chmod +x deployment/docker/redis/deploy.sh
chmod +x deployment/scripts/infra.sh
```

### 重置环境

```bash
# 完全重置本地环境
./deployment/scripts/infra.sh local all reset

# 或分别重置
./deployment/scripts/infra.sh local postgres reset
./deployment/scripts/infra.sh local redis reset
```

## 📊 监控和维护

### 数据备份

```bash
# PostgreSQL 备份
docker exec supplynexus-postgres-local pg_dump -U supplynexus_admin -d supplynexus > backup.sql

# Redis 备份
docker exec supplynexus-redis-local redis-cli -a your-password BGSAVE
```

### 性能监控

```bash
# 查看容器资源使用
docker stats supplynexus-postgres-local supplynexus-redis-local

# 查看服务状态
./deployment/scripts/infra.sh local all status
```

## 🎯 最佳实践

1. **环境隔离**：不同环境使用不同的端口和数据库
2. **配置管理**：敏感信息只存储在环境文件中
3. **迁移管理**：本地开发生成迁移，环境部署应用迁移
4. **监控日志**：定期检查容器日志
5. **备份策略**：定期备份数据库和配置文件
6. **测试验证**：部署前在测试环境验证

## 📝 相关文档

- [架构说明](./ARCHITECTURE.md)
- [数据库设置指南](./DATABASE_SETUP.md)
- [API 文档](../docs/api/)
- [开发指南](../docs/development/)
