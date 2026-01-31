#!/bin/bash
# SupplyNexus Celery Beat 部署脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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
    echo "  local       - 本地环境"
    echo "  dev         - 开发环境"
    echo "  stg         - 测试环境"
    echo "  prod        - 生产环境"
    echo ""
    echo "支持的操作:"
    echo "  up          - 启动服务 (默认)"
    echo "  down        - 停止服务"
    echo "  restart     - 重启服务"
    echo "  logs        - 查看日志"
    echo "  status      - 查看状态"
    echo ""
    echo "示例:"
    echo "  $0 dev up        # 启动开发环境"
    echo "  $0 dev down      # 停止开发环境"
    echo "  $0 dev restart   # 重启开发环境"
    echo "  $0 dev logs      # 查看日志"
}

# 检查参数
if [ $# -eq 0 ]; then
    print_error "缺少环境参数"
    show_usage
    exit 1
fi

ENVIRONMENT=$1
ACTION=${2:-up}

# 验证环境参数
case $ENVIRONMENT in
    local|dev|stg|prod)
        print_status "部署环境: $ENVIRONMENT"
        ;;
    *)
        print_error "不支持的环境: $ENVIRONMENT"
        show_usage
        exit 1
        ;;
esac

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

# 设置环境变量
export ENV_FILE="env.$ENVIRONMENT"

# 检查环境文件
ENV_FILE_PATH="../../environments/backend/.env.$ENVIRONMENT"
if [ ! -f "$ENV_FILE_PATH" ]; then
    print_warning "环境文件不存在: $ENV_FILE_PATH"
    print_status "从示例文件创建环境文件..."
    EXAMPLE_FILE="../../environments/backend/env.example"
    if [ -f "$EXAMPLE_FILE" ]; then
        cp "$EXAMPLE_FILE" "$ENV_FILE_PATH"
        print_status "✅ 环境文件已创建: $ENV_FILE_PATH"
        print_warning "请编辑 $ENV_FILE_PATH 文件并配置正确的环境变量"
        print_warning "然后重新运行此脚本"
        exit 1
    else
        print_error "示例文件不存在: $EXAMPLE_FILE"
        exit 1
    fi
fi

print_status "开始操作 SupplyNexus Celery Beat ($ENVIRONMENT 环境, $ACTION 操作)"

# 显示环境文件信息
print_status "环境文件信息:"
echo "  文件: $(basename "$ENV_FILE_PATH")"
echo "  大小: $(ls -lh "$ENV_FILE_PATH" | awk '{print $5}')"
echo "  修改时间: $(ls -lh "$ENV_FILE_PATH" | awk '{print $6, $7, $8}')"

# 确保日志目录存在
LOGS_DIR="logs-$ENVIRONMENT"
if [ ! -d "$LOGS_DIR" ]; then
    print_status "创建日志目录: $LOGS_DIR"
    mkdir -p "$LOGS_DIR"
    touch "$LOGS_DIR/.gitkeep"
fi

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    print_error "Docker 未运行，请先启动 Docker"
    exit 1
fi

# 执行操作
case $ACTION in
    "up")
        print_status "启动 Celery Beat 服务..."
        docker-compose up -d --build
        
        print_status "✅ Celery Beat 服务启动成功！"
        echo ""
        print_status "服务信息:"
        docker-compose ps
        echo ""
        print_status "日志目录: $LOGS_DIR"
        ;;
        
    "down")
        print_status "停止 Celery Beat 服务..."
        docker-compose down
        print_status "✅ 服务已停止"
        ;;
        
    "restart")
        print_status "重启 Celery Beat 服务..."
        docker-compose restart
        print_status "✅ 服务已重启"
        ;;
        
    "logs")
        print_status "查看 Celery Beat 服务日志..."
        docker-compose logs -f celery_beat
        ;;
        
    "status")
        print_status "Celery Beat 服务状态:"
        docker-compose ps
        ;;
esac

print_status "🎉 操作完成！"
