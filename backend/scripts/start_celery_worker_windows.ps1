# Celery Worker 启动脚本 (Windows 专用)
# 解决 Windows 上 prefork 进程池权限问题

param(
    [string]$LogLevel = "info",
    [string]$Queues = "default,shopify,orders,order_automation",
    [int]$Concurrency = 4
)

Write-Host "🔄 启动 Celery Worker (Windows 兼容模式)..." -ForegroundColor Cyan

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

# 设置环境变量
$env:PYTHONPATH = "."
# Windows 上强制使用 solo 池（单进程模式）
$env:CELERY_WORKER_POOL = "solo"

Write-Host "   📋 配置信息:" -ForegroundColor Cyan
Write-Host "      - 进程池: solo (Windows 兼容模式)" -ForegroundColor Gray
Write-Host "      - 日志级别: $LogLevel" -ForegroundColor Gray
Write-Host "      - 队列: $Queues" -ForegroundColor Gray
Write-Host "      - 并发数: $Concurrency" -ForegroundColor Gray
Write-Host ""

# 启动 Celery Worker
# 使用 --pool=solo 避免 Windows 上的权限问题
celery -A app.tasks.celery_app worker `
    --loglevel=$LogLevel `
    --pool=solo `
    --concurrency=$Concurrency `
    -Q $Queues

