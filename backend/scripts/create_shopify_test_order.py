#!/usr/bin/env python3
"""
创建 Shopify 测试订单的简单脚本
直接使用提供的 token 和 store 信息
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any


async def create_shopify_test_order(
    shop_name: str,
    access_token: str,
    order_data: Dict[str, Any]
) -> Dict[str, Any]:
    """创建 Shopify 测试订单"""
    
    url = f"https://{shop_name}.myshopify.com/admin/api/2025-07/orders.json"
    headers = {
        'Content-Type': 'application/json',
        'X-Shopify-Access-Token': access_token
    }
    
    print(f"🌐 发送请求到: {url}")
    print(f"📋 订单数据: {json.dumps(order_data, indent=2, ensure_ascii=False)}")
    
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


async def main():
    """主函数"""
    print("🚀 开始创建 Shopify 测试订单...")
    
    # 使用提供的凭据
    shop_name = "x0ri77-4v"
    access_token = "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"
    
    print(f"🏪 商店: {shop_name}")
    print(f"🔑 Access Token: {access_token[:20]}...")
    
    # 创建测试订单数据
    test_order_data = {
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
            "note": "这是一个测试订单，用于测试 fulfillment service",
            "tags": "test, fulfillment-test",
            "currency": "CNY",
            "customer": {
                "first_name": "张",
                "last_name": "三",
                "email": "test@example.com",
                "phone": "+86 138 0013 8000"
            }
        }
    }
    
    print(f"📦 创建测试订单...")
    
    # 创建订单
    result = await create_shopify_test_order(shop_name, access_token, test_order_data)
    
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
        print(f"🔗 订单链接: https://{shop_name}.myshopify.com/admin/orders/{order['id']}")
    else:
        print("❌ 创建测试订单失败")


if __name__ == "__main__":
    asyncio.run(main())
