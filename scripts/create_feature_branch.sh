#!/bin/bash

# SupplyNexus OMS Feature Branch Creator
# Usage: ./scripts/create_feature_branch.sh <phase> <feature-name>
# Example: ./scripts/create_feature_branch.sh 1 jwt-auth-system

set -e

# Check if we're in the right directory
if [ ! -f "backend/app/main.py" ]; then
    echo "Error: Please run this script from the project root directory"
    exit 1
fi

# Check arguments
if [ $# -ne 2 ]; then
    echo "Usage: $0 <phase> <feature-name>"
    echo "Example: $0 1 jwt-auth-system"
    exit 1
fi

PHASE=$1
FEATURE_NAME=$2
BRANCH_NAME="feature/phase-${PHASE}-${FEATURE_NAME}"

# Check if we're on develop branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "develop" ]; then
    echo "Warning: You're not on the develop branch. Current branch: $CURRENT_BRANCH"
    read -p "Do you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

# Pull latest changes from develop
echo "Pulling latest changes from develop..."
git pull origin develop

# Create and checkout new branch
echo "Creating feature branch: $BRANCH_NAME"
git checkout -b "$BRANCH_NAME"

echo "✅ Successfully created and switched to branch: $BRANCH_NAME"
echo ""
echo "📋 Next steps:"
echo "1. Start working on your feature"
echo "2. Commit your changes with descriptive messages"
echo "3. Push the branch: git push -u origin $BRANCH_NAME"
echo "4. Create a Pull Request when ready"
echo ""
echo "🔗 Available tasks for Phase $PHASE:"
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
        echo "  - Unknown phase. Check docs/DEVELOPMENT_TASKS.md for available tasks"
        ;;
esac
