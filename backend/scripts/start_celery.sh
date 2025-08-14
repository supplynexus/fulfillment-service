#!/bin/bash

# 启动 Celery Worker 和 Beat 的脚本

echo "🚀 启动 Celery 服务..."
echo "================================"

# 检查是否在正确的目录
if [ ! -f "app/main.py" ]; then
    echo "❌ 请在 backend 目录下运行此脚本"
    exit 1
fi

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行: python -m venv .venv && source .venv/bin/activate"
    exit 1
fi

# 激活虚拟环境
source .venv/bin/activate

# 设置环境变量
export PYTHONPATH=.
export C_FORCE_ROOT=true

echo "📋 启动选项："
echo "1) 启动 Celery Worker"
echo "2) 启动 Celery Beat (定时任务)"
echo "3) 启动 Celery Worker + Beat (后台运行)"
echo "4) 查看 Celery 状态"
echo "5) 停止所有 Celery 进程"
echo ""

read -p "请选择选项 (1-5): " choice

case $choice in
    1)
        echo "🔄 启动 Celery Worker..."
        celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2 --queues=default,shopify,orders
        ;;
    2)
        echo "⏰ 启动 Celery Beat..."
        celery -A app.tasks.celery_app beat --loglevel=info --scheduler=celery.beat.PersistentScheduler
        ;;
    3)
        echo "🚀 启动 Celery Worker + Beat (后台运行)..."
        
        # 启动 Worker
        nohup celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2 --queues=default,shopify,orders > logs-local/celery-worker.log 2>&1 &
        WORKER_PID=$!
        echo $WORKER_PID > logs-local/celery-worker.pid
        echo "✅ Worker 已启动 (PID: $WORKER_PID)"
        
        # 启动 Beat
        nohup celery -A app.tasks.celery_app beat --loglevel=info --scheduler=celery.beat.PersistentScheduler > logs-local/celery-beat.log 2>&1 &
        BEAT_PID=$!
        echo $BEAT_PID > logs-local/celery-beat.pid
        echo "✅ Beat 已启动 (PID: $BEAT_PID)"
        
        echo "📋 进程信息："
        echo "  - Worker PID: $WORKER_PID (logs-local/celery-worker.log)"
        echo "  - Beat PID: $BEAT_PID (logs-local/celery-beat.log)"
        echo "  - 使用 './scripts/stop_celery.sh' 停止服务"
        ;;
    4)
        echo "📊 Celery 状态："
        celery -A app.tasks.celery_app inspect active
        echo ""
        echo "📋 定时任务："
        celery -A app.tasks.celery_app inspect scheduled
        ;;
    5)
        echo "🛑 停止所有 Celery 进程..."
        
        # 停止 Worker
        if [ -f "logs-local/celery-worker.pid" ]; then
            WORKER_PID=$(cat logs-local/celery-worker.pid)
            if kill -0 $WORKER_PID 2>/dev/null; then
                kill $WORKER_PID
                echo "✅ Worker 已停止 (PID: $WORKER_PID)"
            else
                echo "⚠️  Worker 进程不存在 (PID: $WORKER_PID)"
            fi
            rm -f logs-local/celery-worker.pid
        else
            echo "⚠️  未找到 Worker PID 文件"
        fi
        
        # 停止 Beat
        if [ -f "logs-local/celery-beat.pid" ]; then
            BEAT_PID=$(cat logs-local/celery-beat.pid)
            if kill -0 $BEAT_PID 2>/dev/null; then
                kill $BEAT_PID
                echo "✅ Beat 已停止 (PID: $BEAT_PID)"
            else
                echo "⚠️  Beat 进程不存在 (PID: $BEAT_PID)"
            fi
            rm -f logs-local/celery-beat.pid
        else
            echo "⚠️  未找到 Beat PID 文件"
        fi
        
        # 强制停止所有 celery 进程
        pkill -f "celery.*app.tasks.celery_app" 2>/dev/null && echo "✅ 已强制停止所有 Celery 进程"
        ;;
    *)
        echo "❌ 无效选项，请重新运行脚本"
        exit 1
        ;;
esac

echo ""
echo "✅ 操作完成！"
