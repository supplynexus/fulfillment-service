#!/bin/bash

# 快速代码检查工具
# 用法: ./quick_check.sh

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

echo -e "${BLUE}🔍 快速代码检查工具${NC}"
echo "=========================="

# 激活虚拟环境
echo -e "${YELLOW}🔧 激活虚拟环境...${NC}"
cd "$PROJECT_ROOT"
source .venv/bin/activate

# 运行快速检查
echo -e "${YELLOW}🚀 开始快速检查...${NC}"
python scripts/quick_check.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 快速检查通过！${NC}"
else
    echo -e "${RED}❌ 快速检查失败！${NC}"
    exit 1
fi
