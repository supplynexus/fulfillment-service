@echo off
REM Celery Worker 启动脚本 (Windows 批处理版本)
REM 解决 Windows 上 prefork 进程池权限问题

echo 🔄 启动 Celery Worker (Windows 兼容模式)...

REM 检查是否在正确的目录
if not exist "app\main.py" (
    echo ❌ 请在 backend 目录下运行此脚本
    exit /b 1
)

REM 检查虚拟环境
if not exist ".venv" (
    echo ❌ 虚拟环境不存在，请先创建: python -m venv .venv
    exit /b 1
)

REM 激活虚拟环境
call .venv\Scripts\activate.bat

REM 设置环境变量
set PYTHONPATH=.
REM Windows 上强制使用 solo 池（单进程模式）
set CELERY_WORKER_POOL=solo

echo    📋 配置信息:
echo       - 进程池: solo (Windows 兼容模式)
echo       - 日志级别: info
echo       - 队列: default,shopify,orders,order_automation
echo       - 并发数: 4
echo.

REM 启动 Celery Worker
REM 使用 --pool=solo 避免 Windows 上的权限问题
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo --concurrency=4 -Q default,shopify,orders,order_automation












