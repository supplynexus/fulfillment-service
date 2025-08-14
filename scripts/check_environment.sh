#!/bin/bash

# SupplyNexus 环境配置检查脚本
# Usage: ./scripts/check_environment.sh [environment]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Function to show usage
show_usage() {
    echo "SupplyNexus 环境配置检查脚本"
    echo "Usage: ./scripts/check_environment.sh [environment]"
    echo ""
    echo "Environments:"
    echo "  local        - Local development environment"
    echo "  dev          - Development environment"
    echo "  stg          - Staging environment"
    echo "  prod         - Production environment"
    echo ""
    echo "Examples:"
    echo "  ./scripts/check_environment.sh"
    echo "  ./scripts/check_environment.sh dev"
    echo "  ./scripts/check_environment.sh prod"
}

# Parse arguments
ENVIRONMENT=${1:-"local"}

# Validate environment
case "$ENVIRONMENT" in
    local|dev|stg|prod)
        ;;
    *)
        print_error "Invalid environment: $ENVIRONMENT"
        echo "Valid environments: local, dev, stg, prod"
        exit 1
        ;;
esac

print_status "检查环境配置: $ENVIRONMENT"

# Get the project root directory
PROJECT_ROOT="$(dirname "$0")/.."
ENV_FILE_PATH="$PROJECT_ROOT/deployment/environments/env.$ENVIRONMENT"

# Check if environment file exists
if [ ! -f "$ENV_FILE_PATH" ]; then
    print_error "环境配置文件不存在: $ENV_FILE_PATH"
    echo "请创建环境配置文件:"
    echo "  cp $PROJECT_ROOT/deployment/environments/env.example $ENV_FILE_PATH"
    exit 1
fi

print_success "环境配置文件存在: $ENV_FILE_PATH"

# Check required environment variables
print_status "检查必需的环境变量..."

# Source the environment file
set -a
source "$ENV_FILE_PATH"
set +a

# Required variables
REQUIRED_VARS=(
    "DATABASE_URL"
    "DATABASE_URL_SYNC"
    "REDIS_URL"
    "CELERY_BROKER_URL"
    "CELERY_RESULT_BACKEND"
    "SECRET_KEY"
    "HEALTH_CHECK_API_KEY"
)

# Optional variables
OPTIONAL_VARS=(
    "SHOPIFY_API_KEY"
    "SHOPIFY_API_SECRET"
    "SHOPIFY_ACCESS_TOKEN"
    "PRINTIFY_API_TOKEN"
    "SENTRY_DSN"
)

# Check required variables
MISSING_REQUIRED=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_REQUIRED+=("$var")
    else
        print_success "✓ $var"
    fi
done

# Check optional variables
MISSING_OPTIONAL=()
for var in "${OPTIONAL_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_OPTIONAL+=("$var")
    else
        print_success "✓ $var"
    fi
done

