#!/bin/bash

# SupplyNexus 基础设施管理脚本
# 统一管理 PostgreSQL 和 Redis 服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 函数定义
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示使用方法
show_usage() {
    echo "SupplyNexus 基础设施管理脚本"
    echo ""
    echo "用法: $0 <environment> <service> [action]"
    echo ""
    echo "环境 (environment):"
    echo "  dev      - 开发环境"
    echo "  staging  - 测试环境"
    echo "  prod     - 生产环境"
    echo ""
    echo "服务 (service):"
    echo "  postgres - PostgreSQL 数据库"
    echo "  redis    - Redis 缓存"
    echo "  all      - 所有服务"
    echo ""
    echo "操作 (action):"
    echo "  start    - 启动服务 (默认)"
    echo "  stop     - 停止服务"
    echo "  restart  - 重启服务"
    echo "  status   - 查看状态"
    echo "  logs     - 查看日志"
    echo "  reset    - 重置服务 (删除所有数据)"
    echo ""
    echo "示例:"
    echo "  $0 dev postgres start     # 启动开发环境 PostgreSQL"
    echo "  $0 dev redis start        # 启动开发环境 Redis"
    echo "  $0 dev all start          # 启动开发环境所有服务"
    echo "  $0 staging all status     # 查看测试环境所有服务状态"
    echo ""
    echo "首次使用:"
    echo "  1. 配置 PostgreSQL: cd deployment/docker/postgresql && cp environment.example environment.dev"
    echo "  2. 配置 Redis: cd deployment/docker/redis && cp environment.example environment.dev"
    echo "  3. 编辑配置文件，修改密码"
    echo "  4. 启动服务: $0 dev all start"
}

# 检查参数
if [ $# -lt 2 ]; then
    print_error "缺少参数"
    show_usage
    exit 1
fi

ENVIRONMENT=$1
SERVICE=$2
ACTION=${3:-start}

# 验证环境参数
case $ENVIRONMENT in
    dev|staging|prod)
        print_status "目标环境: $ENVIRONMENT"
        ;;
    *)
        print_error "不支持的环境: $ENVIRONMENT"
        show_usage
        exit 1
        ;;
esac

# 验证服务参数
case $SERVICE in
    postgres|redis|all)
        print_status "目标服务: $SERVICE"
        ;;
    *)
        print_error "不支持的服务: $SERVICE"
        show_usage
        exit 1
        ;;
esac

# PostgreSQL 管理函数
manage_postgres() {
    local action=$1
    print_status "管理 PostgreSQL ($action)..."
    
    cd deployment/docker/postgresql
    
    case $action in
        start)
            ./deploy.sh $ENVIRONMENT
            ;;
        stop)
            docker-compose down
            print_success "PostgreSQL 已停止"
            ;;
        restart)
            docker-compose down
            sleep 2
            ./deploy.sh $ENVIRONMENT
            ;;
        status)
            docker-compose ps
            ;;
        logs)
            docker-compose logs -f
            ;;
        reset)
            print_warning "⚠️  这将删除 PostgreSQL 的所有数据！"
            echo "确认重置 PostgreSQL？(y/N)"
            read -r response
            if [[ "$response" =~ ^[Yy]$ ]]; then
                docker-compose down
                DATA_DIR=$(grep DATA_DIR .env | cut -d'=' -f2)
                print_status "删除数据目录: $DATA_DIR"
                rm -rf "$DATA_DIR"
                mkdir -p "$DATA_DIR"
                ./deploy.sh $ENVIRONMENT
                print_success "PostgreSQL 重置完成"
            else
                print_status "取消重置操作"
            fi
            ;;
        *)
            print_error "不支持的操作: $action"
            exit 1
            ;;
    esac
    
    cd - > /dev/null
}

# Redis 管理函数
manage_redis() {
    local action=$1
    print_status "管理 Redis ($action)..."
    
    cd deployment/docker/redis
    
    case $action in
        start)
            ./deploy.sh $ENVIRONMENT
            ;;
        stop)
            docker-compose down
            print_success "Redis 已停止"
            ;;
        restart)
            docker-compose down
            sleep 2
            ./deploy.sh $ENVIRONMENT
            ;;
        status)
            docker-compose ps
            ;;
        logs)
            docker-compose logs -f
            ;;
        reset)
            print_warning "⚠️  这将删除 Redis 的所有数据！"
            echo "确认重置 Redis？(y/N)"
            read -r response
            if [[ "$response" =~ ^[Yy]$ ]]; then
                docker-compose down
                DATA_DIR=$(grep DATA_DIR .env | cut -d'=' -f2)
                print_status "删除数据目录: $DATA_DIR"
                rm -rf "$DATA_DIR"
                mkdir -p "$DATA_DIR"
                ./deploy.sh $ENVIRONMENT
                print_success "Redis 重置完成"
            else
                print_status "取消重置操作"
            fi
            ;;
        *)
            print_error "不支持的操作: $action"
            exit 1
            ;;
    esac
    
    cd - > /dev/null
}

# 主逻辑
case $SERVICE in
    postgres)
        manage_postgres $ACTION
        ;;
    redis)
        manage_redis $ACTION
        ;;
    all)
        case $ACTION in
            start)
                print_status "启动所有基础设施服务..."
                manage_postgres start
                manage_redis start
                print_success "✅ 所有基础设施服务启动完成！"
                ;;
            stop)
                print_status "停止所有基础设施服务..."
                manage_postgres stop
                manage_redis stop
                print_success "✅ 所有基础设施服务已停止！"
                ;;
            restart)
                print_status "重启所有基础设施服务..."
                manage_postgres restart
                manage_redis restart
                print_success "✅ 所有基础设施服务重启完成！"
                ;;
            status)
                print_status "PostgreSQL 状态:"
                manage_postgres status
                echo ""
                print_status "Redis 状态:"
                manage_redis status
                ;;
            logs)
                print_error "不支持同时查看所有服务的日志"
                echo "请分别查看:"
                echo "  $0 $ENVIRONMENT postgres logs"
                echo "  $0 $ENVIRONMENT redis logs"
                exit 1
                ;;
            reset)
                print_warning "⚠️  这将删除所有基础设施的数据！"
                echo "确认重置所有服务？(y/N)"
                read -r response
                if [[ "$response" =~ ^[Yy]$ ]]; then
                    manage_postgres reset
                    manage_redis reset
                    print_success "✅ 所有基础设施重置完成！"
                else
                    print_status "取消重置操作"
                fi
                ;;
            *)
                print_error "不支持的操作: $ACTION"
                show_usage
                exit 1
                ;;
        esac
        ;;
esac
