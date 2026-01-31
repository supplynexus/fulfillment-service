# 🚀 本地开发快速启动指南

## ✅ 前置检查

### 1. 检查 PostgreSQL
```powershell
# 检查服务状态
Get-Service | Where-Object {$_.Name -like "*postgres*"}

# 或手动启动
net start postgresql-x64-XX
```

### 2. 检查 Redis/Memurai
```powershell
# 使用管理脚本
cd backend\scripts
.\redis_control.ps1 status

# 如果未运行，启动它
.\redis_control.ps1 start

# 测试连接
.\redis_control.ps1 test
```

## 📝 配置环境变量

创建 `backend/.env.local` 文件：

```bash
# 数据库配置（根据你的实际配置修改）
DATABASE_URL=postgresql+asyncpg://用户名:密码@localhost:5432/supplynexus
DATABASE_URL_SYNC=postgresql://用户名:密码@localhost:5432/supplynexus

# Redis配置（默认即可，Memurai已自动配置）
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# 安全配置
SECRET_KEY=dev-secret-key-change-in-prod
HASHIDS_SALT=dev-hashids-salt-change-in-prod
HEALTH_CHECK_API_KEY=dev-health-check-key
SYSTEM_API_KEY=dev-system-api-key
WEBHOOK_SECRET=dev-webhook-secret

# 环境
ENVIRONMENT=dev
```

## 🎯 启动步骤

### 1. 启动基础设施

```powershell
# 启动 PostgreSQL（如果未运行）
net start postgresql-x64-XX

# 启动 Redis/Memurai
cd backend\scripts
.\redis_control.ps1 start
```

### 2. 运行数据库迁移

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
alembic upgrade head
```

### 3. 启动后端API

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 启动Celery（可选，用于定时任务）

**终端1 - Celery Beat**
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
celery -A app.tasks.celery_app beat --loglevel=info
```

**终端2 - Celery Worker**
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
celery -A app.tasks.celery_app worker --loglevel=info -Q default,shopify,orders,order_automation
```

### 5. 启动前端

```powershell
cd frontend
npm install  # 首次运行
npm run dev
```

## 🔍 验证

- **后端API**: http://localhost:8000/docs
- **前端应用**: http://localhost:3000
- **Redis测试**: `cd backend; python scripts/test_redis_connection.py`

## 🛠️ 常用命令

### Redis管理
```powershell
cd backend\scripts
.\redis_control.ps1 start    # 启动
.\redis_control.ps1 stop     # 停止
.\redis_control.ps1 restart  # 重启
.\redis_control.ps1 status   # 状态
.\redis_control.ps1 test     # 测试连接
```

### Celery管理
```powershell
# 查看Worker状态
celery -A app.tasks.celery_app inspect active

# 查看调度任务
celery -A app.tasks.celery_app inspect scheduled
```

## ⚠️ 注意事项

1. **Redis必须运行**: Celery需要Redis，确保Memurai服务运行
2. **数据库迁移**: 首次启动前运行 `alembic upgrade head`
3. **端口占用**: 确保8000、3000、6379端口未被占用
4. **环境变量**: 确保 `.env.local` 配置正确

## 📚 详细文档

- [本地开发环境配置指南](docs/LOCAL_DEVELOPMENT_SETUP.md)
- [Celery后台任务系统](docs/CELERY_BACKGROUND_TASKS.md)

