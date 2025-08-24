#!/bin/bash

# 租户公钥更新工具
# 用法: ./update_tenant_public_key.sh <tenant_name> <private_key_file>

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}🔧 租户公钥更新工具${NC}"
echo "=================================="

# 检查参数
if [ $# -ne 2 ]; then
    echo -e "${RED}❌ 参数错误${NC}"
    echo "用法: $0 <tenant_name> <private_key_file>"
    echo "示例: $0 impeach ../frontend/keys/impeach_private_key.pem"
    exit 1
fi

TENANT_NAME="$1"
PRIVATE_KEY_FILE="$2"

# 检查私钥文件是否存在
if [ ! -f "$PRIVATE_KEY_FILE" ]; then
    echo -e "${RED}❌ 私钥文件不存在: $PRIVATE_KEY_FILE${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 参数信息:${NC}"
echo "  租户名称: $TENANT_NAME"
echo "  私钥文件: $PRIVATE_KEY_FILE"
echo ""

# 激活虚拟环境
echo -e "${YELLOW}🔧 激活虚拟环境...${NC}"
cd "$PROJECT_ROOT"
source .venv/bin/activate

# 运行 Python 脚本
echo -e "${YELLOW}🚀 开始更新公钥...${NC}"
python scripts/update_tenant_public_key.py "$TENANT_NAME" "$PRIVATE_KEY_FILE"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 公钥更新成功！${NC}"
else
    echo -e "${RED}❌ 公钥更新失败！${NC}"
    exit 1
fi
