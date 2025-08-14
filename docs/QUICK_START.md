# 🚀 SupplyNexus Fulfillment Service - 快速开始指南

## 📋 项目概述
SupplyNexus Fulfillment Service是一个多租户的订单履行自动化服务，集成Shopify和Printify，提供完整的订单管理、发货和库存管理功能。

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
cp deployment/environments/env.example deployment/environments/env.local

# 编辑环境配置
vim deployment/environments/env.local
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
./scripts/db/alembic.sh local upgrade

# 启动后端服务
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 启动Celery任务队列
```bash
# 启动Celery Worker (新终端)
cd backend
source .venv/bin/activate
./scripts/start_celery.sh

# 启动Celery Beat (新终端)
cd backend
source .venv/bin/activate
celery -A app.tasks.celery_app beat --loglevel=info
```

### 6. 前端设置
```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 7. 验证服务状态
```bash
# 检查健康状态
curl http://localhost:8000/api/v1/health

# 检查API文档
open http://localhost:8000/api/v1/docs
```

## 📋 服务检查清单

### ✅ FastAPI服务
- [ ] 服务启动成功
- [ ] 健康检查端点响应正常
- [ ] API文档可访问
- [ ] 端口8000可访问

### ✅ Celery任务队列
- [ ] Worker进程启动成功
- [ ] Beat进程启动成功
- [ ] 任务队列连接正常
- [ ] 定时任务配置正确

### ✅ 数据库连接
- [ ] PostgreSQL连接正常
- [ ] 数据库迁移完成
- [ ] 表结构正确

### ✅ Redis连接
- [ ] Redis服务运行正常
- [ ] Celery可以连接Redis
- [ ] 缓存功能正常

## 🔧 常用命令

### 服务管理
```bash
# 启动FastAPI
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 启动Celery Worker
./scripts/start_celery.sh

# 启动Celery Beat
celery -A app.tasks.celery_app beat --loglevel=info

# 停止Celery
./scripts/stop_celery.sh
```

### 数据同步
```bash
# 完全重新同步
./scripts/full_resync.sh

# 只同步订单
./scripts/full_resync.sh --orders-only

# 只同步商品
./scripts/full_resync.sh --products-only
```

### 环境检查
```bash
# 检查依赖
python scripts/check_dependencies.py

# 检查数据库
python scripts/db.py
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

## 🐛 故障排除

### 常见问题

#### 1. 端口被占用
```bash
# 查找占用端口的进程
lsof -i :8000

# 杀死进程
kill -9 <PID>
```

#### 2. 数据库连接失败
```bash
# 检查数据库服务
docker ps | grep postgres

# 检查环境变量
echo $DATABASE_URL
```

#### 3. Redis连接失败
```bash
# 检查Redis服务
docker ps | grep redis

# 测试Redis连接
redis-cli ping
```

#### 4. Celery任务不执行
```bash
# 检查Celery状态
celery -A app.tasks.celery_app inspect active

# 检查任务队列
celery -A app.tasks.celery_app inspect stats
```

### 日志查看
```bash
# 查看应用日志
tail -f logs-local/app.log

# 查看Celery日志
tail -f logs-local/celery.log
```

## 📊 监控端点

### 健康检查
- `GET /api/v1/health` - 基本健康检查
- `GET /api/v1/health/db` - 数据库健康检查
- `GET /api/v1/health/redis` - Redis健康检查
- `GET /api/v1/health/full` - 完整健康检查

### 同步状态
- `GET /api/v1/sync/status` - 同步状态
- `GET /api/v1/sync/summary` - 同步摘要
- `GET /api/v1/sync/tasks` - 任务列表

### API文档
- `GET /api/v1/docs` - Swagger UI
- `GET /api/v1/openapi.json` - OpenAPI规范

## 🔐 认证

### API密钥认证
```bash
# 设置API密钥
export API_KEY="your-api-key"

# 使用API密钥访问
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/health/full
```

### 用户认证
```bash
# 用户登录
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=password"
```

## 📝 环境配置

### 必需的环境变量
```bash
# 数据库配置
DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname

# Redis配置
REDIS_URL=redis://localhost:6379/0

# Shopify配置
SHOPIFY_ACCESS_TOKEN=your-access-token
SHOPIFY_STORE_URL=your-store.myshopify.com

# 安全配置
SECRET_KEY=your-secret-key
API_KEY=your-api-key
```

### 配置文件
- `deployment/environments/env.example` - 环境变量示例
- `alembic.ini` - 数据库迁移配置
- `docker-compose.yml` - Docker服务配置

## 🎯 下一步

1. **配置环境变量**: 设置正确的数据库和API密钥
2. **启动服务**: 按照上述步骤启动所有服务
3. **验证功能**: 测试API端点和同步功能
4. **监控状态**: 使用监控端点检查系统状态
5. **部署生产**: 准备生产环境部署

---

**文档版本**: v2.0  
**最后更新**: 2025年8月14日
