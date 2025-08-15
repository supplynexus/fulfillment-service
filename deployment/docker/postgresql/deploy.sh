#!/bin/bash
# SupplyNexus PostgreSQL 部署脚本

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
    echo "用法: $0 <environment>"
    echo ""
    echo "支持的环境:"
    echo "  local    - 本地环境 (端口: 5432)"
    echo "  dev      - 开发环境 (端口: 5433)"
    echo "  stg  - 测试环境 (端口: 5434)"
    echo "  prod     - 生产环境 (端口: 5435)"
    echo ""
    echo "示例:"
    echo "  $0 local"
    echo "  $0 dev"
    echo "  $0 stg"
    echo "  $0 prod"
}

# 检查参数
if [ $# -eq 0 ]; then
    print_error "缺少环境参数"
    show_usage
    exit 1
fi

ENVIRONMENT=$1

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

# 检查环境文件
ENV_FILE="../../environments/env.$ENVIRONMENT"
if [ ! -f "$ENV_FILE" ]; then
    print_error "环境文件不存在: $ENV_FILE"
    exit 1
fi

print_status "开始部署 SupplyNexus PostgreSQL ($ENVIRONMENT 环境)"

# 复制环境配置
print_status "复制环境配置: $ENV_FILE -> .env"
cp "$ENV_FILE" .env

# 确保数据目录存在
DATA_DIR=$(grep DATA_DIR .env | cut -d'=' -f2)
if [ ! -d "$DATA_DIR" ]; then
    print_status "创建数据目录: $DATA_DIR"
    mkdir -p "$DATA_DIR"
fi

# 检查密码是否已修改
if grep -q "your-secure-password-here-change-this" .env; then
    print_warning "检测到默认密码，请修改 .env 文件中的 POSTGRES_PASSWORD"
    print_warning "按任意键继续，或 Ctrl+C 退出..."
    read -n 1 -s
fi

# 停止现有服务（如果存在）
if [ "$(docker-compose ps -q)" ]; then
    print_status "停止现有服务..."
    docker-compose down
fi

# 启动服务
print_status "启动 PostgreSQL 服务..."
docker-compose up -d

# 等待服务启动
print_status "等待服务启动..."
sleep 5

# 检查服务状态
if docker-compose ps | grep -q "Up"; then
    print_status "✅ PostgreSQL 服务启动成功！"
    echo ""
    print_status "服务信息:"
    docker-compose ps
    echo ""
    print_status "连接信息:"
    CONTAINER_NAME=$(grep CONTAINER_NAME .env | cut -d'=' -f2)
    POSTGRES_PORT=$(grep POSTGRES_PORT .env | cut -d'=' -f2)
    echo "  容器名称: $CONTAINER_NAME"
    echo "  端口: $POSTGRES_PORT"
    echo "  数据库: supplynexus"
    echo "  用户: supplynexus_admin"
else
    print_error "❌ 服务启动失败"
    print_status "查看日志:"
    docker-compose logs
    exit 1
fi

print_status "🎉 部署完成！"
