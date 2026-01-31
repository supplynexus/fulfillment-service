#!/bin/bash

# SupplyNexus OMS Task Status Viewer
# Usage: ./scripts/show_tasks.sh [phase]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_phase() {
    local phase=$1
    local title=$2
    local status=$3
    
    case $status in
        "completed")
            echo -e "${GREEN}✓${NC} Phase $phase: $title"
            ;;
        "in-progress")
            echo -e "${YELLOW}⟳${NC} Phase $phase: $title"
            ;;
        "pending")
            echo -e "${BLUE}○${NC} Phase $phase: $title"
            ;;
        *)
            echo -e "${RED}?${NC} Phase $phase: $title"
            ;;
    esac
}

# Function to show current branch info
show_current_branch() {
    local current_branch=$(git branch --show-current)
    echo -e "\n${BLUE}📍 Current Branch:${NC} $current_branch"
    
    if [[ $current_branch == feature/* ]]; then
        echo -e "${YELLOW}📋 Working on feature branch${NC}"
    elif [[ $current_branch == develop ]]; then
        echo -e "${GREEN}📋 On develop branch${NC}"
    elif [[ $current_branch == main ]]; then
        echo -e "${RED}⚠️  On main branch${NC}"
    fi
}

# Function to show available branches
show_available_branches() {
    echo -e "\n${BLUE}🌿 Available Feature Branches:${NC}"
    git branch -r | grep "feature/phase-" | sort | while read branch; do
        echo "  $branch"
    done
}

# Main task overview
echo -e "${BLUE}🎯 SupplyNexus OMS Development Tasks${NC}"
echo "=================================================="

# Show phases
print_phase "1" "认证和安全基础" "in-progress"
print_phase "2" "数据获取和同步" "pending"
print_phase "3" "核心业务功能" "pending"
print_phase "4" "用户界面" "pending"
print_phase "5" "多租户完善" "pending"

# Show current branch info
show_current_branch

# Show available branches
show_available_branches

# Show next steps
echo -e "\n${BLUE}📋 Next Steps:${NC}"
echo "1. Complete current feature branch"
echo "2. Create Pull Request"
echo "3. Merge to develop after review"
echo "4. Move to next phase"

# Show quick commands
echo -e "\n${BLUE}⚡ Quick Commands:${NC}"
echo "  Create new feature: ./scripts/create_feature_branch.sh <phase> <feature>"
echo "  View tasks: ./scripts/show_tasks.sh"
echo "  Switch to develop: git checkout develop"
echo "  View task details: cat docs/DEVELOPMENT_TASKS.md"

# If specific phase requested
if [ $# -eq 1 ]; then
    PHASE=$1
    echo -e "\n${BLUE}📋 Phase $PHASE Details:${NC}"
    case $PHASE in
        1)
            echo "  - JWT认证系统完善 (jwt-auth-system)"
            echo "  - API Key管理系统 (api-key-management)"
            ;;
        2)
            echo "  - Shopify API集成 (shopify-api-integration)"
            echo "  - 批量数据同步 (batch-sync)"
            ;;
        3)
            echo "  - 订单管理API (order-management-api)"
            echo "  - 前端订单界面 (order-ui)"
            echo "  - 自动发货配置 (auto-fulfillment)"
            ;;
        4)
            echo "  - 仪表板界面 (dashboard-ui)"
            echo "  - 订单管理界面 (order-management-ui)"
            echo "  - 商品管理界面 (product-management-ui)"
            echo "  - 发货操作界面 (fulfillment-ui)"
            echo "  - 库存管理界面 (inventory-ui)"
            ;;
        5)
            echo "  - 租户隔离机制 (tenant-isolation)"
            echo "  - 租户配置管理 (tenant-config)"
            echo "  - 租户权限管理 (tenant-permissions)"
            ;;
        *)
            echo "  - Unknown phase. Check docs/DEVELOPMENT_TASKS.md"
            ;;
    esac
fi
