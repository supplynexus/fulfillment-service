#!/bin/bash

# 详细导入检查工具
# 用法: ./check_imports.sh [directory]

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

echo -e "${BLUE}🔍 详细导入检查工具${NC}"
echo "=========================="

# 设置检查目录
if [ $# -eq 1 ]; then
    CHECK_DIR="$1"
else
    CHECK_DIR="app"
fi

echo -e "${YELLOW}📋 检查目录: $CHECK_DIR${NC}"

# 激活虚拟环境
echo -e "${YELLOW}🔧 激活虚拟环境...${NC}"
cd "$PROJECT_ROOT"
source .venv/bin/activate

# 运行导入检查
echo -e "${YELLOW}🚀 开始导入检查...${NC}"
python scripts/check_imports.py "$CHECK_DIR"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 导入检查通过！${NC}"
else
    echo -e "${RED}❌ 导入检查发现问题！${NC}"
    exit 1
fi
