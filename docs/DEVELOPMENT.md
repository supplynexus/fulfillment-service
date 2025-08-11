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

# 查看日志
docker-compose -f docker-compose.dev.yml logs -f [service_name]

# 进入容器
docker-compose -f docker-compose.dev.yml exec backend_dev bash
docker-compose -f docker-compose.dev.yml exec frontend_dev sh
```

### 数据库管理

#### 快速参考

```bash
# 查看当前迁移版本
./scripts/db/alembic.sh dev current

# 升级数据库
./scripts/db/alembic.sh dev upgrade

# 生成迁移文件
./scripts/db/alembic.sh dev autogen "描述变更"

# 查看迁移历史
./scripts/db/alembic.sh dev history

# 回退一个版本
./scripts/db/alembic.sh dev downgrade
```

#### 开发环境（有 Python 环境）

```bash
cd backend
source .venv/bin/activate

# 查看当前迁移版本
python scripts/db.py current

# 升级到最新版本
python scripts/db.py upgrade

# 自动生成迁移文件
python scripts/db.py autogen "添加用户表"

# 创建空迁移文件
python scripts/db.py revision "手动迁移"

# 回退一个版本
python scripts/db.py downgrade
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
- `GET /api/v1/customers` - 获取客户列表
- `POST /api/v1/customers` - 创建客户
- `GET /api/v1/orders` - 获取订单列表
- `POST /api/v1/webhooks/shopify/orders/create` - Shopify 订单 webhook

## 📞 支持

如果您遇到问题或需要帮助：

- 📧 **邮箱**: support@supplynexus.store
- 📱 **GitHub Issues**: [创建 Issue](https://github.com/supplynexus/fulfillment-service/issues)
- 📚 **文档**: 查看 `docs/` 目录下的详细文档
