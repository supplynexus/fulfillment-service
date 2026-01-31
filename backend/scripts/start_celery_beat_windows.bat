@echo off
REM Celery Beat 启动脚本 (Windows 批处理版本)
REM 解决 Windows 上 dbm.gnu 不兼容的问题

echo ⏰ 启动 Celery Beat (Windows 兼容模式)...

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

REM 设置环境变量强制使用 dbm.dumb
set CELERY_BEAT_SCHEDULE_FILENAME=celerybeat-schedule
set PYTHONPATH=.
set SHELVE_USE_DBMDUMB=1

REM 删除可能损坏的调度文件（如果存在）
if exist "celerybeat-schedule" (
    del /f /q "celerybeat-schedule" 2>nul
    if %ERRORLEVEL%==0 (
        echo    ✅ 已删除旧的调度文件: celerybeat-schedule
    )
)

if exist "celerybeat-schedule-shm" (
    del /f /q "celerybeat-schedule-shm" 2>nul
)

if exist "celerybeat-schedule-wal" (
    del /f /q "celerybeat-schedule-wal" 2>nul
)

echo    📋 配置信息:
echo       - 调度器: PersistentScheduler (使用 dbm.dumb)
echo       - 日志级别: info
echo       - 调度文件: celerybeat-schedule
echo.

REM 启动 Celery Beat
celery -A app.tasks.celery_app beat --loglevel=info

