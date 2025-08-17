#!/bin/bash

# SupplyNexus Frontend Docker Deployment Script
# 用于部署前端 Docker 容器

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 默认配置
DEFAULT_ENVIRONMENT="local"
DEFAULT_VERSION="latest"
DEFAULT_PORT="3000"

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"

# 显示使用方法
show_usage() {
    echo "用法: $0 <environment> [action]"
    echo ""
    echo "支持的环境:"
    echo "  local       - 本地环境 (端口: 3000)"
    echo "  dev         - 开发环境 (端口: 3001)"
    echo "  stg         - 测试环境 (端口: 3002)"
    echo "  prod        - 生产环境 (端口: 3003)"
    echo ""
    echo "支持的操作:"
    echo "  up          - 启动服务 (默认)"
    echo "  down        - 停止服务"
    echo "  restart     - 重启服务"
    echo "  logs        - 查看日志"
    echo "  status      - 查看状态"
    echo "  build       - 构建镜像"
    echo "  deploy      - 构建并启动（完整部署）"
    echo "  cleanup     - 清理资源"
    echo ""
    echo "示例:"
    echo "  $0 local up        # 启动本地环境"
    echo "  $0 dev up          # 启动开发环境"
    echo "  $0 stg up          # 启动测试环境"
    echo "  $0 prod up         # 启动生产环境"
    echo "  $0 local down      # 停止本地环境"
    echo "  $0 local restart   # 重启本地环境"
    echo "  $0 local logs      # 查看本地环境日志"
    echo "  $0 local status    # 查看本地环境状态"
    echo "  $0 local deploy    # 完整部署本地环境"
}

# 检查参数
if [ $# -eq 0 ]; then
    log_error "缺少环境参数"
    show_usage
    exit 1
fi

ENVIRONMENT=$1
ACTION=${2:-up}

# 验证环境参数
case $ENVIRONMENT in
    local|dev|stg|prod)
        log_info "部署环境: $ENVIRONMENT"
        ;;
    *)
        log_error "不支持的环境: $ENVIRONMENT"
        show_usage
        exit 1
        ;;
esac

# 验证操作参数
case $ACTION in
    up|down|restart|logs|status|build|deploy|cleanup)
        log_info "操作: $ACTION"
        ;;
    *)
        log_error "不支持的操作: $ACTION"
        show_usage
        exit 1
        ;;
esac

# 检查环境
check_environment() {
    log_info "检查部署环境..."
    
    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        exit 1
    fi
    
    # 检查 Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装"
        exit 1
    fi
    
    # 检查网络
    if ! docker network ls | grep -q "supplynexus-network"; then
        log_warning "supplynexus-network 网络不存在，正在创建..."
        docker network create supplynexus-network
    fi
    
    # 检查密钥目录
    KEYS_PATH="${KEYS_PATH:-$PROJECT_ROOT/frontend/keys}"
    if [[ ! -d "$KEYS_PATH" ]]; then
        log_warning "密钥目录不存在: $KEYS_PATH"
        mkdir -p "$KEYS_PATH"
        log_warning "请将密钥文件放入 $KEYS_PATH 目录"
    fi
    
    # 检查环境文件
    ENV_FILE="${ENV_FILE:-$PROJECT_ROOT/deployment/environments/frontend/env.$ENVIRONMENT}"
    if [[ ! -f "$ENV_FILE" ]]; then
        log_warning "环境变量文件不存在: $ENV_FILE"
        log_warning "创建默认环境文件..."
        cp "$PROJECT_ROOT/deployment/environments/frontend/env.example" "$ENV_FILE"
        log_warning "请编辑 $ENV_FILE 文件并配置正确的环境变量"
        log_warning "然后重新运行此脚本"
        exit 1
    fi
    
    # 设置密钥路径
    export KEYS_PATH="${KEYS_PATH:-$PROJECT_ROOT/frontend/keys}"
    export ENV_FILE="${ENV_FILE:-$PROJECT_ROOT/deployment/environments/frontend/env.$ENVIRONMENT}"
    
    log_success "环境检查完成"
}

