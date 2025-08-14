# SupplyNexus Fulfillment Service - 本地开发环境搭建指南

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

## 🛠️ 手动安装

如果自动安装脚本失败，可以手动执行以下步骤：

### 1. 环境配置

```bash
# 复制环境配置模板
cp environment.example .env

# 编辑环境变量（必须）
vim .env
```

### 2. 启动服务

```bash
# 启动开发环境
docker-compose -f docker-compose.dev.yml up -d

# 查看服务状态
docker-compose -f docker-compose.dev.yml ps
```

### 3. 数据库迁移

```bash
# 使用 Docker 脚本（推荐）
./scripts/db/alembic.sh dev upgrade

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

## ⚡ Celery 后台任务系统

### 系统组件

- **FastAPI Web API 服务** (端口 8000) - 提供 RESTful API 接口
- **Celery Beat** (定时任务调度器) - 根据配置的定时规则触发任务
- **Celery Worker** (任务执行器) - 执行具体的异步任务
- **Redis** (消息代理，端口 6380) - 存储任务队列和结果
- **PostgreSQL** (数据库) - 存储业务数据

### 启动 Celery 服务

```bash
# 1. 启动 Web API 服务
cd backend && source .venv/bin/activate && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 2. 启动 Celery Beat (定时任务调度器)
cd backend && source .venv/bin/activate && celery -A app.tasks.celery_app beat --loglevel=info

# 3. 启动 Celery Worker (任务执行器)
cd backend && source .venv/bin/activate && celery -A app.tasks.celery_app worker --loglevel=info -Q shopify,default,orders
```

### 定时任务配置

- **1分钟同步**: `sync-shopify-products-1min` - 每分钟同步 Shopify 产品
- **30分钟同步**: `sync-shopify-products-30min` - 每30分钟同步 Shopify 产品
- **每小时同步**: `sync-shopify-products-hourly` - 每小时同步订单
- **每天全量同步**: `sync-shopify-products-daily` - 每天凌晨2点全量同步

### 队列说明

- **shopify**: Shopify 相关任务（产品同步、订单同步）
- **default**: 默认任务队列
- **orders**: 订单处理任务

### 监控和调试

```bash
# 检查 Celery 进程
ps aux | grep celery

# 检查 Redis 队列长度
redis-cli -p 6380 llen shopify
redis-cli -p 6380 llen default
redis-cli -p 6380 llen orders

# 查看 Celery 日志
tail -f logs-local/celery-beat.log
tail -f logs-local/celery-worker.log

# 重启 Celery 服务
pkill -f celery
cd backend && source .venv/bin/activate
celery -A app.tasks.celery_app beat --loglevel=info &
celery -A app.tasks.celery_app worker --loglevel=info -Q shopify,default,orders &
```

### 故障排除

#### 常见问题

1. **任务不执行**
   - 检查 Celery Worker 是否启动
   - 检查队列配置是否正确
   - 检查 Redis 连接是否正常

2. **时区问题**
   - 确保所有时间都使用 UTC
   - 检查数据库时区设置

3. **队列堆积**
   - 检查 Worker 是否正常运行
   - 检查任务是否有错误

## 🔧 开发命令

### 快速开始

```bash
# 1. 设置数据库
cp deployment/environments/env.example deployment/environments/env.local
vim deployment/environments/env.local  # 编辑配置
./deployment/scripts/db-setup.sh local start

# 2. 运行数据库迁移
ENV_FILE=deployment/environments/env.local python backend/scripts/db.py upgrade

# 3. 启动开发环境
./scripts/dev/start.sh
```

### 开发命令

```bash
# 启动开发环境
./scripts/dev/start.sh

# 停止开发环境
./scripts/dev/stop.sh

# 重启开发环境
./scripts/dev/restart.sh

# 查看日志
./scripts/dev/logs.sh
```

### 数据库操作

```bash
# 运行迁移
./scripts/db/alembic.sh local upgrade

# 创建新迁移
./scripts/db/alembic.sh local revision --autogenerate -m "描述"

# 回滚迁移
./scripts/db/alembic.sh local downgrade -1

# 查看迁移历史
./scripts/db/alembic.sh local history
```

### 测试

```bash
# 运行所有测试
docker-compose -f docker-compose.dev.yml exec backend_dev pytest

# 运行特定测试
docker-compose -f docker-compose.dev.yml exec backend_dev pytest tests/test_auth.py

# 运行测试并生成覆盖率报告
docker-compose -f docker-compose.dev.yml exec backend_dev pytest --cov=app tests/

# 运行前端测试
cd frontend && npm test
```

### 代码质量

```bash
# Python 代码格式化
docker-compose -f docker-compose.dev.yml exec backend_dev black app/

# Python 代码检查
docker-compose -f docker-compose.dev.yml exec backend_dev flake8 app/

