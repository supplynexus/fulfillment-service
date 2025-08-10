#!/bin/bash

# SupplyNexus Backend 开发模式启动脚本

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

echo "🔄 启动 SupplyNexus Backend 开发模式..."

# 检查是否在正确的目录
if [[ ! -f "$BACKEND_DIR/app/main.py" ]]; then
    echo "❌ 错误：请在 backend 目录下运行此脚本"
    exit 1
fi

# 检查虚拟环境
if [[ ! -d "$BACKEND_DIR/.venv" ]]; then
    echo "❌ 错误：虚拟环境不存在，请先运行 setup.sh"
    exit 1
fi

# 切换到 backend 目录
cd "$BACKEND_DIR"

# 激活虚拟环境
echo "📦 激活虚拟环境..."
source .venv/bin/activate

# 检查依赖
echo "🔍 检查依赖..."
python -c "import uvicorn" 2>/dev/null || {
    echo "❌ 错误：uvicorn 未安装，请运行 pip install -r requirements.txt"
    exit 1
}

# 开发模式参数
HOST=${HOST:-"0.0.0.0"}
PORT=${PORT:-"8000"}

echo "🔄 开发模式启动（自动重载）..."
echo "📍 服务地址：http://$HOST:$PORT"
echo "📚 API 文档：http://$HOST:$PORT/api/v1/docs"
echo "💚 健康检查：http://$HOST:$PORT/api/v1/health"
echo ""

# 启动应用（开发模式）
echo "⏳ 启动中..."
exec python -m uvicorn app.main:app --reload --host "$HOST" --port "$PORT"
