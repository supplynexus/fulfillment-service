#!/bin/bash
# 生产环境 UFW 防火墙配置脚本
# 用于限制数据库和 Redis 端口外网访问

set -e

echo "🔒 配置生产环境 UFW 防火墙..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 检查是否以 root 或 sudo 运行
if [ "$EUID" -ne 0 ]; then 
    print_error "请使用 sudo 运行此脚本"
    exit 1
fi

# 检查 UFW 是否已安装
if ! command -v ufw &> /dev/null; then
    print_status "安装 UFW..."
    apt-get update
    apt-get install -y ufw
fi

# 启用 UFW（如果未启用）
if ! ufw status | grep -q "Status: active"; then
    print_status "启用 UFW..."
    ufw --force enable
fi

# 允许 SSH（重要！避免锁定自己）
print_status "允许 SSH (端口 22)..."
ufw allow 22/tcp comment 'SSH'

# 允许 HTTP 和 HTTPS
print_status "允许 HTTP (端口 80) 和 HTTPS (端口 443)..."
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'

# 拒绝数据库和 Redis 端口外网访问
print_status "拒绝 PostgreSQL (端口 5432) 外网访问..."
ufw deny 5432/tcp comment 'PostgreSQL - Internal only'

print_status "拒绝 Redis (端口 6379) 外网访问..."
ufw deny 6379/tcp comment 'Redis - Internal only'

# 允许本地访问数据库和 Redis（如果需要）
print_status "允许本地访问 PostgreSQL 和 Redis..."
ufw allow from 127.0.0.1 to any port 5432 comment 'PostgreSQL - Local only'
ufw allow from 127.0.0.1 to any port 6379 comment 'Redis - Local only'

# 如果需要临时开放端口给特定 IP（例如你的本地 IP），可以取消注释并修改
# print_status "允许特定 IP 访问数据库..."
# ufw allow from YOUR_IP_ADDRESS to any port 5432 comment 'PostgreSQL - Temporary access'
# ufw allow from YOUR_IP_ADDRESS to any port 6379 comment 'Redis - Temporary access'

# 显示防火墙状态
print_success "UFW 配置完成！"
echo ""
print_status "当前防火墙规则："
ufw status numbered

echo ""
print_warning "注意："
echo "  - 数据库和 Redis 端口已限制为仅本地访问"
echo "  - 如需临时开放端口，使用: sudo ufw allow from YOUR_IP to any port 5432"
echo "  - 临时开放后记得关闭: sudo ufw delete allow from YOUR_IP to any port 5432"
