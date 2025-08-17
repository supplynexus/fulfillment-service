#!/bin/bash

# SupplyNexus 总体部署脚本
# 用于管理整个 docker-compose.yml 系统的部署

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印函数
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

# 显示使用说明
show_usage() {
    echo "SupplyNexus 总体部署脚本"
    echo ""
    echo "用法: $0 <environment> <action>"
    echo ""
    echo "环境参数:"
    echo "  local    - 本地环境"
    echo "  dev      - 开发环境"
    echo "  stg      - 测试环境"
    echo "  prod     - 生产环境"
    echo ""
    echo "操作参数:"
    echo "  up       - 启动所有服务"
    echo "  down     - 停止所有服务"
    echo "  restart  - 重启所有服务"
    echo "  build    - 重新构建并启动所有服务"
    echo "  logs     - 查看所有服务日志"
    echo "  status   - 查看所有服务状态"
    echo "  clean    - 清理所有容器和网络（保留数据卷）"
    echo "  reset    - 完全重置（清理容器、网络和数据卷）"
    echo ""
    echo "示例:"
    echo "  $0 dev up        # 启动开发环境"
    echo "  $0 dev down      # 停止开发环境"
    echo "  $0 dev restart   # 重启开发环境"
    echo "  $0 dev build     # 重新构建开发环境"
    echo "  $0 dev clean     # 清理开发环境"
    echo "  $0 dev reset     # 完全重置开发环境"
}

# 检查参数
if [ $# -eq 0 ]; then
    print_error "缺少参数"
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
    up|down|restart|build|logs|status|clean|reset)
        print_status "操作: $ACTION"
        ;;
    *)
        print_error "不支持的操作: $ACTION"
        show_usage
        exit 1
        ;;
esac

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

print_status "项目根目录: $PROJECT_ROOT"

# 检查环境文件
ENV_FILE="../environments/backend/.env.$ENVIRONMENT"
if [ ! -f "$ENV_FILE" ]; then
    print_warning "环境文件不存在: $ENV_FILE"
    print_status "从示例文件创建环境文件..."
    EXAMPLE_FILE="../environments/backend/env.example"
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

print_status "环境文件: $ENV_FILE"

# 显示环境文件信息
print_status "环境文件信息:"
echo "  文件: $(basename "$ENV_FILE")"
echo "  大小: $(ls -lh "$ENV_FILE" | awk '{print $5}')"
echo "  修改时间: $(ls -lh "$ENV_FILE" | awk '{print $6, $7, $8}')"

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    print_error "Docker 未运行，请先启动 Docker"
    exit 1
fi

# 设置环境变量
export ENV_FILE="env.$ENVIRONMENT"

print_status "开始操作 SupplyNexus 总体部署 ($ENVIRONMENT 环境, $ACTION 操作)"

