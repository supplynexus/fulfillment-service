# 🚀 SupplyNexus OMS 快速开始指南

## 📋 项目概述
SupplyNexus OMS是一个多租户的订单管理系统，集成Shopify和Printify，提供完整的订单管理、发货和库存管理功能。

## 🏗️ 技术栈
- **后端**: FastAPI + PostgreSQL + Redis + Celery
- **前端**: Next.js + TypeScript
- **部署**: Docker + Kubernetes
- **认证**: 基于租户的时间戳签名认证 + JWT + API Key

## ⚡ 快速开始

### 1. 克隆项目
```bash
git clone <repository-url>
cd fulfillment-service
```

### 2. 环境设置
```bash
# 复制环境配置文件
cp environment.example environment.local

# 编辑环境配置
vim environment.local
```

### 3. 启动开发环境
```bash
# 启动所有服务
docker-compose -f docker-compose.dev.yml up -d

# 或者分别启动
docker-compose up -d postgresql
docker-compose up -d redis
```

### 4. 后端设置
```bash
cd backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 运行数据库迁移
alembic upgrade head

# 启动后端服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 前端设置
```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

## 🎯 开发工作流

### 查看任务状态
```bash
# 查看所有任务
./scripts/show_tasks.sh

# 查看特定阶段任务
./scripts/show_tasks.sh 1
```

### 创建新功能分支
```bash
# 确保在develop分支
git checkout develop
git pull origin develop

# 创建新功能分支
./scripts/create_feature_branch.sh <phase> <feature-name>

# 例如：创建JWT认证系统分支
./scripts/create_feature_branch.sh 1 jwt-auth-system
```

### 开发流程
1. 创建功能分支
2. 开发功能
3. 提交代码
4. 创建Pull Request
5. 代码审查
6. 合并到develop

## 📊 项目结构

```
fulfillment-service/
├── backend/                 # FastAPI后端
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务逻辑
│   │   └── tasks/          # Celery任务
│   ├── migrations/         # 数据库迁移
│   └── tests/              # 测试
├── frontend/               # Next.js前端
│   ├── src/
│   │   ├── app/           # 页面路由
│   │   ├── components/    # React组件
│   │   └── lib/           # 工具库
│   └── tests/             # 测试
├── deployment/            # 部署配置
├── docs/                  # 项目文档
└── scripts/               # 开发脚本
```

## 🔧 常用命令

### 开发命令
```bash
# 查看任务状态
./scripts/show_tasks.sh

# 创建功能分支
./scripts/create_feature_branch.sh <phase> <feature>

# 启动开发环境
docker-compose -f docker-compose.dev.yml up -d

# 停止开发环境
docker-compose -f docker-compose.dev.yml down

# 查看日志
docker-compose -f docker-compose.dev.yml logs -f
```

### 后端命令
```bash
cd backend

# 激活虚拟环境
source .venv/bin/activate

# 运行测试
pytest

# 运行代码格式化
black app/
isort app/

# 运行类型检查
mypy app/

# 数据库迁移
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### 数据库迁移命令（按环境）

#### Local环境（有Python虚拟环境）
```bash
# 检查当前状态
./scripts/db/alembic.sh local current

# 查看迁移历史
./scripts/db/alembic.sh local history

# 应用所有迁移
./scripts/db/alembic.sh local upgrade

# 生成新迁移
./scripts/db/alembic.sh local autogen "add new feature"
```

#### Develop/Staging/Production环境（只有Docker）
```bash
# 检查当前状态
./deployment/scripts/db-docker.sh dev current

# 查看迁移历史
./deployment/scripts/db-docker.sh dev history

# 应用所有迁移
./deployment/scripts/db-docker.sh dev upgrade

# 生成新迁移
./deployment/scripts/db-docker.sh dev autogen "add new feature"
```

**环境差异说明**:
- **Local环境**: 有Python虚拟环境，可以直接执行alembic命令
- **服务器环境**: 只有Docker环境，必须使用db-docker.sh脚本

### 前端命令
```bash
cd frontend

# 运行开发服务器
npm run dev

# 构建生产版本
npm run build

# 运行测试
npm test

# 代码格式化
npm run lint
npm run format
```

## 📚 API文档

### 后端API
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 前端应用
- 开发服务器: http://localhost:3000

## 🧪 测试

### 后端测试
```bash
cd backend
pytest

# 运行特定测试
pytest tests/unit/test_auth.py

# 生成覆盖率报告
pytest --cov=app tests/
```

### 前端测试
```bash
cd frontend
npm test

# 运行E2E测试
npm run test:e2e
```

## 🚀 部署

### 开发环境
```bash
# 使用Docker Compose
docker-compose -f docker-compose.dev.yml up -d

# 或使用部署脚本
./scripts/dev/start.sh
```

### 生产环境
```bash
# 使用部署脚本
./scripts/deployment/deploy.sh production
```

## 🔒 环境变量

### 必需的环境变量
```bash
# 数据库
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5433/dbname

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Hashids
HASHIDS_SALT=your-hashids-salt-here
HASHIDS_MIN_LENGTH=8

# Shopify
SHOPIFY_SHOP_NAME=your-shop-name
SHOPIFY_ACCESS_TOKEN=your-access-token

# Printify
PRINTIFY_API_TOKEN=your-api-token
```

## 📞 获取帮助

### 文档
- [开发任务分解](./DEVELOPMENT_TASKS.md)
- [开发工作流](./DEVELOPMENT_WORKFLOW.md)
- [API文档](./api/)

### 问题报告
1. 查看现有Issue
2. 创建新Issue
3. 提供详细的错误信息

### 贡献指南
1. Fork项目
2. 创建功能分支
3. 提交代码
4. 创建Pull Request

## 🎯 下一步

1. 阅读[开发任务分解](./DEVELOPMENT_TASKS.md)了解项目计划
2. 查看[开发工作流](./DEVELOPMENT_WORKFLOW.md)了解开发流程
3. 从Phase 1开始开发认证系统
4. 根据需要创建新的功能分支

## 📈 项目进度

- [x] 项目初始化
- [x] 基础架构搭建
- [x] 开发工作流建立
- [x] Phase 1: 认证和安全基础 ✅
  - [x] 基于租户的JWT认证系统
  - [x] 时间戳签名认证
  - [x] Hashids支持
  - [x] 完整的数据库模型设计
- [ ] Phase 2: 数据获取和同步
- [ ] Phase 3: 核心业务功能
- [ ] Phase 4: 用户界面
- [ ] Phase 5: 多租户完善