# TypeScript 代码检查
cd frontend && npm run lint

# TypeScript 类型检查
cd frontend && npm run type-check
```

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

## 🔐 认证配置

### RSA 密钥对生成

```bash
# 进入 frontend 目录
cd frontend

# 生成 RSA 密钥对
mkdir -p keys
openssl genrsa -out keys/frontend_private_key.pem 2048
openssl rsa -in keys/frontend_private_key.pem -pubout -out keys/frontend_public_key.pem

# 插入测试数据（包含密钥注册）
cd ..
python scripts/insert_test_data.py
```

### 密钥管理说明

- 🔒 **私钥**: 存储在 `frontend/keys/frontend_private_key.pem` (不上传 Git)
- 🔓 **公钥**: 自动注册到 Backend 数据库
- 🔄 **环境差异**: 每个环境需要独立的密钥对
- 📝 **详细说明**: 查看 [Frontend 密钥管理文档](frontend/keys/README.md)

## 🌐 API 开发

### 创建新的 API 端点

1. 在 `backend/app/api/v1/endpoints/` 创建新的路由文件
2. 在 `backend/app/schemas/` 定义请求/响应模式
3. 在 `backend/app/services/` 实现业务逻辑
4. 在 `backend/app/api/v1/api.py` 注册路由
5. 编写测试用例

### 示例：创建产品 API

```python
# backend/app/api/v1/endpoints/products.py
from fastapi import APIRouter, Depends
from app.schemas.product import ProductCreate, ProductResponse
from app.services.product_service import ProductService

router = APIRouter()

@router.post("/", response_model=ProductResponse)
async def create_product(
    product: ProductCreate,
    product_service: ProductService = Depends()
):
    return await product_service.create_product(product)
```

## 🧪 测试开发

### 单元测试

```python
# backend/tests/unit/test_product_service.py
import pytest
from app.services.product_service import ProductService

class TestProductService:
    @pytest.mark.asyncio
    async def test_create_product(self):
        service = ProductService()
        # 测试逻辑
        pass
```

### 集成测试

```python
# backend/tests/integration/test_product_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_product():
    response = client.post("/api/v1/products/", json={
        "title": "Test Product",
        "description": "Test Description"
    })
    assert response.status_code == 200
```

## 🔍 调试技巧

### 后端调试

```bash
# 进入后端容器
docker-compose -f docker-compose.dev.yml exec backend_dev bash

# 启动调试模式
python -m debugpy --listen 0.0.0.0:5678 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 查看日志
tail -f logs-local/backend.log
```

### 前端调试

```bash
# 进入前端容器
docker-compose -f docker-compose.dev.yml exec frontend_dev bash

# 启动开发服务器
npm run dev

# 查看日志
tail -f logs-local/frontend.log
```

### 数据库调试

```bash
# 连接数据库
docker-compose -f docker-compose.dev.yml exec postgres_dev psql -U supplynexus_admin -d supplynexus

# 查看表结构
\dt

# 查看数据
SELECT * FROM products LIMIT 10;
```

## 📚 相关文档

- [Celery 后台任务系统](docs/CELERY_BACKGROUND_TASKS.md) - Celery 任务队列系统详细说明
- [API 文档](http://localhost:8000/api/v1/docs) - Swagger/OpenAPI 文档
- [数据库管理指南](docs/DATABASE_MANAGEMENT.md) - 数据库操作指南
- [部署指南](docs/DEPLOYMENT.md) - 环境部署指南

## 🆘 常见问题

### 1. 端口冲突

```bash
# 检查端口占用
lsof -i :8000
lsof -i :3000

# 修改端口
BACKEND_PORT=8001 FRONTEND_PORT=3001 docker-compose -f docker-compose.dev.yml up -d
```

### 2. 数据库连接失败

```bash
# 检查数据库服务
docker-compose -f docker-compose.dev.yml ps postgres

# 检查数据库连接
docker-compose -f docker-compose.dev.yml exec postgres_dev psql -U supplynexus_admin -d supplynexus -c "SELECT 1;"
```

### 3. 环境变量问题

```bash
# 检查环境文件
ls -la .env*

# 检查环境变量
docker-compose -f docker-compose.dev.yml config
```

### 4. Celery 任务不执行

```bash
# 检查 Celery 进程
ps aux | grep celery

# 检查 Redis 连接
redis-cli -p 6380 ping

# 检查队列长度
redis-cli -p 6380 llen shopify
```

## 📞 获取帮助

如果您在开发过程中遇到问题：

1. 查看 [故障排除指南](docs/TROUBLESHOOTING.md)
2. 检查 [GitHub Issues](https://github.com/supplynexus/fulfillment-service/issues)
3. 联系开发团队：support@supplynexus.store