# 执行操作
case $ACTION in
    "up")
        print_status "启动所有服务..."
        
        # 检查是否有现有服务在运行
        if [ "$(docker-compose ps -q)" ]; then
            print_warning "检测到现有服务正在运行"
            read -p "是否要停止现有服务并重新启动？(y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                print_status "停止现有服务..."
                docker-compose down
            else
                print_status "跳过启动操作"
                exit 0
            fi
        fi
        
        # 启动所有服务
        docker-compose up -d
        
        # 等待服务启动
        print_status "等待服务启动..."
        sleep 10
        
        # 检查服务状态
        print_status "检查服务状态..."
        docker-compose ps
        
        print_success "✅ 所有服务启动成功！"
        ;;
        
    "down")
        print_status "停止所有服务..."
        docker-compose down
        print_success "✅ 所有服务已停止"
        ;;
        
    "restart")
        print_status "重启所有服务..."
        docker-compose restart
        print_success "✅ 所有服务已重启"
        ;;
        
    "build")
        print_status "重新构建并启动所有服务..."
        docker-compose down
        docker-compose up --build -d
        
        # 等待服务启动
        print_status "等待服务启动..."
        sleep 15
        
        # 检查服务状态
        print_status "检查服务状态..."
        docker-compose ps
        
        print_success "✅ 所有服务重新构建并启动成功！"
        ;;
        
    "logs")
        print_status "查看所有服务日志..."
        docker-compose logs -f
        ;;
        
    "status")
        print_status "所有服务状态:"
        docker-compose ps
        echo ""
        print_status "服务健康检查:"
        
        # 检查 PostgreSQL
        if docker-compose ps postgres | grep -q "Up"; then
            print_success "PostgreSQL: 运行中"
        else
            print_error "PostgreSQL: 未运行"
        fi
        
        # 检查 Redis
        if docker-compose ps redis | grep -q "Up"; then
            print_success "Redis: 运行中"
        else
            print_error "Redis: 未运行"
        fi
        
        # 检查 Backend
        if docker-compose ps backend | grep -q "Up"; then
            print_success "Backend: 运行中"
        else
            print_error "Backend: 未运行"
        fi
        
        # 检查 Celery Worker
        if docker-compose ps celery_worker | grep -q "Up"; then
            print_success "Celery Worker: 运行中"
        else
            print_error "Celery Worker: 未运行"
        fi
        
        # 检查 Celery Beat
        if docker-compose ps celery_beat | grep -q "Up"; then
            print_success "Celery Beat: 运行中"
        else
            print_error "Celery Beat: 未运行"
        fi
        
        # 检查 Flower
        if docker-compose ps flower | grep -q "Up"; then
            print_success "Flower: 运行中"
        else
            print_error "Flower: 未运行"
        fi
        
        # 检查 Frontend
        if docker-compose ps frontend | grep -q "Up"; then
            print_success "Frontend: 运行中"
        else
            print_error "Frontend: 未运行"
        fi
        ;;
        
    "clean")
        print_warning "⚠️  即将清理所有容器和网络（保留数据卷）"
        read -p "确认继续？(y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_status "停止所有服务..."
            docker-compose down
            
            print_status "清理未使用的容器..."
            docker container prune -f
            
            print_status "清理未使用的网络..."
            docker network prune -f
            
            print_success "✅ 清理完成（数据卷已保留）"
        else
            print_status "取消清理操作"
        fi
        ;;
        
    "reset")
        print_warning "⚠️  ⚠️  ⚠️  即将完全重置所有内容（包括数据卷）"
        print_warning "这将删除所有数据，包括数据库和缓存！"
        read -p "确认继续？(输入 'YES' 确认): " -r
        if [[ $REPLY == "YES" ]]; then
            print_status "停止所有服务..."
            docker-compose down
            
            print_status "删除所有相关容器..."
            docker-compose down -v
            
            print_status "清理未使用的容器..."
            docker container prune -f
            
            print_status "清理未使用的网络..."
            docker network prune -f
            
            print_status "清理未使用的数据卷..."
            docker volume prune -f
            
            print_success "✅ 完全重置完成"
            print_warning "所有数据已被删除，需要重新初始化数据库"
        else
            print_status "取消重置操作"
        fi
        ;;
esac

print_status "🎉 操作完成！"

# 显示访问信息
if [ "$ACTION" = "up" ] || [ "$ACTION" = "build" ]; then
    echo ""
    print_status "🌐 服务访问地址:"
    print_success "Frontend: http://localhost:${FRONTEND_PORT:-3000}"
    print_success "Backend API: http://localhost:${BACKEND_PORT:-8000}"
    print_success "Flower (Celery): http://localhost:${FLOWER_PORT:-5555}"
    print_success "PostgreSQL: localhost:${POSTGRES_PORT:-5432}"
    print_success "Redis: localhost:${REDIS_PORT:-6379}"
    echo ""
    print_status "📊 健康检查:"
    print_success "Frontend Health: http://localhost:${FRONTEND_PORT:-3000}/api/health"
    print_success "Backend Health: http://localhost:${BACKEND_PORT:-8000}/health"
fi
