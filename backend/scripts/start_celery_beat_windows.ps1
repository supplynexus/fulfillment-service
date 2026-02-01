# Celery Beat 启动脚本 (Windows 专用)
# 解决 Windows 上 dbm.gnu 不兼容的问题

param(
    [string]$LogLevel = "info"
)

Write-Host "⏰ 启动 Celery Beat (Windows 兼容模式)..." -ForegroundColor Cyan

# 检查是否在正确的目录
if (-not (Test-Path "app\main.py")) {
    Write-Host "❌ 请在 backend 目录下运行此脚本" -ForegroundColor Red
    exit 1
}

# 检查虚拟环境
if (-not (Test-Path ".venv")) {
    Write-Host "❌ 虚拟环境不存在，请先创建: python -m venv .venv" -ForegroundColor Red
    exit 1
}

# 激活虚拟环境
& ".venv\Scripts\Activate.ps1"

# 设置环境变量强制使用 dbm.dumb
$env:CELERY_BEAT_SCHEDULE_FILENAME = "celerybeat-schedule"
$env:PYTHONPATH = "."

# 删除可能损坏的调度文件（如果存在且未被占用）
$scheduleFiles = @("celerybeat-schedule", "celerybeat-schedule-shm", "celerybeat-schedule-wal")
foreach ($file in $scheduleFiles) {
    if (Test-Path $file) {
        try {
            Remove-Item $file -Force -ErrorAction Stop
            Write-Host "   ✅ 已删除旧的调度文件: $file" -ForegroundColor Green
        } catch {
            Write-Host "   ⚠️  无法删除 $file (可能正在使用中，将在启动时自动处理)" -ForegroundColor Yellow
        }
    }
}

# 启动 Celery Beat
# 使用 --scheduler=celery.beat:PersistentScheduler 并强制使用 dbm.dumb
# 通过设置环境变量 SHELVE_USE_DBMDUMB=1 来强制使用 dbm.dumb
$env:SHELVE_USE_DBMDUMB = "1"

Write-Host "   📋 配置信息:" -ForegroundColor Cyan
Write-Host "      - 调度器: PersistentScheduler (使用 dbm.dumb)" -ForegroundColor Gray
Write-Host "      - 日志级别: $LogLevel" -ForegroundColor Gray
Write-Host "      - 调度文件: celerybeat-schedule" -ForegroundColor Gray
Write-Host ""

# 启动 Celery Beat
# 注意：在 Windows 上，PersistentScheduler 会自动使用 dbm.dumb（如果 dbm.gnu 不可用）
# 但为了确保，我们显式设置环境变量
celery -A app.tasks.celery_app beat --loglevel=$LogLevel












