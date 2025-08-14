#!/usr/bin/env python3
"""
Shopify 订单管理脚本
支持从数据库获取 access token 和创建测试订单
"""

import asyncio
import aiohttp
import json
import argparse
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.models.external_system import ExternalSystem, ExternalSystemType
from app.core.security import decrypt_data

# 数据库连接
engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_shopify_access_token_from_db(tenant_id: int = 1) -> Optional[str]:
    """从数据库获取 Shopify access token"""
    async with AsyncSessionLocal() as db:
        # 查找 Shopify 类型的外部系统
        result = await db.execute(
            select(ExternalSystem).where(
                ExternalSystem.tenant_id == tenant_id,
                ExternalSystem.system_type == ExternalSystemType.SHOPIFY,
                ExternalSystem.is_active == True
            )
        )
        external_system = result.scalar_one_or_none()
        
        if not external_system:
            print("未找到活跃的 Shopify 外部系统")
            return None
        
        # 解密 credentials
        credentials = external_system.credentials
        if 'access_token' in credentials:
            try:
                access_token = decrypt_data(credentials['access_token'])
                return access_token
            except Exception as e:
                print(f"解密 access token 失败: {e}")
                return None
        
        print("未找到 access_token")
        return None


async def create_shopify_order(
    shop_name: str,
    access_token: str,
    order_data: Dict[str, Any]
) -> Dict[str, Any]:
    """创建 Shopify 订单"""
    
    url = f"https://{shop_name}.myshopify.com/admin/api/2025-07/orders.json"
    headers = {
        'Content-Type': 'application/json',
        'X-Shopify-Access-Token': access_token
    }
    
    print(f"🌐 发送请求到: {url}")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            headers=headers,
            json=order_data,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            print(f"📡 响应状态: {response.status}")
            
            if response.status == 201:
                data = await response.json()
                print(f"✅ 订单创建成功!")
                return data
            else:
                error_text = await response.text()
                print(f"❌ 创建订单失败: HTTP {response.status}")
                print(f"错误信息: {error_text}")
                return None


def get_test_order_templates() -> Dict[str, Dict[str, Any]]:
    """获取测试订单模板"""
    return {
        "basic": {
            "order": {
                "email": "test@example.com",
                "financial_status": "pending",
                "fulfillment_status": "unfulfilled",
                "send_receipt": False,
                "send_fulfillment_receipt": False,
                "line_items": [
                    {
                        "title": "测试产品 - T恤",
                        "price": "29.99",
                        "quantity": 2,
                        "variant_title": "M / 蓝色",
                        "sku": "TEST-TSHIRT-M-BLUE",
                        "vendor": "测试供应商"
                    }
                ],
                "shipping_address": {
                    "first_name": "张",
                    "last_name": "三",
                    "address1": "测试地址 123号",
                    "city": "北京",
                    "province": "北京",
                    "country": "中国",
                    "zip": "100000",
                    "phone": "+86 138 0013 8000"
                },
                "billing_address": {
                    "first_name": "张",
                    "last_name": "三",
                    "address1": "测试地址 123号",
                    "city": "北京",
                    "province": "北京",
                    "country": "中国",
                    "zip": "100000",
                    "phone": "+86 138 0013 8000"
                },
                "note": "基础测试订单",
                "tags": "test, basic",
                "currency": "CNY",
                "customer": {
                    "first_name": "张",
                    "last_name": "三",
                    "email": "test@example.com",
                    "phone": "+86 138 0013 8000"
                }
            }
        },
        "multi_items": {
            "order": {
                "email": "test@example.com",
                "financial_status": "pending",
                "fulfillment_status": "unfulfilled",
                "send_receipt": False,
                "send_fulfillment_receipt": False,
                "line_items": [
                    {
                        "title": "测试产品 - T恤",
                        "price": "29.99",
                        "quantity": 2,
                        "variant_title": "M / 蓝色",
                        "sku": "TEST-TSHIRT-M-BLUE",
                        "vendor": "测试供应商"
                    },
                    {
                        "title": "测试产品 - 帽子",
                        "price": "19.99",
                        "quantity": 1,
                        "variant_title": "L / 黑色",
                        "sku": "TEST-HAT-L-BLACK",
                        "vendor": "测试供应商"
                    },
                    {
                        "title": "测试产品 - 手机壳",
                        "price": "15.99",
                        "quantity": 3,
                        "variant_title": "iPhone 14 / 透明",
                        "sku": "TEST-CASE-IPHONE14-CLEAR",
                        "vendor": "测试供应商"
                    }
                ],
                "shipping_address": {
                    "first_name": "李",
                    "last_name": "四",
                    "address1": "测试地址 456号",
                    "city": "上海",
                    "province": "上海",
                    "country": "中国",
                    "zip": "200000",
                    "phone": "+86 139 0013 9000"
                },
                "billing_address": {
                    "first_name": "李",
                    "last_name": "四",
                    "address1": "测试地址 456号",
                    "city": "上海",
                    "province": "上海",
                    "country": "中国",
                    "zip": "200000",
                    "phone": "+86 139 0013 9000"
                },
                "note": "多商品测试订单",
                "tags": "test, multi-items",
                "currency": "CNY",
                "customer": {
                    "first_name": "李",
                    "last_name": "四",
                    "email": "test@example.com",
                    "phone": "+86 139 0013 9000"
                }
            }
        },
        "paid": {
            "order": {
                "email": "test@example.com",
                "financial_status": "paid",
                "fulfillment_status": "unfulfilled",
                "send_receipt": False,
                "send_fulfillment_receipt": False,
                "line_items": [
                    {
                        "title": "测试产品 - 高级T恤",
                        "price": "99.99",
                        "quantity": 1,
                        "variant_title": "XL / 红色",
                        "sku": "TEST-PREMIUM-TSHIRT-XL-RED",
                        "vendor": "测试供应商"
                    }
                ],
                "shipping_address": {
                    "first_name": "王",
                    "last_name": "五",
                    "address1": "测试地址 789号",
                    "city": "广州",
                    "province": "广东",
                    "country": "中国",
                    "zip": "510000",
                    "phone": "+86 137 0013 7000"
                },
                "billing_address": {
                    "first_name": "王",
                    "last_name": "五",
                    "address1": "测试地址 789号",
                    "city": "广州",
                    "province": "广东",
                    "country": "中国",
                    "zip": "510000",
                    "phone": "+86 137 0013 7000"
                },
                "note": "已支付测试订单",
                "tags": "test, paid",
                "currency": "CNY",
                "customer": {
                    "first_name": "王",
                    "last_name": "五",
                    "email": "test@example.com",
                    "phone": "+86 137 0013 7000"
                }
            }
        }
    }


