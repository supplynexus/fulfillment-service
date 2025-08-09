# SupplyNexus Fulfillment Service

Shopify 到 Printify 的订单履约自动化服务 - 为电商品牌提供无缝的按需打印订单处理。

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Node.js](https://img.shields.io/badge/node.js-18+-green.svg)
![Docker](https://img.shields.io/badge/docker-compose-blue.svg)

## 📋 项目概述

SupplyNexus Fulfillment Service 是一个全栈的 SaaS 解决方案，专为电商品牌设计，实现 Shopify 订单到 Printify 打印服务的自动化履约流程。

### 🎯 核心功能

- **自动订单处理**: 接收 Shopify webhook，自动创建 Printify 订单
- **多租户架构**: 支持多个客户，数据完全隔离
- **实时状态同步**: 订单状态实时更新，包含跟踪信息
- **智能重试机制**: 失败订单自动重试，错误处理
- **管理后台**: 完整的订单监控和客户管理界面
- **异步任务队列**: Celery 处理耗时操作，确保响应速度

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
./scripts/development/setup.sh
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

#### 2. 启动服务

```bash
# 启动开发环境
docker-compose -f docker-compose.dev.yml up -d

# 查看服务状态
docker-compose -f docker-compose.dev.yml ps
```

#### 3. 数据库迁移

```bash
# 进入后端容器
docker-compose -f docker-compose.dev.yml exec backend_dev bash

# 运行迁移
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
├── database/                  # 数据库相关
│   ├── migrations/           # Alembic 迁移
│   └── seeds/               # 初始数据
├── deployment/               # 部署配置
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

# 数据库配置
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db
REDIS_URL=redis://host:port/db
```

### Webhook 配置

在 Shopify 管理后台配置 webhook：

- **URL**: `https://your-domain.com/api/v1/webhooks/shopify/orders/create`
- **Format**: JSON
- **Events**: Order creation
- **Verification**: 使用 WEBHOOK_SECRET

## 🛠️ 开发指南

### 开发命令

```bash
# 启动开发环境
./scripts/development/start.sh

# 停止开发环境
./scripts/development/stop.sh

# 查看日志
docker-compose -f docker-compose.dev.yml logs -f [service_name]

# 进入容器
docker-compose -f docker-compose.dev.yml exec backend_dev bash
docker-compose -f docker-compose.dev.yml exec frontend_dev sh
```

### 数据库操作

```bash
# 创建新的迁移
alembic revision --autogenerate -m "Description"

# 应用迁移
alembic upgrade head

# 查看迁移历史
alembic history
```

### 后端开发

```bash
# 安装依赖
cd backend
pip install -r requirements.txt

# 运行测试
pytest

# 代码格式化
black app/
isort app/
flake8 app/
```

### 前端开发

```bash
# 安装依赖
cd frontend
npm install

# 开发模式
npm run dev

# 类型检查
npm run type-check

# 代码格式化
npm run lint:fix
```

## 🧪 测试

### 运行测试

```bash
# 后端测试
docker-compose -f docker-compose.dev.yml exec backend_dev pytest

# 前端测试
docker-compose -f docker-compose.dev.yml exec frontend_dev npm test

# 集成测试
docker-compose -f docker-compose.dev.yml exec backend_dev pytest tests/integration/
```

### 测试覆盖率

```bash
# 后端覆盖率
pytest --cov=app tests/

# 前端覆盖率
npm run test:coverage
```

## 🚢 部署

### 生产环境部署

```bash
# 构建和启动生产环境
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 环境配置

生产环境需要更新的配置：

- ✅ 更强的 `SECRET_KEY`
- ✅ 生产数据库连接
- ✅ 真实的 API 凭证
- ✅ 正确的域名和 CORS 设置
- ✅ Sentry 错误跟踪
- ✅ 邮件通知配置

## 📊 监控

### 健康检查

- **Backend**: `GET /health`
- **Frontend**: `GET /`
- **Celery**: 通过 Flower 界面

### 日志

- **应用日志**: Docker 容器日志
- **访问日志**: Nginx 访问日志
- **错误跟踪**: Sentry (如已配置)

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

## 📝 API 文档

完整的 API 文档可在以下地址查看：

- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc

### 主要 API 端点

- `POST /api/v1/auth/login` - 用户登录
- `GET /api/v1/customers` - 获取客户列表
- `POST /api/v1/customers` - 创建客户
- `GET /api/v1/orders` - 获取订单列表
- `POST /api/v1/webhooks/shopify/orders/create` - Shopify 订单 webhook

## 📞 支持

如果您遇到问题或需要帮助：

- 📧 **邮箱**: support@supplynexus.store
- 📱 **GitHub Issues**: [创建 Issue](https://github.com/supplynexus/fulfillment-service/issues)
- 📚 **文档**: 查看 `docs/` 目录下的详细文档

## 📄 许可证

本项目基于 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

**由 SupplyNexus 团队用 ❤️ 开发**