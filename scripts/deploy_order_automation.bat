@echo off
REM 订单自动化功能部署脚本 (Windows版本)
REM 用于在Docker环境中部署新的订单自动化功能

echo 🚀 开始部署订单自动化功能...

REM 检查Docker是否运行
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker未运行，请先启动Docker Desktop
    exit /b 1
)

REM 检查docker-compose文件是否存在
if not exist "docker-compose.yml" (
    echo ❌ docker-compose.yml文件不存在
    exit /b 1
)

echo 📦 构建新的Docker镜像...

REM 构建后端镜像
echo 构建后端镜像...
docker-compose build backend

REM 构建Celery Worker镜像
echo 构建Celery Worker镜像...
docker-compose build celery-worker

REM 构建Celery Beat镜像
echo 构建Celery Beat镜像...
docker-compose build celery-beat

echo 🔄 停止现有服务...

REM 停止相关服务
docker-compose stop backend celery-worker celery-beat

echo 🗄️ 运行数据库迁移...

REM 运行数据库迁移
docker-compose run --rm backend python -m alembic upgrade head

echo 🚀 启动服务...

REM 启动服务
docker-compose up -d backend celery-worker celery-beat

echo ⏳ 等待服务启动...
timeout /t 10 /nobreak >nul

echo 🔍 检查服务状态...

REM 检查服务状态
docker-compose ps

echo 📊 检查服务健康状态...

REM 检查后端服务健康状态
curl -f http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ 后端服务运行正常
) else (
    echo ❌ 后端服务启动失败
    docker-compose logs backend
    exit /b 1
)

echo 🎉 订单自动化功能部署完成！
echo.
echo 📋 部署的功能包括：
echo   - Shopify订单自动同步
echo   - 自动创建SCM订单
echo   - 自动调用Printify API
echo   - 订单状态自动同步
echo   - Shopify履约状态自动更新
echo.
echo 🔧 可用的API端点：
echo   - POST /api/v1/automation/process-shopify-orders
echo   - POST /api/v1/automation/sync-printify-status
echo   - POST /api/v1/automation/sync-shopify-fulfillment
echo   - POST /api/v1/automation/sync-all
echo   - GET /api/v1/automation/task-status/{task_id}
echo.
echo 📝 查看日志：
echo   docker-compose logs -f backend
echo   docker-compose logs -f celery-worker
echo   docker-compose logs -f celery-beat
