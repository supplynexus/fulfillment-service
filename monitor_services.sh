#!/bin/bash

# 监控后端和前端服务状态
echo "🔍 监控 SupplyNexus 服务状态"
echo "================================"

# 检查后端服务
echo "📡 后端服务 (端口 8000):"
if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo "   ✅ 后端服务正常运行"
    echo "   📊 健康检查: $(curl -s http://localhost:8000/api/v1/health | jq -r '.status' 2>/dev/null || echo 'healthy')"
else
    echo "   ❌ 后端服务无响应"
fi

# 检查前端服务
echo ""
echo "🌐 前端服务 (端口 3000):"
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "   ✅ 前端服务正常运行"
    echo "   📊 响应状态: $(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000)"
else
    echo "   ❌ 前端服务无响应"
fi

# 检查进程状态
echo ""
echo "🔄 进程状态:"
echo "   后端进程: $(ps aux | grep 'uvicorn.*8000' | grep -v grep | wc -l | tr -d ' ') 个"
echo "   前端进程: $(ps aux | grep 'next.*dev' | grep -v grep | wc -l | tr -d ' ') 个"

# 检查端口占用
echo ""
echo "🔌 端口占用:"
echo "   端口 8000: $(lsof -ti:8000 | wc -l | tr -d ' ') 个进程"
echo "   端口 3000: $(lsof -ti:3000 | wc -l | tr -d ' ') 个进程"

echo ""
echo "⏰ 检查时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================"
