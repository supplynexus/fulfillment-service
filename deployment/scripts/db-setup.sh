#!/bin/bash

# SupplyNexus 数据库设置脚本
# 支持本地、测试、生产环境的数据库快速设置

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
    echo "SupplyNexus 数据库设置脚本"
    echo ""
    echo "用法: $0 <environment> [action]"
    echo ""
    echo "环境 (environment):"
    echo "  local     - 本地开发环境 (端口: 5433)"
    echo "  staging   - 测试环境 (端口: 5434)"
    echo "  prod      - 生产环境 (端口: 5435)"
    echo ""
    echo "操作 (action):"
    echo "  start     - 启动数据库 (默认)"
    echo "  stop      - 停止数据库"
    echo "  restart   - 重启数据库"
    echo "  status    - 查看状态"
    echo "  logs      - 查看日志"
    echo "  reset     - 重置数据库 (删除所有数据)"
    echo "  backup    - 备份数据库"
    echo "  restore   - 恢复数据库"
    echo ""
    echo "示例:"
    echo "  $0 local start      # 启动本地数据库"
    echo "  $0 staging status   # 查看测试环境状态"
    echo "  $0 prod stop        # 停止生产数据库"
    echo ""
    echo "首次使用:"
    echo "  1. 复制环境配置模板: cp deployment/environments/env.example deployment/environments/env.local"
    echo "  2. 编辑配置文件: vim deployment/environments/env.local"
    echo "  3. 启动数据库: $0 local start"
}

# 检查参数
if [ $# -eq 0 ]; then
    print_error "缺少环境参数"
    show_usage
    exit 1
fi

ENVIRONMENT=$1
ACTION=${2:-start}

# 验证环境参数
case $ENVIRONMENT in
    local|staging|prod)
        print_status "目标环境: $ENVIRONMENT"
        ;;
    *)
        print_error "不支持的环境: $ENVIRONMENT"
        show_usage
        exit 1
        ;;
esac

# 设置环境变量
case $ENVIRONMENT in
    local)
        DB_PORT=5433
        DB_NAME=supplynexus_local
        CONTAINER_NAME=supplynexus-postgres-local
        DATA_DIR=./deployment/docker/postgresql/data-local
        ;;
    staging)
        DB_PORT=5434
        DB_NAME=supplynexus_staging
        CONTAINER_NAME=supplynexus-postgres-staging
        DATA_DIR=./deployment/docker/postgresql/data-staging
        ;;
    prod)
        DB_PORT=5435
        DB_NAME=supplynexus_prod
        CONTAINER_NAME=supplynexus-postgres-prod
        DATA_DIR=./deployment/docker/postgresql/data-prod
        ;;
esac

# 检查环境配置文件
ENV_FILE="deployment/environments/env.$ENVIRONMENT"
if [ ! -f "$ENV_FILE" ]; then
    print_error "环境配置文件不存在: $ENV_FILE"
    echo ""
    print_status "请按以下步骤创建配置文件:"
    echo "  1. 复制模板文件: cp deployment/environments/env.example $ENV_FILE"
    echo "  2. 编辑配置文件: vim $ENV_FILE"
    echo "  3. 确保数据库配置正确:"
    echo "     DATABASE_URL=postgresql+asyncpg://supplynexus_admin:your_password@localhost:$DB_PORT/$DB_NAME"
    echo "     DATABASE_URL_SYNC=postgresql://supplynexus_admin:your_password@localhost:$DB_PORT/$DB_NAME"
    exit 1
fi

# 创建临时 docker-compose 文件
create_docker_compose() {
    cat > /tmp/supplynexus-postgres-$ENVIRONMENT.yml << EOF
version: '3.8'

services:
  postgresql:
    image: postgres:15-alpine
    container_name: $CONTAINER_NAME
    restart: unless-stopped
    ports:
      - "$DB_PORT:5432"
    environment:
      POSTGRES_DB: $DB_NAME
      POSTGRES_USER: supplynexus_admin
      POSTGRES_PASSWORD: \${POSTGRES_PASSWORD:-aabbccdd}
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - $DATA_DIR:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U supplynexus_admin -d $DB_NAME"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    networks:
      - postgres-network-$ENVIRONMENT

networks:
  postgres-network-$ENVIRONMENT:
    driver: bridge
EOF
}

# 确保数据目录存在
ensure_data_dir() {
    if [ ! -d "$DATA_DIR" ]; then
        print_status "创建数据目录: $DATA_DIR"
        mkdir -p "$DATA_DIR"
    fi
}