async def list_orders(shop_name: str, access_token: str, limit: int = 10) -> List[Dict[str, Any]]:
    """获取订单列表"""
    url = f"https://{shop_name}.myshopify.com/admin/api/2025-07/orders.json?limit={limit}&status=any"
    headers = {
        'Content-Type': 'application/json',
        'X-Shopify-Access-Token': access_token
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('orders', [])
            else:
                error_text = await response.text()
                print(f"❌ 获取订单列表失败: HTTP {response.status}")
                print(f"错误信息: {error_text}")
                return []


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Shopify 订单管理工具')
    parser.add_argument('--action', choices=['create', 'list'], default='create', 
                       help='操作类型: create (创建订单) 或 list (列出订单)')
    parser.add_argument('--template', choices=['basic', 'multi_items', 'paid'], default='basic',
                       help='订单模板类型')
    parser.add_argument('--shop', default='x0ri77-4v', help='Shopify 商店名称')
    parser.add_argument('--token', help='Shopify access token (如果不提供则从数据库获取)')
    parser.add_argument('--limit', type=int, default=10, help='列出订单时的数量限制')
    parser.add_argument('--use-db', action='store_true', help='强制从数据库获取 token')
    
    args = parser.parse_args()
    
    print("🚀 Shopify 订单管理工具")
    
    # 获取 access token
    access_token = None
    if args.token:
        access_token = args.token
        print(f"🔑 使用提供的 access token: {access_token[:20]}...")
    elif args.use_db:
        print("📡 从数据库获取 Shopify access token...")
        access_token = await get_shopify_access_token_from_db()
        if access_token:
            print(f"✅ 成功获取 access token: {access_token[:20]}...")
        else:
            print("❌ 无法从数据库获取 access token")
            return
    else:
        # 默认使用提供的 token
        access_token = "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"
        print(f"🔑 使用默认 access token: {access_token[:20]}...")
    
    if args.action == 'create':
        print(f"📦 创建 {args.template} 类型的测试订单...")
        
        # 获取订单模板
        templates = get_test_order_templates()
        order_data = templates[args.template]
        
        # 创建订单
        result = await create_shopify_order(args.shop, access_token, order_data)
        
        if result:
            print("\n📋 订单详情:")
            order = result['order']
            print(f"  订单 ID: {order['id']}")
            print(f"  订单号: {order['name']}")
            print(f"  邮箱: {order['email']}")
            print(f"  状态: {order['financial_status']}")
            print(f"  履约状态: {order['fulfillment_status']}")
            print(f"  总金额: {order['total_price']} {order['currency']}")
            print(f"  创建时间: {order['created_at']}")
            
            print("\n📦 商品列表:")
            for item in order['line_items']:
                print(f"  - {item['title']} x{item['quantity']} (¥{item['price']})")
            
            print("\n✅ 测试订单创建完成!")
            print(f"🔗 订单链接: https://{args.shop}.myshopify.com/admin/orders/{order['id']}")
        else:
            print("❌ 创建测试订单失败")
    
    elif args.action == 'list':
        print(f"📋 获取最近 {args.limit} 个订单...")
        
        orders = await list_orders(args.shop, access_token, args.limit)
        
        if orders:
            print(f"\n📋 找到 {len(orders)} 个订单:")
            for order in orders:
                print(f"  - {order['name']} (ID: {order['id']}) - {order['financial_status']} - ¥{order['total_price']}")
                print(f"    邮箱: {order['email']} | 创建时间: {order['created_at']}")
                if order.get('note'):
                    print(f"    备注: {order['note']}")
                print()
        else:
            print("❌ 未找到订单或获取失败")


if __name__ == "__main__":
    asyncio.run(main())