# 设置环境变量
set_environment() {
    export ENVIRONMENT="$ENVIRONMENT"
    export VERSION="${VERSION:-latest}"
    export FRONTEND_PORT="${FRONTEND_PORT:-3000}"
    
    # 根据环境设置API URL
    if [[ "$ENVIRONMENT" == "local" ]]; then
        export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://host.docker.internal:8000}"
        export BACKEND_API_URL="${BACKEND_API_URL:-http://host.docker.internal:8000}"
    else
        export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}"
        export BACKEND_API_URL="${BACKEND_API_URL:-http://localhost:8000}"
    fi
    
    export NEXT_PUBLIC_APP_NAME="${NEXT_PUBLIC_APP_NAME:-SupplyNexus Fulfillment Service}"
    export NEXT_PUBLIC_ENVIRONMENT="${NEXT_PUBLIC_ENVIRONMENT:-$ENVIRONMENT}"
    
    # 设置密钥路径
    export KEYS_PATH="${KEYS_PATH:-$PROJECT_ROOT/frontend/keys}"
    export ENV_FILE="${ENV_FILE:-$PROJECT_ROOT/deployment/environments/frontend/env.$ENVIRONMENT}"
    
    log_info "环境变量设置完成:"
    log_info "  环境: $ENVIRONMENT"
    log_info "  版本: $VERSION"
    log_info "  端口: $FRONTEND_PORT"
    log_info "  API URL: $NEXT_PUBLIC_API_URL"
    log_info "  密钥路径: $KEYS_PATH"
}

# 构建镜像
build_image() {
    log_info "开始构建 Docker 镜像..."
    
    cd "$SCRIPT_DIR"
    
    # 构建镜像
    docker-compose build --no-cache
    
    log_success "Docker 镜像构建完成: supplynexus-frontend:$VERSION"
}

# 启动容器
start_container() {
    log_info "启动前端容器..."
    
    cd "$SCRIPT_DIR"
    
    # 启动容器
    docker-compose up -d
    
    log_success "前端容器已启动"
    log_info "访问地址: http://localhost:$FRONTEND_PORT"
    log_info "健康检查: http://localhost:$FRONTEND_PORT/api/health"
}

# 停止容器
stop_container() {
    log_info "停止前端容器..."
    
    cd "$SCRIPT_DIR"
    docker-compose down
    
    log_success "前端容器已停止"
}

# 重启容器
restart_container() {
    log_info "重启前端容器..."
    
    cd "$SCRIPT_DIR"
    docker-compose restart
    
    log_success "前端容器已重启"
}

# 查看日志
view_logs() {
    log_info "查看容器日志..."
    
    cd "$SCRIPT_DIR"
    docker-compose logs -f frontend
}

# 查看状态
view_status() {
    log_info "查看容器状态..."
    
    cd "$SCRIPT_DIR"
    
    echo "=== 容器状态 ==="
    docker-compose ps
    
    echo ""
    echo "=== 镜像信息 ==="
    docker images | grep supplynexus-frontend
    
    echo ""
    echo "=== 网络信息 ==="
    docker network ls | grep supplynexus
    
    echo ""
    echo "=== 端口使用 ==="
    netstat -tulpn | grep ":$FRONTEND_PORT" || echo "端口 $FRONTEND_PORT 未使用"
}

# 清理资源
cleanup() {
    log_info "清理 Docker 资源..."
    
    cd "$SCRIPT_DIR"
    
    # 停止并删除容器
    docker-compose down --rmi all --volumes --remove-orphans
    
    # 清理未使用的镜像
    docker image prune -f
    
    # 清理未使用的网络
    docker network prune -f
    
    log_success "清理完成"
}

# 完整部署
deploy() {
    log_info "开始完整部署..."
    
    check_environment
    set_environment
    build_image
    start_container
    
    log_success "部署完成！"
    log_info "访问地址: http://localhost:$FRONTEND_PORT"
}

# 主函数
main() {
    case "$ACTION" in
        "build")
            check_environment
            set_environment
            build_image
            ;;
        "start"|"up")
            check_environment
            set_environment
            start_container
            ;;
        "stop"|"down")
            set_environment
            stop_container
            ;;
        "restart")
            set_environment
            restart_container
            ;;
        "logs")
            set_environment
            view_logs
            ;;
        "status")
            set_environment
            view_status
            ;;
        "cleanup")
            set_environment
            cleanup
            ;;
        "deploy")
            deploy
            ;;
        *)
            log_error "未知操作: $ACTION"
            show_usage
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
