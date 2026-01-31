#!/bin/bash

# 停止 Celery 服务的脚本

echo "🛑 停止 Celery 服务..."
echo "================================"

# 检查是否在正确的目录
if [ ! -f "app/main.py" ]; then
    echo "❌ 请在 backend 目录下运行此脚本"
    exit 1
fi

# 激活虚拟环境
source .venv/bin/activate

# 设置环境变量
export PYTHONPATH=.

echo "📋 停止选项："
echo "1) 停止所有 Celery 进程"
echo "2) 查看 Celery 状态"
echo "3) 查看日志"
echo ""

read -p "请选择选项 (1-3): " choice

case $choice in
    1)
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
        
        echo "✅ 所有 Celery 服务已停止"
        ;;
    2)
        echo "📊 Celery 状态："
        celery -A app.tasks.celery_app inspect active
        echo ""
        echo "📋 定时任务："
        celery -A app.tasks.celery_app inspect scheduled
        ;;
    3)
        echo "📋 查看日志："
        echo "1) Worker 日志"
        echo "2) Beat 日志"
        echo "3) 两个日志"
        echo ""
        read -p "请选择 (1-3): " log_choice
        
        case $log_choice in
            1)
                if [ -f "logs-local/celery-worker.log" ]; then
                    echo "📋 Worker 日志："
                    tail -20 logs-local/celery-worker.log
                else
                    echo "❌ 未找到 Worker 日志文件"
                fi
                ;;
            2)
                if [ -f "logs-local/celery-beat.log" ]; then
                    echo "📋 Beat 日志："
                    tail -20 logs-local/celery-beat.log
                else
                    echo "❌ 未找到 Beat 日志文件"
                fi
                ;;
            3)
                if [ -f "logs-local/celery-worker.log" ]; then
                    echo "📋 Worker 日志："
                    tail -10 logs-local/celery-worker.log
                    echo ""
                fi
                if [ -f "logs-local/celery-beat.log" ]; then
                    echo "📋 Beat 日志："
                    tail -10 logs-local/celery-beat.log
                fi
                ;;
            *)
                echo "❌ 无效选项"
                ;;
        esac
        ;;
    *)
        echo "❌ 无效选项，请重新运行脚本"
        exit 1
        ;;
esac

echo ""
echo "✅ 操作完成！"
