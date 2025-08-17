#!/bin/bash
# SupplyNexus Redis 部署脚本

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
    echo "环境参数:"
    echo "  local    - 本地环境 (端口: 6379)"
    echo "  dev      - 开发环境 (端口: 6380)"
    echo "  stg      - 测试环境 (端口: 6381)"
    echo "  prod     - 生产环境 (端口: 6382)"
    echo ""
    echo "操作参数:"
    echo "  up       - 启动服务"
    echo "  down     - 停止服务"
    echo "  restart  - 重启服务"
    echo "  logs     - 查看日志"
    echo "  status   - 查看状态"
    echo ""
    echo "示例:"
    echo "  $0 dev up        # 启动开发环境"
    echo "  $0 dev down      # 停止开发环境"
    echo "  $0 dev restart   # 重启开发环境"
    echo "  $0 dev logs      # 查看日志"
    echo "  $0 dev status    # 查看状态"
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

# 检查环境文件
ENV_FILE="../../environments/infrastructure/redis/env.$ENVIRONMENT"
if [ ! -f "$ENV_FILE" ]; then
    print_warning "环境文件不存在: $ENV_FILE"
    print_status "从示例文件创建环境文件..."
    EXAMPLE_FILE="../../environments/infrastructure/redis/env.example"
    if [ -f "$EXAMPLE_FILE" ]; then
        cp "$EXAMPLE_FILE" "$ENV_FILE"
        print_status "✅ 环境文件已创建: $ENV_FILE"
        print_warning "请编辑 $ENV_FILE 文件并配置正确的环境变量"
        print_warning "然后重新运行此脚本"
        exit 1
    else
        print_error "示例文件不存在: $EXAMPLE_FILE"
        exit 1
    fi
fi

print_status "开始操作 SupplyNexus Redis ($ENVIRONMENT 环境, $ACTION 操作)"

# 显示环境文件信息
print_status "环境文件信息:"
echo "  文件: $(basename "$ENV_FILE")"
echo "  大小: $(ls -lh "$ENV_FILE" | awk '{print $5}')"
echo "  修改时间: $(ls -lh "$ENV_FILE" | awk '{print $6, $7, $8}')"

# 复制环境配置
print_status "复制环境配置: $ENV_FILE -> .env"
cp "$ENV_FILE" .env

# 确保数据目录存在
DATA_DIR=$(grep DATA_DIR .env | cut -d'=' -f2)
if [ -n "$DATA_DIR" ] && [ ! -d "$DATA_DIR" ]; then
    print_status "创建数据目录: $DATA_DIR"
    mkdir -p "$DATA_DIR"
fi

# 检查密码是否已修改
if grep -q "your-secure-redis-password-here-change-this" .env; then
    print_warning "检测到默认密码，请修改 .env 文件中的 REDIS_PASSWORD"
    print_warning "按任意键继续，或 Ctrl+C 退出..."
    read -n 1 -s
fi

# 执行操作
case $ACTION in
    "up")
        # 停止现有服务（如果存在）
        if [ "$(docker-compose ps -q)" ]; then
            print_status "停止现有服务..."
            docker-compose down
        fi
        
        # 启动服务
        print_status "启动 Redis 服务..."
        docker-compose up -d
        
        # 等待服务启动
        print_status "等待服务启动..."
        sleep 5
        
        # 检查服务状态
        if docker-compose ps | grep -q "Up"; then
            print_status "✅ Redis 服务启动成功！"
            echo ""
            print_status "服务信息:"
            docker-compose ps
            echo ""
            print_status "连接信息:"
            CONTAINER_NAME=$(grep CONTAINER_NAME .env | cut -d'=' -f2)
            REDIS_PORT=$(grep REDIS_PORT .env | cut -d'=' -f2)
            echo "  容器名称: $CONTAINER_NAME"
            echo "  端口: $REDIS_PORT"
            echo "  密码: (在 .env 文件中配置)"
        else
            print_error "❌ 服务启动失败"
            print_status "查看日志:"
            docker-compose logs
            exit 1
        fi
        ;;
        
    "down")
        print_status "停止 Redis 服务..."
        docker-compose down
        print_status "✅ Redis 服务已停止"
        ;;
        
    "restart")
        print_status "重启 Redis 服务..."
        docker-compose restart
        print_status "✅ Redis 服务已重启"
        ;;
        
    "logs")
        print_status "查看 Redis 服务日志..."
        docker-compose logs -f
        ;;
        
    "status")
        print_status "Redis 服务状态:"
        docker-compose ps
        ;;
esac

print_status "🎉 操作完成！"
