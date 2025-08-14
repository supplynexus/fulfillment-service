# SupplyNexus Fulfillment Service

> Shopify 到 Printify 的订单履约自动化服务 - 为电商品牌提供无缝的按需打印订单处理

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Node.js](https://img.shields.io/badge/node.js-18+-green.svg)
![Docker](https://img.shields.io/badge/docker-compose-blue.svg)

## 📋 项目概述

SupplyNexus Fulfillment Service 是一个全栈的 SaaS 解决方案，专为电商品牌设计，实现 Shopify 订单到 Printify 打印服务的自动化履约流程。

### 🎯 核心功能

- **🔄 自动订单处理**: 接收 Shopify webhook，自动创建 Printify 订单
- **🏢 多租户架构**: 支持多个客户，数据完全隔离
- **🔐 企业级认证**: 基于租户的时间戳签名认证系统
- **📊 实时状态同步**: 订单状态实时更新，包含跟踪信息
- **🛡️ 智能重试机制**: 失败订单自动重试，错误处理
- **🎛️ 管理后台**: 完整的订单监控和客户管理界面
- **⚡ 异步任务队列**: Celery 处理耗时操作，确保响应速度
- **🕐 自动产品同步**: 1分钟自动同步 Shopify 产品数据

### 🔐 认证系统

#### 时间戳签名认证
- **前端认证**: 使用 RSA 私钥生成时间戳签名
- **后端验证**: 使用对应的公钥验证签名和时间戳
- **防重放攻击**: 使用 nonce 机制防止签名重复使用
- **租户隔离**: 每个租户使用独立的密钥对

#### 认证流程
1. 前端使用私钥对请求内容进行签名
2. 发送请求时包含 `X-Tenant-ID` 和 `X-Signature` 头部
3. 后端验证签名、时间戳和 nonce
4. 验证通过后返回租户和用户信息

### 🏗️ 技术架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Shopify       │    │  Frontend       │    │   Printify      │
│   Webhook       │────│  (NextJS)       │    │   API           │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              │
                    ┌─────────────────┐
                    │   Backend       │
                    │   (FastAPI)     │
                    └─────────────────┘
                              │
                    ┌─────────────────┐    ┌─────────────────┐
                    │  PostgreSQL     │    │     Redis       │
                    │  Database       │    │   + Celery      │
                    └─────────────────┘    └─────────────────┘
```

### ⚡ Celery 后台任务系统

#### 系统组件
- **FastAPI Web API 服务** (端口 8000) - 提供 RESTful API 接口
- **Celery Beat** (定时任务调度器) - 根据配置的定时规则触发任务
- **Celery Worker** (任务执行器) - 执行具体的异步任务
- **Redis** (消息代理，端口 6380) - 存储任务队列和结果
- **PostgreSQL** (数据库) - 存储业务数据

#### 定时任务
- **1分钟同步**: `sync-shopify-products-1min` - 每分钟同步 Shopify 产品
- **30分钟同步**: `sync-shopify-products-30min` - 每30分钟同步 Shopify 产品
- **每小时同步**: `sync-shopify-products-hourly` - 每小时同步订单
- **每天全量同步**: `sync-shopify-products-daily` - 每天凌晨2点全量同步

#### 队列说明
- **shopify**: Shopify 相关任务（产品同步、订单同步）
- **default**: 默认任务队列
- **orders**: 订单处理任务

## 🚀 快速开始

### 系统要求

- **Docker** 和 **Docker Compose**
- **Python 3.11+** (开发时)
- **Node.js 18+** (开发时)
- **Git**

### 一键安装开发环境

```bash
# 克隆项目
git clone https://github.com/supplynexus/fulfillment-service.git
cd fulfillment-service

# 运行自动安装脚本
./scripts/dev/setup.sh
```

安装脚本将：
1. ✅ 检查系统依赖
2. ✅ 创建环境配置文件
3. ✅ 安装后端和前端依赖
4. ✅ 初始化数据库
5. ✅ 启动开发环境

### 手动安装

如果自动安装脚本失败，可以手动执行以下步骤：

#### 1. 环境配置

```bash
# 复制环境配置模板
cp environment.example .env

# 编辑环境变量（必须）
vim .env
```

#### 2. 认证配置

```bash
# 生成 RSA 密钥对（前端使用）
cd frontend
./scripts/generate-keys.sh

# 将公钥添加到后端数据库
# 使用管理工具或直接操作数据库
```

**认证配置说明**:
- 前端使用私钥生成签名
- 后端存储对应的公钥用于验证
- 每个租户使用独立的密钥对
- 密钥文件存储在 `frontend/keys/` 目录（不提交到 git）

#### 3. 启动服务

```bash
# 启动开发环境
docker-compose -f docker-compose.dev.yml up -d

# 查看服务状态
docker-compose -f docker-compose.dev.yml ps
```

#### 4. 数据库迁移

```bash
# 使用 Docker 脚本（推荐）
./scripts/db/alembic.sh dev upgrade
```

#### 4. 密钥配置

**重要**: 系统使用 RSA 密钥对进行安全认证，必须配置密钥：

```bash
# 进入frontend目录
cd frontend

# 生成RSA密钥对
mkdir -p keys
openssl genrsa -out keys/frontend_private_key.pem 2048
openssl rsa -in keys/frontend_private_key.pem -pubout -out keys/frontend_public_key.pem

# 插入测试数据（包含密钥注册）
cd ..
python scripts/insert_test_data.py
```

**密钥管理说明**:
- 🔒 **私钥**: 存储在 `frontend/keys/frontend_private_key.pem` (不上传 Git)
- 🔓 **公钥**: 自动注册到 Backend 数据库
- 🔄 **环境差异**: 每个环境需要独立的密钥对
- 📝 **详细说明**: 查看 [Frontend 密钥管理文档](frontend/keys/README.md)

# 或者进入后端容器
docker-compose -f docker-compose.dev.yml exec backend_dev bash
alembic upgrade head
```

## 🌐 服务访问

启动成功后，您可以访问以下服务：

| 服务 | 地址 | 描述 |
|------|------|------|
| 🖥️ **前端管理后台** | http://localhost:3000 | 订单监控和客户管理 |
| 📊 **后端 API** | http://localhost:8000 | RESTful API 服务 |
| 📚 **API 文档** | http://localhost:8000/api/v1/docs | Swagger/OpenAPI 文档 |
| 🌸 **Celery 监控** | http://localhost:5555 | 任务队列监控 (Flower) |
| 🗄️ **PostgreSQL** | localhost:5432 | 数据库服务 |
| ⚡ **Redis** | localhost:6379 | 缓存和消息队列 |

## 📁 项目结构

```
fulfillment-service/
├── backend/                    # Python FastAPI 后端
│   ├── app/
│   │   ├── api/v1/            # API 路由
│   │   ├── core/              # 核心配置
│   │   ├── models/            # 数据模型
│   │   ├── services/          # 业务逻辑
│   │   ├── tasks/             # Celery 任务
│   │   ├── schemas/           # Pydantic 模式
│   │   └── utils/             # 工具函数
│   ├── tests/                 # 测试文件
│   ├── requirements.txt       # Python 依赖
│   └── Dockerfile            # Docker 配置
├── frontend/                   # NextJS 前端
│   ├── src/
│   │   ├── app/              # App Router 页面
│   │   ├── components/       # React 组件
│   │   ├── lib/              # 工具库
│   │   ├── types/            # TypeScript 类型
│   │   └── utils/            # 工具函数
│   ├── package.json          # Node 依赖
│   └── Dockerfile           # Docker 配置
├── shared/                    # 共享类型和工具
├── deployment/               # 部署配置
│   ├── docker/              # Docker 配置
│   ├── environments/        # 环境配置文件
│   └── scripts/             # 部署脚本
├── docs/                    # 项目文档
├── scripts/                 # 开发脚本
├── docker-compose.yml       # 生产环境
├── docker-compose.dev.yml   # 开发环境
└── environment.example      # 环境变量模板
```

## ⚙️ 配置指南

### 环境变量

关键的环境变量配置：

```bash
# Shopify 配置
SHOPIFY_API_KEY=your-shopify-api-key
SHOPIFY_API_SECRET=your-shopify-api-secret

# Printify 配置
PRINTIFY_API_TOKEN=your-printify-api-token

# 安全配置
SECRET_KEY=your-super-secret-key
WEBHOOK_SECRET=your-webhook-secret
HASHIDS_SALT=your-hashids-salt-here
HASHIDS_MIN_LENGTH=8

# 数据库配置
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db
REDIS_URL=redis://host:port/db

# 健康检查配置（必需）
HEALTH_CHECK_API_KEY=your-secure-api-key
HEALTH_CHECK_RATE_LIMIT=10
HEALTH_CHECK_RATE_WINDOW=60
```

### Webhook 配置

在 Shopify 管理后台配置 webhook：

- **URL**: `https://your-domain.com/api/v1/webhooks/shopify/orders/create`
- **Format**: JSON
- **Events**: Order creation
- **Verification**: 使用 WEBHOOK_SECRET

## 🛠️ 开发指南

详细的开发指南请参考：[本地开发环境搭建指南](docs/DEVELOPMENT.md)

### 快速开始

```bash
# 一键安装开发环境
./scripts/dev/setup.sh

# 或者手动安装
cp environment.example .env
docker-compose -f docker-compose.dev.yml up -d
```

### 启动 Celery 后台任务

```bash
# 1. 启动 Web API 服务
cd backend && source .venv/bin/activate && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 2. 启动 Celery Beat (定时任务调度器)
cd backend && source .venv/bin/activate && celery -A app.tasks.celery_app beat --loglevel=info

# 3. 启动 Celery Worker (任务执行器)
cd backend && source .venv/bin/activate && celery -A app.tasks.celery_app worker --loglevel=info -Q shopify,default,orders
```

### 常用命令

```bash
# 启动开发环境
./scripts/dev/start.sh

# 停止开发环境
./scripts/dev/stop.sh

# 数据库迁移
./scripts/db/alembic.sh dev upgrade

# 运行测试
docker-compose -f docker-compose.dev.yml exec backend_dev pytest

# 检查 Celery 任务状态
redis-cli -p 6380 llen shopify
redis-cli -p 6380 llen default

# 检查 Celery 进程
ps aux | grep celery
```

## 🚢 部署

详细的部署指南请参考：[环境部署指南](docs/DEPLOYMENT.md)

### 快速部署

```bash
# 启动开发环境
./deployment/scripts/deploy.sh dev start

# 启动生产环境
./deployment/scripts/deploy.sh prod start

# 运行数据库迁移
./deployment/scripts/deploy.sh dev db-upgrade
```

### 环境说明

- **local** - 本地开发环境
- **dev** - 开发服务器环境
- **staging** - 测试环境
- **production** - 生产环境

### 域名配置

- **开发环境**: `api.dev.supplynexus.store`
- **测试环境**: `api.stg.supplynexus.store`
- **生产环境**: `api.supplynexus.store`

## 📊 监控

### 健康检查

- **基本健康检查**: `GET /api/v1/health`
- **数据库健康检查**: `GET /api/v1/health/db` (需要 API Key)
- **Redis 健康检查**: `GET /api/v1/health/redis` (需要 API Key)
- **完整健康检查**: `GET /api/v1/health/full` (需要 API Key)

### 使用示例

```bash
# 基本健康检查
curl http://localhost:8000/api/v1/health

# 需要认证的健康检查
curl -H "X-API-Key: your-api-key" \
     http://localhost:8000/api/v1/health/db
```

### 日志

- **应用日志**: Docker 容器日志
- **访问日志**: Nginx 访问日志
- **错误跟踪**: Sentry (如已配置)

## 🔍 故障排除

### 常见问题

#### 1. 服务无法启动
```bash
# 检查日志
docker-compose logs backend

# 检查环境变量
docker-compose config

# 重新构建
docker-compose build --no-cache
```

#### 2. 健康检查失败
```bash
# 检查数据库连接
docker-compose exec backend python -c "
from app.core.database import get_async_db
import asyncio
async def test():
    async for db in get_async_db():
        result = await db.execute('SELECT 1')
        print('Database OK')
asyncio.run(test())
"
```

#### 3. 端口冲突
```bash
# 检查端口占用
lsof -i :8000

# 修改端口
BACKEND_PORT=8001 docker-compose up -d
```

#### 4. 数据库连接问题
```bash
# 检查数据库服务
docker-compose ps postgres

# 检查数据库连接
docker-compose exec postgres psql -U supplynexus_admin -d supplynexus -c "SELECT 1;"
```

#### 5. 环境文件问题
```bash
# 检查环境文件是否存在
ls -la .env.*

# 检查环境文件内容
cat .env.local
```

#### 6. Celery 任务不执行
```bash
# 检查 Celery Worker 是否启动
ps aux | grep celery

# 检查队列长度
redis-cli -p 6380 llen shopify
redis-cli -p 6380 llen default

# 重启 Celery 服务
pkill -f celery
cd backend && source .venv/bin/activate
celery -A app.tasks.celery_app beat --loglevel=info &
celery -A app.tasks.celery_app worker --loglevel=info -Q shopify,default,orders &
```

### 调试命令

```bash
# 进入容器
docker-compose exec backend bash

# 检查网络
docker network ls
docker network inspect backend_backend_network

# 检查容器状态
docker-compose ps
docker stats
```

## 📝 API 文档

完整的 API 文档可在以下地址查看：

- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc

### 主要 API 端点

- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/refresh` - 刷新访问令牌
- `POST /api/v1/auth/logout` - 用户登出
- `GET /api/v1/orders` - 获取订单列表（需要租户认证）
- `GET /api/v1/external-systems` - 获取外部系统配置
- `POST /api/v1/webhooks/shopify/orders/create` - Shopify 订单 webhook

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 开发规范

- 遵循 PEP 8 (Python) 和 ESLint (TypeScript)
- 编写测试用例
- 更新相关文档
- 确保所有测试通过

## 📚 详细文档

- [系统架构文档](deployment/ARCHITECTURE.md) - 系统架构和部署设计
- [Celery 后台任务系统](docs/CELERY_BACKGROUND_TASKS.md) - Celery 任务队列系统详细说明
- [健康检查安全配置](backend/docs/HEALTH_CHECK_SECURITY.md) - 健康检查 API 安全配置
- [数据库管理指南](docs/DATABASE_MANAGEMENT.md) - 数据库迁移、备份、恢复操作
- [文档索引](docs/README.md) - 项目文档导航

### 📋 数据库管理详细说明

#### 架构优势
- ✅ **开发体验好**：所有命令都在 `backend/` 目录执行
- ✅ **职责清晰**：数据库迁移属于后端服务
- ✅ **符合微服务架构**：每个服务管理自己的数据库变更
- ✅ **部署简单**：CI/CD 流程更清晰

#### 多环境支持
```bash
# 本地环境
./scripts/db/alembic.sh local upgrade

# 开发环境
./scripts/db/alembic.sh dev upgrade

# 测试环境
./scripts/db/alembic.sh stg upgrade

# 生产环境
./scripts/db/alembic.sh prod upgrade
```

#### 环境差异和工具选择
| 环境 | 工具 | 环境文件路径 | 实际读取文件 | 说明 |
|------|------|--------------|--------------|------|
| **Local** | `./scripts/db/alembic.sh local` | `backend/.env.local` | `backend/.env.local` | 有Python虚拟环境，直接执行alembic |
| **Develop** | `./deployment/scripts/db-docker.sh dev` | `deployment/environments/env.dev` | `deployment/environments/env.dev` | 只有Docker，需要容器化执行 |
| **Staging** | `./deployment/scripts/db-docker.sh stg` | `deployment/environments/env.stg` | `deployment/environments/env.stg` | 只有Docker |
| **Production** | `./deployment/scripts/db-docker.sh prod` | `deployment/environments/env.prod` | `deployment/environments/env.prod` | 只有Docker |

**关键区别**:
- **Local环境**: 有Python虚拟环境，可以直接使用alembic命令
- **服务器环境**: 只有Docker环境，必须使用db-docker.sh脚本

### 🐳 Docker部署详细说明

#### 环境配置
项目支持多个环境配置文件：
- `.env` - 本地开发环境（默认）
- `.env.dev` - 开发环境
- `.env.stg` - 测试环境
- `.env.prod` - 生产环境

#### 日志目录
每个环境都有对应的日志目录：
- `logs-local/` - 本地环境日志
- `logs-dev/` - 开发环境日志
- `logs-stg/` - 测试环境日志
- `logs-prod/` - 生产环境日志

#### 必需的环境变量
```bash
# 数据库配置
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database

# Redis 配置
REDIS_URL=redis://host:port/database

# 健康检查配置（必需）
HEALTH_CHECK_API_KEY=your-secure-api-key
HEALTH_CHECK_RATE_LIMIT=10
HEALTH_CHECK_RATE_WINDOW=60
```

## 📞 支持

如果您遇到问题或需要帮助：

- 📧 **邮箱**: support@supplynexus.store
- 📱 **GitHub Issues**: [创建 Issue](https://github.com/supplynexus/fulfillment-service/issues)
- 📚 **文档**: 查看 `docs/` 目录下的详细文档

## 📄 许可证

本项目基于 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

**由 SupplyNexus 团队用 ❤️ 开发**