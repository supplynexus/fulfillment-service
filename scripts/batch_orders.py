#!/usr/bin/env python3
"""
批量订单处理命令行工具
用于直接运行批量获取和处理订单
"""
import asyncio
import argparse
import sys
import os
from datetime import datetime, timedelta
from typing import Optional

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.services.shopify.client import create_shopify_client
from app.core.config import settings


async def fetch_orders_direct(
    shop_name: str,
    access_token: str,
    query_filter: Optional[str] = None,
    max_orders: Optional[int] = None,
    output_file: Optional[str] = None
):
    """直接获取订单（不通过数据库）"""
    
    print(f"🚀 开始批量获取订单...")
    print(f"商店: {shop_name}.myshopify.com")
    print(f"过滤条件: {query_filter or '无'}")
    print(f"最大数量: {max_orders or '无限制'}")
    print("-" * 50)
    
    # 创建客户端
    client = create_shopify_client(shop_name, access_token)
    
    # 获取商店信息
    try:
        shop_info = await client.get_shop_info()
        print(f"✅ 商店信息: {shop_info.get('name')} ({shop_info.get('currencyCode')})")
    except Exception as e:
        print(f"❌ 获取商店信息失败: {e}")
        return
    
    # 获取订单
    orders = []
    order_count = 0
    
    try:
        async for order in client.get_all_orders(
            query_filter=query_filter,
            max_orders=max_orders
        ):
            order_count += 1
            orders.append(order)
            
            # 每10个订单显示一次进度
            if order_count % 10 == 0:
                print(f"📦 已获取 {order_count} 个订单...")
            
            # 显示订单基本信息
            if order_count <= 5:  # 只显示前5个订单的详细信息
                total_price = order.get('totalPriceSet', {}).get('shopMoney', {})
                print(f"  订单 {order.get('name')}: {total_price.get('amount', 'N/A')} {total_price.get('currencyCode', '')}")
    
    except Exception as e:
        print(f"❌ 获取订单时出错: {e}")
        return
    
    print(f"\n✅ 订单获取完成！总计: {order_count} 个订单")
    
    # 保存到文件
    if output_file and orders:
        import json
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(orders, f, ensure_ascii=False, indent=2, default=str)
        print(f"📁 订单数据已保存到: {output_file}")
    
    return orders


async def get_order_summary(shop_name: str, access_token: str):
    """获取订单摘要统计"""
    print("📊 获取订单摘要统计...")
    
    client = create_shopify_client(shop_name, access_token)
    
    # 获取不同状态的订单统计
    stats = {}
    
    # 最近24小时的订单
    recent_orders = await client.get_recent_orders(hours=24)
    stats['recent_24h'] = len(recent_orders)
    
    # 未履约订单
    unfulfilled_orders = await client.get_unfulfilled_orders()
    stats['unfulfilled'] = len(unfulfilled_orders)
    
    # 已支付订单
    paid_orders = await client.get_paid_orders()
    stats['paid'] = len(paid_orders)
    
    print("\n📈 订单统计:")
    print(f"  最近24小时: {stats['recent_24h']} 个订单")
    print(f"  未履约订单: {stats['unfulfilled']} 个订单")
    print(f"  已支付订单: {stats['paid']} 个订单")
    
    return stats


def main():
    parser = argparse.ArgumentParser(description='批量订单处理工具')
    parser.add_argument('--shop', required=True, help='Shopify 商店名称')
    parser.add_argument('--token', required=True, help='访问令牌')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 获取订单命令
    fetch_parser = subparsers.add_parser('fetch', help='批量获取订单')
    fetch_parser.add_argument('--filter', help='订单过滤条件')
    fetch_parser.add_argument('--max', type=int, help='最大订单数量')
    fetch_parser.add_argument('--output', help='输出文件路径')
    
    # 获取统计命令
    subparsers.add_parser('stats', help='获取订单统计')
    
    # 获取最近订单命令
    recent_parser = subparsers.add_parser('recent', help='获取最近订单')
    recent_parser.add_argument('--hours', type=int, default=24, help='最近几小时（默认24）')
    recent_parser.add_argument('--output', help='输出文件路径')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 执行相应命令
    if args.command == 'fetch':
        asyncio.run(fetch_orders_direct(
            shop_name=args.shop,
            access_token=args.token,
            query_filter=args.filter,
            max_orders=args.max,
            output_file=args.output
        ))
    
    elif args.command == 'stats':
        asyncio.run(get_order_summary(
            shop_name=args.shop,
            access_token=args.token
        ))
    
    elif args.command == 'recent':
        query_filter = f"created_at:>={datetime.utcnow() - timedelta(hours=args.hours)}"
        asyncio.run(fetch_orders_direct(
            shop_name=args.shop,
            access_token=args.token,
            query_filter=query_filter,
            output_file=args.output
        ))


if __name__ == "__main__":
    main()