# 启动数据库
start_database() {
    print_status "启动 $ENVIRONMENT 环境数据库..."
    
    ensure_data_dir
    create_docker_compose
    
    # 停止现有容器（如果存在）
    docker-compose -f /tmp/supplynexus-postgres-$ENVIRONMENT.yml down 2>/dev/null || true
    
    # 启动服务
    docker-compose -f /tmp/supplynexus-postgres-$ENVIRONMENT.yml up -d
    
    # 等待服务启动
    print_status "等待数据库启动..."
    sleep 10
    
    # 检查服务状态
    if docker-compose -f /tmp/supplynexus-postgres-$ENVIRONMENT.yml ps | grep -q "Up"; then
        print_success "✅ 数据库启动成功！"
        echo ""
        print_status "连接信息:"
        echo "  容器名称: $CONTAINER_NAME"
        echo "  端口: $DB_PORT"
        echo "  数据库: $DB_NAME"
        echo "  用户: supplynexus_admin"
        echo "  密码: aabbccdd (默认，建议修改)"
        echo ""
        print_status "连接字符串:"
        echo "  DATABASE_URL=postgresql+asyncpg://supplynexus_admin:aabbccdd@localhost:$DB_PORT/$DB_NAME"
        echo "  DATABASE_URL_SYNC=postgresql://supplynexus_admin:aabbccdd@localhost:$DB_PORT/$DB_NAME"
    else
        print_error "❌ 数据库启动失败"
        docker-compose -f /tmp/supplynexus-postgres-$ENVIRONMENT.yml logs
        exit 1
    fi
}

# 停止数据库
stop_database() {
    print_status "停止 $ENVIRONMENT 环境数据库..."
    create_docker_compose
    docker-compose -f /tmp/supplynexus-postgres-$ENVIRONMENT.yml down
    print_success "数据库已停止"
}

# 重启数据库
restart_database() {
    print_status "重启 $ENVIRONMENT 环境数据库..."
    stop_database
    sleep 2
    start_database
}

# 查看状态
show_status() {
    print_status "$ENVIRONMENT 环境数据库状态:"
    create_docker_compose
    docker-compose -f /tmp/supplynexus-postgres-$ENVIRONMENT.yml ps
}

# 查看日志
show_logs() {
    print_status "$ENVIRONMENT 环境数据库日志:"
    create_docker_compose
    docker-compose -f /tmp/supplynexus-postgres-$ENVIRONMENT.yml logs -f
}

# 重置数据库
reset_database() {
    print_warning "⚠️  这将删除 $ENVIRONMENT 环境的所有数据！"
    echo "确认重置数据库？(y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        print_status "重置 $ENVIRONMENT 环境数据库..."
        stop_database
        print_status "删除数据目录: $DATA_DIR"
        rm -rf "$DATA_DIR"
        ensure_data_dir
        start_database
        print_success "数据库重置完成"
    else
        print_status "取消重置操作"
    fi
}

# 备份数据库
backup_database() {
    print_status "备份 $ENVIRONMENT 环境数据库..."
    BACKUP_FILE="backup_${ENVIRONMENT}_$(date +%Y%m%d_%H%M%S).sql"
    
    create_docker_compose
    docker-compose -f /tmp/supplynexus-postgres-$ENVIRONMENT.yml exec -T postgresql pg_dump -U supplynexus_admin -d $DB_NAME > "$BACKUP_FILE"
    
    if [ $? -eq 0 ]; then
        print_success "备份完成: $BACKUP_FILE"
    else
        print_error "备份失败"
        exit 1
    fi
}

# 恢复数据库
restore_database() {
    if [ -z "$3" ]; then
        print_error "请指定备份文件路径"
        echo "用法: $0 $ENVIRONMENT restore <backup_file>"
        exit 1
    fi
    
    BACKUP_FILE=$3
    if [ ! -f "$BACKUP_FILE" ]; then
        print_error "备份文件不存在: $BACKUP_FILE"
        exit 1
    fi
    
    print_warning "⚠️  这将覆盖 $ENVIRONMENT 环境的所有数据！"
    echo "确认恢复数据库？(y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        print_status "恢复 $ENVIRONMENT 环境数据库..."
        create_docker_compose
        
        # 确保数据库运行
        if ! docker-compose -f /tmp/supplynexus-postgres-$ENVIRONMENT.yml ps | grep -q "Up"; then
            start_database
        fi
        
        # 恢复数据
        docker-compose -f /tmp/supplynexus-postgres-$ENVIRONMENT.yml exec -T postgresql psql -U supplynexus_admin -d $DB_NAME < "$BACKUP_FILE"
        
        if [ $? -eq 0 ]; then
            print_success "数据库恢复完成"
        else
            print_error "数据库恢复失败"
            exit 1
        fi
    else
        print_status "取消恢复操作"
    fi
}

# 主逻辑
case $ACTION in
    start)
        start_database
        ;;
    stop)
        stop_database
        ;;
    restart)
        restart_database
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    reset)
        reset_database
        ;;
    backup)
        backup_database
        ;;
    restore)
        restore_database "$@"
        ;;
    *)
        print_error "不支持的操作: $ACTION"
        show_usage
        exit 1
        ;;
esac

# 清理临时文件
rm -f /tmp/supplynexus-postgres-$ENVIRONMENT.yml
