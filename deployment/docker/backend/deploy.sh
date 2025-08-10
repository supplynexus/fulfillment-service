#!/bin/bash
# SupplyNexus Backend 部署脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 函数定义
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示使用方法
show_usage() {
    echo "用法: $0 <environment> [action]"
    echo ""
    echo "支持的环境:"
    echo "  local       - 本地环境 (端口: 8000)"
    echo "  development - 开发环境 (端口: 8001)"
    echo "  staging     - 测试环境 (端口: 8002)"
    echo "  production  - 生产环境 (端口: 8003)"
    echo ""
    echo "支持的操作:"
    echo "  up          - 启动服务 (默认)"
    echo "  down        - 停止服务"
    echo "  restart     - 重启服务"
    echo "  logs        - 查看日志"
    echo "  status      - 查看状态"
    echo ""
    echo "示例:"
    echo "  $0 local up        # 启动本地环境"
    echo "  $0 local down      # 停止本地环境"
    echo "  $0 local restart   # 重启本地环境"
    echo "  $0 local logs      # 查看本地环境日志"
    echo "  $0 local status    # 查看本地环境状态"
}

# 检查参数
if [ $# -eq 0 ]; then
    print_error "缺少环境参数"
    show_usage
    exit 1
fi

ENVIRONMENT=$1
ACTION=${2:-up}

# 验证操作参数
case $ACTION in
    up|down|restart|logs|status)
        print_status "操作: $ACTION"
        ;;
    *)
        print_error "不支持的操作: $ACTION"
        show_usage
        exit 1
        ;;
esac

# 验证环境参数
case $ENVIRONMENT in
    local|development|staging|production)
        print_status "部署环境: $ENVIRONMENT"
        ;;
    *)
        print_error "不支持的环境: $ENVIRONMENT"
        show_usage
        exit 1
        ;;
esac

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")/backend"

print_status "Backend 目录: $BACKEND_DIR"

# 检查 backend 目录是否存在
if [ ! -d "$BACKEND_DIR" ]; then
    print_error "Backend 目录不存在: $BACKEND_DIR"
    exit 1
fi

# 检查环境文件
ENV_FILE="$BACKEND_DIR/.env.$ENVIRONMENT"
if [ ! -f "$ENV_FILE" ]; then
    print_error "环境文件不存在: $ENV_FILE"
    print_status "可用的环境文件:"
    ls -la "$BACKEND_DIR"/.env.* 2>/dev/null || echo "No .env files found"
    exit 1
fi

print_status "开始操作 SupplyNexus Backend ($ENVIRONMENT 环境, $ACTION 操作)"

# 切换到 backend 目录
cd "$BACKEND_DIR"

# 显示环境文件信息
print_status "环境文件信息:"
echo "  文件: $(basename "$ENV_FILE")"
echo "  大小: $(ls -lh "$ENV_FILE" | awk '{print $5}')"
echo "  修改时间: $(ls -lh "$ENV_FILE" | awk '{print $6, $7, $8}')"

# 复制环境文件到 .env
print_status "复制环境文件到 .env"
cp "$ENV_FILE" "${BACKEND_DIR}/.env"

# 确保日志目录存在
LOGS_DIR="logs-$ENVIRONMENT"
if [ ! -d "$LOGS_DIR" ]; then
    print_status "创建日志目录: $LOGS_DIR"
    mkdir -p "$LOGS_DIR"
    touch "$LOGS_DIR/.gitkeep"
fi

# 设置环境变量
export ENVIRONMENT=$ENVIRONMENT

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    print_error "Docker 未运行，请先启动 Docker"
    exit 1
fi

# 执行操作
case $ACTION in
    "up")
        # 停止现有服务（如果存在）
        if [ "$(docker-compose ps -q)" ]; then
            print_status "停止现有服务..."
            docker-compose down
        fi

        # 构建并启动服务
        print_status "构建并启动 Backend 服务..."
        docker-compose up --build -d

        # 获取端口配置（从环境文件或默认值）
        if grep -q "BACKEND_PORT" .env; then
            BACKEND_PORT=$(grep BACKEND_PORT .env | cut -d'=' -f2)
        else
            BACKEND_PORT="8000"
        fi
        print_status "使用端口: $BACKEND_PORT"

        # 等待服务启动
        print_status "等待服务启动..."
        timeout=60
        counter=0
        while [ $counter -lt $timeout ]; do
            if curl -f http://localhost:${BACKEND_PORT}/api/v1/health > /dev/null 2>&1; then
                print_status "✅ 服务已就绪！"
                break
            fi
            sleep 2
            counter=$((counter + 2))
            echo -n "."
        done

        if [ $counter -ge $timeout ]; then
            print_error "❌ 服务启动超时 (${timeout}s)"
            print_status "查看日志:"
            docker-compose logs backend
            exit 1
        fi

        # 检查服务状态
        if docker-compose ps | grep -q "Up"; then
            print_status "✅ Backend 服务启动成功！"
            echo ""
            print_status "服务信息:"
            docker-compose ps
            echo ""
            print_status "连接信息:"
            echo "  API: http://localhost:${BACKEND_PORT}"
            echo "  API 文档: http://localhost:${BACKEND_PORT}/api/v1/docs"
            echo "  健康检查: http://localhost:${BACKEND_PORT}/api/v1/health"
            echo "  日志目录: $LOGS_DIR"
        else
            print_error "❌ 服务启动失败"
            print_status "查看日志:"
            docker-compose logs backend
            exit 1
        fi
        ;;
        
    "down")
        print_status "停止 Backend 服务..."
        docker-compose down
        print_status "✅ 服务已停止"
        ;;
        
    "restart")
        print_status "重启 Backend 服务..."
        docker-compose restart
        print_status "✅ 服务已重启"
        ;;
        
    "logs")
        print_status "查看 Backend 服务日志..."
        docker-compose logs -f backend
        ;;
        
    "status")
        print_status "Backend 服务状态:"
        docker-compose ps
        ;;
esac

print_status "🎉 操作完成！"