# Report results
if [ ${#MISSING_REQUIRED[@]} -gt 0 ]; then
    print_error "缺少必需的环境变量:"
    for var in "${MISSING_REQUIRED[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "请在 $ENV_FILE_PATH 中设置这些变量"
    exit 1
fi

if [ ${#MISSING_OPTIONAL[@]} -gt 0 ]; then
    print_warning "缺少可选的环境变量:"
    for var in "${MISSING_OPTIONAL[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "这些变量不是必需的，但建议设置"
fi

# Check database connection
print_status "检查数据库连接..."
if command -v psql &> /dev/null; then
    # Extract database connection info
    DB_URL="${DATABASE_URL_SYNC}"
    if [[ $DB_URL =~ postgresql://([^:]+):([^@]+)@([^:]+):([^/]+)/(.+) ]]; then
        DB_USER="${BASH_REMATCH[1]}"
        DB_PASS="${BASH_REMATCH[2]}"
        DB_HOST="${BASH_REMATCH[3]}"
        DB_PORT="${BASH_REMATCH[4]}"
        DB_NAME="${BASH_REMATCH[5]}"
        
        # Test connection
        if PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" &> /dev/null; then
            print_success "数据库连接正常"
        else
            print_error "数据库连接失败"
            echo "请检查数据库配置和连接"
        fi
    else
        print_warning "无法解析数据库URL格式"
    fi
else
    print_warning "psql 命令不可用，跳过数据库连接测试"
fi

# Check Redis connection
print_status "检查Redis连接..."
if command -v redis-cli &> /dev/null; then
    # Extract Redis connection info
    REDIS_URL_CLEAN="${REDIS_URL}"
    if [[ $REDIS_URL_CLEAN =~ redis://([^:]*):([^@]+)@([^:]+):([^/]+)/(.+) ]]; then
        REDIS_PASS="${BASH_REMATCH[2]}"
        REDIS_HOST="${BASH_REMATCH[3]}"
        REDIS_PORT="${BASH_REMATCH[4]}"
        REDIS_DB="${BASH_REMATCH[5]}"
        
        # Test connection
        if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASS" ping &> /dev/null; then
            print_success "Redis连接正常"
        else
            print_error "Redis连接失败"
            echo "请检查Redis配置和连接"
        fi
    elif [[ $REDIS_URL_CLEAN =~ redis://([^:]+):([^/]+)/(.+) ]]; then
        REDIS_HOST="${BASH_REMATCH[1]}"
        REDIS_PORT="${BASH_REMATCH[2]}"
        REDIS_DB="${BASH_REMATCH[3]}"
        
        # Test connection
        if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping &> /dev/null; then
            print_success "Redis连接正常"
        else
            print_error "Redis连接失败"
            echo "请检查Redis配置和连接"
        fi
    else
        print_warning "无法解析Redis URL格式"
    fi
else
    print_warning "redis-cli 命令不可用，跳过Redis连接测试"
fi

# Check environment-specific configurations
print_status "检查环境特定配置..."

case "$ENVIRONMENT" in
    local)
        if [ "$ENVIRONMENT" != "local" ]; then
            print_warning "ENVIRONMENT 变量设置为 $ENVIRONMENT，但检查的是 local 环境"
        fi
        ;;
    dev)
        if [ "$ENVIRONMENT" != "dev" ]; then
            print_warning "ENVIRONMENT 变量设置为 $ENVIRONMENT，但检查的是 dev 环境"
        fi
        ;;
    stg)
        if [ "$ENVIRONMENT" != "stg" ]; then
            print_warning "ENVIRONMENT 变量设置为 $ENVIRONMENT，但检查的是 stg 环境"
        fi
        ;;
    prod)
        if [ "$ENVIRONMENT" != "prod" ]; then
            print_warning "ENVIRONMENT 变量设置为 $ENVIRONMENT，但检查的是 prod 环境"
        fi
        
        # Production-specific checks
        if [ "$SECRET_KEY" = "your-secret-key-change-in-prod" ]; then
            print_error "生产环境使用了默认的 SECRET_KEY"
        fi
        
        if [ "$HEALTH_CHECK_API_KEY" = "your-health-check-api-key" ]; then
            print_error "生产环境使用了默认的 HEALTH_CHECK_API_KEY"
        fi
        ;;
esac

# Check file permissions
print_status "检查文件权限..."
if [ -r "$ENV_FILE_PATH" ]; then
    print_success "环境配置文件可读"
else
    print_error "环境配置文件不可读"
fi

# Summary
echo ""
print_success "环境配置检查完成: $ENVIRONMENT"

if [ ${#MISSING_OPTIONAL[@]} -gt 0 ]; then
    print_warning "有 ${#MISSING_OPTIONAL[@]} 个可选变量未设置"
else
    print_success "所有环境变量都已配置"
fi

echo ""
print_status "下一步:"
echo "  1. 启动服务: ./scripts/dev/start.sh"
echo "  2. 运行数据库迁移: ./scripts/db/alembic.sh $ENVIRONMENT upgrade"
echo "  3. 启动Celery: export ENV_FILE=$ENV_FILE_PATH && ./backend/scripts/start_celery.sh"
