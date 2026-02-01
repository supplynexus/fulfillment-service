#!/bin/bash
# SupplyNexus 基础设施快速设置脚本
# 用于在新服务器上快速建立 Redis 和 PostgreSQL

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 函数定义
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    
    print_status "Docker 和 Docker Compose 已安装"
}

# 创建目录结构
create_directories() {
    print_header "创建目录结构"
    
    BASE_DIR="${1:-$HOME/supplynexus/infrastructure}"
    print_status "基础目录: $BASE_DIR"
    
    mkdir -p "$BASE_DIR/postgresql"
    mkdir -p "$BASE_DIR/redis"
    
    print_status "✅ 目录结构创建完成"
}

# 检查配置文件是否存在
check_config_files() {
    local service=$1
    local config_file=$2
    
    if [ ! -f "$config_file" ]; then
        print_error "$service 配置文件不存在: $config_file"
        print_warning "请确保您已从项目复制了以下文件："
        print_warning "  - docker-compose.yml"
        print_warning "  - deploy.sh"
        print_warning "  - environment.example"
        return 1
    fi
    return 0
}

# 设置 PostgreSQL
setup_postgresql() {
    print_header "设置 PostgreSQL"
    
    BASE_DIR="${1:-$HOME/supplynexus/infrastructure}"
    PG_DIR="$BASE_DIR/postgresql"
    
    cd "$PG_DIR" || exit 1
    
    # 检查配置文件
    if ! check_config_files "PostgreSQL" "docker-compose.yml"; then
        return 1
    fi
    
    # 检查环境文件
    if [ ! -f ".env" ]; then
        if [ -f "environment.example" ]; then
            print_status "从示例文件创建 .env"
            cp environment.example .env
            print_warning "⚠️  请编辑 .env 文件并修改密码！"
            print_warning "   文件位置: $PG_DIR/.env"
            print_warning "   必须修改: POSTGRES_PASSWORD"
        else
            print_error "environment.example 文件不存在"
            return 1
        fi
    else
        print_status ".env 文件已存在"
    fi
    
    # 设置脚本权限
    if [ -f "deploy.sh" ]; then
        chmod +x deploy.sh
        print_status "✅ deploy.sh 权限已设置"
    fi
    
    # 创建数据目录
    DATA_DIR=$(grep DATA_DIR .env 2>/dev/null | cut -d'=' -f2 || echo "./data-prod")
    if [ -n "$DATA_DIR" ] && [ ! -d "$DATA_DIR" ]; then
        mkdir -p "$DATA_DIR"
        print_status "✅ 数据目录已创建: $DATA_DIR"
    fi
    
    print_status "✅ PostgreSQL 设置完成"
}

# 设置 Redis
setup_redis() {
    print_header "设置 Redis"
    
    BASE_DIR="${1:-$HOME/supplynexus/infrastructure}"
    REDIS_DIR="$BASE_DIR/redis"
    
    cd "$REDIS_DIR" || exit 1
    
    # 检查配置文件
    if ! check_config_files "Redis" "docker-compose.yml"; then
        return 1
    fi
    
    # 检查环境文件
    if [ ! -f ".env" ]; then
        if [ -f "environment.example" ]; then
            print_status "从示例文件创建 .env"
            cp environment.example .env
            print_warning "⚠️  请编辑 .env 文件并修改密码！"
            print_warning "   文件位置: $REDIS_DIR/.env"
            print_warning "   必须修改: REDIS_PASSWORD"
        else
            print_error "environment.example 文件不存在"
            return 1
        fi
    else
        print_status ".env 文件已存在"
    fi
    
    # 设置脚本权限
    if [ -f "deploy.sh" ]; then
        chmod +x deploy.sh
        print_status "✅ deploy.sh 权限已设置"
    fi
    
    # 创建数据目录
    DATA_DIR=$(grep DATA_DIR .env 2>/dev/null | cut -d'=' -f2 || echo "./data-prod")
    if [ -n "$DATA_DIR" ] && [ ! -d "$DATA_DIR" ]; then
        mkdir -p "$DATA_DIR"
        print_status "✅ 数据目录已创建: $DATA_DIR"
    fi
    
    print_status "✅ Redis 设置完成"
}

# 显示使用说明
show_usage() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -d, --dir DIR     指定基础目录 (默认: ~/supplynexus/infrastructure)"
    echo "  -h, --help        显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                使用默认目录设置"
    echo "  $0 -d /opt/supplynexus  使用指定目录设置"
}

# 主函数
main() {
    BASE_DIR="$HOME/supplynexus/infrastructure"
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--dir)
                BASE_DIR="$2"
                shift 2
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                print_error "未知参数: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    print_header "SupplyNexus 基础设施快速设置"
    echo ""
    print_status "基础目录: $BASE_DIR"
    echo ""
    
    # 检查 Docker
    check_docker
    echo ""
    
    # 创建目录
    create_directories "$BASE_DIR"
    echo ""
    
    # 设置 PostgreSQL
    if ! setup_postgresql "$BASE_DIR"; then
        print_error "PostgreSQL 设置失败"
        exit 1
    fi
    echo ""
    
    # 设置 Redis
    if ! setup_redis "$BASE_DIR"; then
        print_error "Redis 设置失败"
        exit 1
    fi
    echo ""
    
    print_header "设置完成"
    print_status "✅ 所有基础设施组件已设置完成"
    echo ""
    print_warning "⚠️  重要提示："
    echo "   1. 请编辑以下文件并修改密码："
    echo "      - $BASE_DIR/postgresql/.env (修改 POSTGRES_PASSWORD)"
    echo "      - $BASE_DIR/redis/.env (修改 REDIS_PASSWORD)"
    echo ""
    echo "   2. 启动服务："
    echo "      cd $BASE_DIR/postgresql && ./deploy.sh prod up"
    echo "      cd $BASE_DIR/redis && ./deploy.sh prod up"
    echo ""
    echo "   3. 验证服务："
    echo "      docker ps | grep -E 'postgres|redis'"
    echo ""
}

# 运行主函数
main "$@"
