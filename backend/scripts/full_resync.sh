#!/bin/bash

# 完全重新同步脚本
# 用于手动触发Shopify订单和商品的完全重新同步

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}🚀 Shopify 完全重新同步工具${NC}"
echo "=================================="

# 检查参数
SYNC_ORDERS=true
SYNC_PRODUCTS=true
MAX_ORDERS=""
MAX_PRODUCTS=""
TENANT_ID=""

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --orders-only)
            SYNC_ORDERS=true
            SYNC_PRODUCTS=false
            shift
            ;;
        --products-only)
            SYNC_ORDERS=false
            SYNC_PRODUCTS=true
            shift
            ;;
        --max-orders)
            MAX_ORDERS="$2"
            shift 2
            ;;
        --max-products)
            MAX_PRODUCTS="$2"
            shift 2
            ;;
        --tenant-id)
            TENANT_ID="$2"
            shift 2
            ;;
        --help|-h)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --orders-only      只同步订单"
            echo "  --products-only    只同步商品"
            echo "  --max-orders N     限制最大订单数量"
            echo "  --max-products N   限制最大商品数量"
            echo "  --tenant-id ID     指定租户ID"
            echo "  --help, -h         显示此帮助信息"
            echo ""
            echo "示例:"
            echo "  $0                                    # 同步所有订单和商品"
            echo "  $0 --orders-only                      # 只同步订单"
            echo "  $0 --max-orders 1000                  # 限制订单数量"
            echo "  $0 --tenant-id 1 --max-products 500   # 指定租户和商品数量"
            exit 0
            ;;
        *)
            echo -e "${RED}错误: 未知参数 $1${NC}"
            echo "使用 --help 查看帮助信息"
            exit 1
            ;;
    esac
done

# 显示同步配置
echo -e "${YELLOW}📋 同步配置:${NC}"
echo "  同步订单: $SYNC_ORDERS"
echo "  同步商品: $SYNC_PRODUCTS"
if [[ -n "$MAX_ORDERS" ]]; then
    echo "  最大订单数: $MAX_ORDERS"
fi
if [[ -n "$MAX_PRODUCTS" ]]; then
    echo "  最大商品数: $MAX_PRODUCTS"
fi
if [[ -n "$TENANT_ID" ]]; then
    echo "  指定租户: $TENANT_ID"
fi
echo ""

# 确认执行
echo -e "${YELLOW}⚠️  警告: 这将执行完全重新同步，可能会花费较长时间${NC}"
read -p "是否继续? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}已取消${NC}"
    exit 0
fi

# 切换到后端目录
cd "$BACKEND_DIR"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到 python3${NC}"
    exit 1
fi

# 构建Python脚本参数
PYTHON_ARGS=""
if [[ "$SYNC_ORDERS" == "true" ]]; then
    PYTHON_ARGS="$PYTHON_ARGS --orders"
fi
if [[ "$SYNC_PRODUCTS" == "true" ]]; then
    PYTHON_ARGS="$PYTHON_ARGS --products"
fi
if [[ -n "$MAX_ORDERS" ]]; then
    PYTHON_ARGS="$PYTHON_ARGS --max-orders $MAX_ORDERS"
fi
if [[ -n "$MAX_PRODUCTS" ]]; then
    PYTHON_ARGS="$PYTHON_ARGS --max-products $MAX_PRODUCTS"
fi
if [[ -n "$TENANT_ID" ]]; then
    PYTHON_ARGS="$PYTHON_ARGS --tenant-id $TENANT_ID"
fi

# 执行Python脚本
echo -e "${GREEN}🔄 开始执行完全重新同步...${NC}"
echo ""

python3 scripts/full_resync.py $PYTHON_ARGS

# 检查执行结果
if [[ $? -eq 0 ]]; then
    echo ""
    echo -e "${GREEN}✅ 完全重新同步完成${NC}"
else
    echo ""
    echo -e "${RED}❌ 完全重新同步失败${NC}"
    exit 1
fi
