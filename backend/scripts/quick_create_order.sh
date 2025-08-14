#!/bin/bash

# Shopify 快速创建订单脚本

echo "🚀 Shopify 快速创建订单工具"
echo "================================"

# 检查是否在正确的目录
if [ ! -f "app/main.py" ]; then
    echo "❌ 请在 backend 目录下运行此脚本"
    exit 1
fi

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行: python -m venv .venv && source .venv/bin/activate"
    exit 1
fi

# 激活虚拟环境
source .venv/bin/activate

# 显示选项
echo ""
echo "请选择要创建的订单类型："
echo "1) 基础测试订单 (basic)"
echo "2) 多商品测试订单 (multi_items)"
echo "3) 已支付测试订单 (paid)"
echo "4) 列出现有订单"
echo "5) 退出"
echo ""

read -p "请输入选项 (1-5): " choice

case $choice in
    1)
        echo "📦 创建基础测试订单..."
        PYTHONPATH=. python scripts/shopify_order_manager.py --action create --template basic
        ;;
    2)
        echo "📦 创建多商品测试订单..."
        PYTHONPATH=. python scripts/shopify_order_manager.py --action create --template multi_items
        ;;
    3)
        echo "📦 创建已支付测试订单..."
        PYTHONPATH=. python scripts/shopify_order_manager.py --action create --template paid
        ;;
    4)
        echo "📋 列出现有订单..."
        PYTHONPATH=. python scripts/shopify_order_manager.py --action list --limit 10
        ;;
    5)
        echo "👋 再见！"
        exit 0
        ;;
    *)
        echo "❌ 无效选项，请重新运行脚本"
        exit 1
        ;;
esac

echo ""
echo "✅ 操作完成！"
