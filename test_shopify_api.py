#!/usr/bin/env python3
"""
测试 Shopify API 连接 - 支持 REST API 和 GraphQL API
"""
import requests
import json
import os
from urllib.parse import urlparse

def test_shopify_graphql_api(shop_name, access_token):
    """测试 Shopify GraphQL API 访问"""
    
    print("🔍 测试 Shopify GraphQL API 连接...")
    print(f"商店: {shop_name}.myshopify.com")
    print(f"Token: {access_token[:20]}...")
    
    # GraphQL API 端点
    url = f"https://{shop_name}.myshopify.com/admin/api/unstable/graphql.json"
    headers = {
        'Content-Type': 'application/json',
        'X-Shopify-Access-Token': access_token
    }
    
    # 测试 1: 获取商店信息
    print("\n📋 测试 1: 获取商店基本信息")
    query1 = """
    query {
      shop {
        name
        email
        myshopifyDomain
        currencyCode
        timezoneAbbreviation
        plan {
          displayName
        }
      }
    }
    """
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json={'query': query1},
            timeout=10
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'errors' in data:
                print(f"❌ GraphQL 错误: {data['errors']}")
            else:
                shop = data.get('data', {}).get('shop', {})
                print("✅ 商店信息获取成功:")
                print(f"  商店名称: {shop.get('name', 'N/A')}")
                print(f"  邮箱: {shop.get('email', 'N/A')}")
                print(f"  域名: {shop.get('myshopifyDomain', 'N/A')}")
                print(f"  货币: {shop.get('currencyCode', 'N/A')}")
                print(f"  时区: {shop.get('timezoneAbbreviation', 'N/A')}")
                plan = shop.get('plan', {})
                print(f"  套餐: {plan.get('displayName', 'N/A')}")
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求错误: {e}")
    
    # 测试 2: 获取产品列表
    print("\n📦 测试 2: 获取产品列表")
    query2 = """
    query {
      products(first: 5) {
        edges {
          node {
            id
            title
            handle
            status
            totalInventory
            priceRangeV2 {
              minVariantPrice {
                amount
                currencyCode
              }
            }
          }
        }
      }
    }
    """
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json={'query': query2},
            timeout=10
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'errors' in data:
                print(f"❌ GraphQL 错误: {data['errors']}")
            else:
                products = data.get('data', {}).get('products', {}).get('edges', [])
                print(f"✅ 找到 {len(products)} 个产品:")
                
                for i, edge in enumerate(products, 1):
                    product = edge['node']
                    price_info = product.get('priceRangeV2', {}).get('minVariantPrice', {})
                    price = f"{price_info.get('amount', 'N/A')} {price_info.get('currencyCode', '')}"
                    print(f"  {i}. {product.get('title', 'N/A')}")
                    print(f"     状态: {product.get('status', 'N/A')} | 价格: {price}")
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求错误: {e}")

    # 测试 3: 获取订单列表
    print("\n📋 测试 3: 获取订单列表")
    query3 = """
    query {
      orders(first: 5) {
        edges {
          node {
            id
            name
            displayFinancialStatus
            displayFulfillmentStatus
            totalPriceSet {
              shopMoney {
                amount
                currencyCode
              }
            }
            customer {
              displayName
              email
            }
            createdAt
          }
        }
      }
    }
    """
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json={'query': query3},
            timeout=10
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'errors' in data:
                print(f"❌ GraphQL 错误: {data['errors']}")
            else:
                orders = data.get('data', {}).get('orders', {}).get('edges', [])
                print(f"✅ 找到 {len(orders)} 个订单:")
                
                for i, edge in enumerate(orders, 1):
                    order = edge['node']
                    total_price = order.get('totalPriceSet', {}).get('shopMoney', {})
                    customer = order.get('customer', {})
                    
                    print(f"  {i}. 订单 {order.get('name', 'N/A')}")
                    print(f"     金额: {total_price.get('amount', 'N/A')} {total_price.get('currencyCode', '')}")
                    print(f"     支付状态: {order.get('displayFinancialStatus', 'N/A')}")
                    print(f"     客户: {customer.get('displayName', customer.get('email', 'N/A'))}")
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求错误: {e}")

def get_shopify_credentials():
    """提示用户输入 Shopify 凭证"""
    print("🔑 请提供您的 Shopify API 凭证:")
    print("(GraphQL API 只需要 Shop Name 和 Access Token)")
    print()
    
    shop_name = input("商店名称 (不包含.myshopify.com): ").strip()
    access_token = input("Access Token (shpat_...): ").strip()
    
    return shop_name, access_token

if __name__ == "__main__":
    print("🛍️  Shopify GraphQL API 连接测试工具")
    print("=" * 60)
    
    # 检查是否有环境变量
    shop_name = os.getenv("SHOPIFY_SHOP_NAME")
    access_token = os.getenv("SHOPIFY_ACCESS_TOKEN")
    
    if not all([shop_name, access_token]):
        print("⚠️  未检测到环境变量，请手动输入凭证")
        print()
        shop_name, access_token = get_shopify_credentials()
    else:
        print("✅ 使用环境变量中的凭证")
        print(f"商店: {shop_name}.myshopify.com")
        print(f"Token: {access_token[:20]}...")
    
    if shop_name and access_token:
        print("\n🚀 开始测试 GraphQL API...")
        test_shopify_graphql_api(shop_name, access_token)
    else:
        print("❌ 缺少必要的凭证信息")
        
    print("\n" + "=" * 60)
    print("🏁 测试完成")
    print("\n💡 提示:")
    print("  - 设置环境变量: export SHOPIFY_SHOP_NAME='your-shop'")
    print("  - 设置环境变量: export SHOPIFY_ACCESS_TOKEN='shpat_...'")
    print("  - GraphQL API 文档: https://shopify.dev/docs/api/admin-graphql")
