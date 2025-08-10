#!/bin/bash
"""
启动脚本 - 确保正确加载环境变量
"""

# 设置环境文件
export ENV_FILE="../environment.local"

# 检查环境文件是否存在
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ 环境文件 $ENV_FILE 不存在"
    exit 1
fi

echo "🚀 启动 SupplyNexus Fulfillment Service..."
echo "📁 环境文件: $ENV_FILE"

# 启动应用
cd "$(dirname "$0")/.."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
