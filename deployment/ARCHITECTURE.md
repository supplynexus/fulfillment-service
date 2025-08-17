# SupplyNexus 架构说明

## 🏗️ 架构概述

本项目采用**分层架构**，将基础设施和应用层完全分离：

```
┌─────────────────────────────────────────────────────────────┐
│                    应用层 (Application Layer)                │
├─────────────────────────────────────────────────────────────┤
│  Frontend (Next.js/React)                                   │
│  - 现代化的 Web 应用界面                                     │
│  - 支持多租户认证                                           │
│  - RSA 签名认证机制                                         │
│                                                             │
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
│  - 端口: dev(5433), stg(5434), prod(5435)              │
│  - 独立的环境变量配置                                        │
│  - 独立的数据持久化                                          │
│                                                             │
│  Redis (独立 Docker Compose)                                │
│  - 端口: dev(6380), stg(6381), prod(6382)              │
│  - 独立的环境变量配置                                        │
│  - 独立的数据持久化                                          │
└─────────────────────────────────────────────────────────────┘
```

## 📁 目录结构

```
deployment/
├── docker/                          # 基础设施 Docker 配置
│   ├── postgresql/                  # PostgreSQL 独立配置
│   │   ├── docker-compose.yml      # PostgreSQL Docker Compose
│   │   ├── deploy.sh               # PostgreSQL 部署脚本
│   │   ├── environment.example     # 环境配置模板
│   │   ├── environment.dev         # 开发环境配置（不提交到 git）
│   │   ├── environment.stg     # 测试环境配置（不提交到 git）
│   │   ├── environment.prod        # 生产环境配置（不提交到 git）
│   │   └── data-*/                 # 数据持久化目录
│   │
│   ├── redis/                      # Redis 独立配置
│   │   ├── docker-compose.yml      # Redis Docker Compose
│   │   ├── deploy.sh               # Redis 部署脚本
│   │   ├── environment.example     # 环境配置模板
│   │   ├── environment.dev         # 开发环境配置（不提交到 git）
│   │   ├── environment.stg     # 测试环境配置（不提交到 git）
│   │   ├── environment.prod        # 生产环境配置（不提交到 git）
│   │   └── data-*/                 # 数据持久化目录
│   │
│   ├── frontend/                   # Frontend 独立配置
│   │   ├── docker-compose.yml      # Frontend Docker Compose
│   │   ├── deploy.sh               # Frontend 部署脚本
│   │   ├── README.md               # Frontend 部署文档
│   │   └── logs-*/                 # 各环境日志目录
│   │
│   └── docker-compose.yml          # 总体 Docker Compose（包含所有服务）
│
├── environments/                    # 应用层环境配置
│   ├── env.example                 # 应用环境配置模板
│   ├── env.local                   # 本地环境配置（不提交到 git）
│   ├── env.stg                 # 测试环境配置（不提交到 git）
│   └── env.prod              # 生产环境配置（不提交到 git）
│
└── scripts/                        # 管理脚本
    ├── infra.sh                    # 基础设施管理脚本
    ├── deploy.sh                   # 应用部署脚本
    └── db.py                       # 数据库迁移脚本
```

## 🔄 部署流程

### 1. 基础设施部署

```bash
# 启动所有基础设施服务
./deployment/scripts/infra.sh dev all start

# 或分别启动
./deployment/scripts/infra.sh dev postgres start
./deployment/scripts/infra.sh dev redis start
```

### 2. 应用部署

```bash
# 启动应用（使用已启动的基础设施）
ENV_FILE=deployment/environments/env.local ./deployment/scripts/deploy.sh start
```

### 3. 数据库迁移

```bash
# 运行数据库迁移
ENV_FILE=deployment/environments/env.local python backend/scripts/db.py upgrade
```

## 🌍 环境配置

### 基础设施环境配置

| 环境 | PostgreSQL 端口 | Redis 端口 | 数据库名 | 容器名前缀 |
|------|----------------|------------|----------|------------|
| dev | 5433 | 6380 | supplynexus | supplynexus-postgres-dev |
| stg | 5434 | 6381 | supplynexus | supplynexus-postgres-stg |
| prod | 5435 | 6382 | supplynexus | supplynexus-postgres-prod |

### 应用环境配置

应用层通过环境变量连接到已启动的基础设施：

```bash
# 连接到开发环境基础设施
DATABASE_URL=postgresql+asyncpg://supplynexus_admin:password@localhost:5433/supplynexus
REDIS_URL=redis://:password@localhost:6380/0
```

## 🔧 管理命令

### 基础设施管理

```bash
# 查看帮助
./deployment/scripts/infra.sh

# 启动所有基础设施
./deployment/scripts/infra.sh dev all start

# 查看状态
./deployment/scripts/infra.sh dev all status

# 停止服务
./deployment/scripts/infra.sh dev postgres stop
./deployment/scripts/infra.sh dev redis stop

# 重置数据
./deployment/scripts/infra.sh dev all reset
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

## 🔒 安全特性

### 环境隔离

- **端口隔离**：不同环境使用不同端口
- **数据隔离**：每个环境独立的数据目录
- **网络隔离**：独立的 Docker 网络

### 配置管理

- **基础设施配置**：`deployment/docker/*/environment.*`
- **应用配置**：`deployment/environments/env.*`
- **所有配置文件**：不提交到 git，手动编辑

### 密码管理

- **PostgreSQL 密码**：在基础设施配置中设置
- **Redis 密码**：在基础设施配置中设置
- **应用密钥**：在应用环境配置中设置

## 📋 首次设置流程

### 1. 配置基础设施

```bash
# PostgreSQL 配置
cd deployment/docker/postgresql
cp environment.example environment.dev
vim environment.dev  # 编辑密码和配置

# Redis 配置
cd ../redis
cp environment.example environment.dev
vim environment.dev  # 编辑密码和配置
```

### 2. 配置应用

```bash
# 应用配置
cd ../../environments
cp env.example env.local
vim env.local  # 编辑连接信息和 API 密钥
```

### 3. 启动服务

```bash
# 启动基础设施
./deployment/scripts/infra.sh dev all start

# 启动应用
ENV_FILE=deployment/environments/env.local ./deployment/scripts/deploy.sh start

# 运行数据库迁移
ENV_FILE=deployment/environments/env.local python backend/scripts/db.py upgrade
```

## 🎯 架构优势

1. **职责分离**：基础设施和应用层完全分离
2. **环境隔离**：不同环境完全独立，互不影响
3. **配置灵活**：每个服务有独立的环境变量配置
4. **部署简单**：基础设施启动一次，应用可以多次重启
5. **安全可靠**：敏感配置不提交到 git，手动管理
6. **易于维护**：每个服务独立管理，故障隔离

## 🔄 开发流程

### 本地开发

```bash
# 1. 启动基础设施（一次）
./deployment/scripts/infra.sh dev all start

# 2. 修改代码
vim backend/app/models/user.py

# 3. 生成迁移
python backend/scripts/db.py autogen "添加新字段"

# 4. 应用迁移
ENV_FILE=deployment/environments/env.local python backend/scripts/db.py upgrade

# 5. 重启应用（多次）
ENV_FILE=deployment/environments/env.local ./deployment/scripts/deploy.sh restart
```

### 环境部署

```bash
# 1. 提交代码
git add backend/migrations/versions/
git commit -m "Add new migration"
git push

# 2. 在目标环境执行迁移
ENV_FILE=deployment/environments/env.stg python backend/scripts/db.py upgrade
```
