#!/usr/bin/env python3
"""
获取 Shopify 店铺的所有商品

使用方法:

方法 1: 使用 tenant 配置（推荐，最安全）
   python scripts/get_shopify_store_products.py --tenant impeach

方法 2: 从文件读取配置
   python scripts/get_shopify_store_products.py --config-file tenants/impeach/shopify/login_info.json

方法 3: 直接提供参数
   python scripts/get_shopify_store_products.py --shop-id x0ri77-4v --access-token YOUR_ACCESS_TOKEN

方法 4: 仅列出店铺信息（用于验证配置）
   python scripts/get_shopify_store_products.py --tenant impeach --list-shop-only
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "backend"))

import httpx


class ShopifyService:
    """Shopify API 服务"""

    def __init__(self, shop_id: str, access_token: str, api_version: str = "2024-10"):
        self.shop_id = shop_id
        self.access_token = access_token
        self.api_version = api_version
        self.base_url = f"https://{shop_id}.myshopify.com/admin/api/{api_version}"
        self.graphql_url = f"{self.base_url}/graphql.json"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def get_shop_info(self) -> dict:
        """获取店铺信息"""
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token,
        }

        query = """
        query {
            shop {
                id
                name
                email
                myshopifyDomain
                plan {
                    displayName
                }
                currencyCode
                primaryDomain {
                    host
                    url
                }
            }
        }
        """

        try:
            response = await self.client.post(
                self.graphql_url,
                headers=headers,
                json={"query": query},
            )
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                return {"success": False, "error": data["errors"][0]["message"]}

            shop_data = data.get("data", {}).get("shop", {})
            return {"success": True, "shop": shop_data}

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return {"success": False, "error": "认证失败：Access Token 无效或已过期"}
            return {"success": False, "error": f"HTTP {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_products(self, limit: int = 50, after: str = None) -> dict:
        """获取商品列表（支持分页）"""
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token,
        }

        # 构建查询参数
        args = [f"first: {limit}"]
        if after:
            args.append(f'after: "{after}"')
        args_str = ", ".join(args)

        query = f"""
        query GetProducts {{
            products({args_str}) {{
                nodes {{
                    id
                    title
                    handle
                    description
                    productType
                    vendor
                    tags
                    status
                    createdAt
                    updatedAt
                    publishedAt
                    totalInventory
                    tracksInventory
                    priceRangeV2 {{
                        minVariantPrice {{
                            amount
                            currencyCode
                        }}
                        maxVariantPrice {{
                            amount
                            currencyCode
                        }}
                    }}
                    variants(first: 50) {{
                        nodes {{
                            id
                            title
                            sku
                            barcode
                            price
                            compareAtPrice
                            inventoryQuantity
                            selectedOptions {{
                                name
                                value
                            }}
                        }}
                    }}
                    media(first: 5) {{
                        nodes {{
                            id
                            alt
                            mediaContentType
                            ... on MediaImage {{
                                image {{
                                    url
                                    width
                                    height
                                    altText
                                }}
                            }}
                        }}
                    }}
                    onlineStoreUrl
                }}
                pageInfo {{
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                }}
            }}
        }}
        """

        try:
            response = await self.client.post(
                self.graphql_url,
                headers=headers,
                json={"query": query},
            )
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                return {"success": False, "error": data["errors"][0]["message"]}

            products_data = data.get("data", {}).get("products", {})
            return {
                "success": True,
                "products": products_data.get("nodes", []),
                "pageInfo": products_data.get("pageInfo", {}),
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return {"success": False, "error": "认证失败：Access Token 无效或已过期"}
            return {"success": False, "error": f"HTTP {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()


async def main():
    parser = argparse.ArgumentParser(description="获取 Shopify 店铺的所有商品。")
    parser.add_argument("--shop-id", help="Shopify 店铺 ID (例如: x0ri77-4v)")
    parser.add_argument("--access-token", help="Shopify Access Token")
    parser.add_argument("--config-file", help="包含 Shopify 配置的 JSON 文件路径")
    parser.add_argument("--tenant", help="指定租户名称，将从 tenants/{tenant}/shopify/ 读取配置")
    parser.add_argument("--api-version", default="2024-10", help="Shopify API 版本 (默认: 2024-10)")
    parser.add_argument("--output", default="shopify_store_products.json", help="输出 JSON 文件的路径")
    parser.add_argument("--list-shop-only", action="store_true", help="只列出店铺信息，不获取商品")
    args = parser.parse_args()

    shop_id = args.shop_id
    access_token = args.access_token
    shop_info = None

    # 从 tenant 配置读取
    if args.tenant:
        tenant_dir = Path(__file__).parent.parent / "tenants" / args.tenant / "shopify"
        config_file = tenant_dir / "login_info.json"

        if config_file.exists():
            with open(config_file, "r") as f:
                config = json.load(f)
                if not shop_id:
                    shop_id = config.get("shop_id")
                if not access_token:
                    access_token = config.get("access_token")
                if args.api_version == "2024-10":
                    args.api_version = config.get("api_version", "2024-10")
                shop_info = config
                print(f"✅ 从 tenant '{args.tenant}' 读取配置: {config_file}")
        else:
            print(f"❌ Tenant '{args.tenant}' 的 Shopify 配置文件不存在: {config_file}")
            return

    # 从配置文件读取
    elif args.config_file:
        config_file = Path(args.config_file)
        if config_file.exists():
            with open(config_file, "r") as f:
                config = json.load(f)
                if not shop_id:
                    shop_id = config.get("shop_id")
                if not access_token:
                    access_token = config.get("access_token")
                shop_info = config
                print(f"✅ 从配置文件读取: {config_file}")
        else:
            print(f"❌ 配置文件不存在: {config_file}")
            return

    if not shop_id or not access_token:
        print("❌ 未提供 Shopify 店铺 ID 或 Access Token。")
        print("   请使用 --tenant, --config-file 或 --shop-id --access-token 参数。")
        return

    service = ShopifyService(shop_id, access_token, args.api_version)

    # 获取店铺信息
    print(f"\n🔍 获取店铺信息: {shop_id}")
    shop_result = await service.get_shop_info()
    if not shop_result.get("success"):
        print(f"❌ 获取店铺信息失败: {shop_result.get('error')}")
        await service.close()
        return

    shop_data = shop_result.get("shop", {})
    print(f"✅ 店铺名称: {shop_data.get('name', 'N/A')}")
    print(f"   域名: {shop_data.get('myshopifyDomain', 'N/A')}")
    print(f"   邮箱: {shop_data.get('email', 'N/A')}")
    print(f"   计划: {shop_data.get('plan', {}).get('displayName', 'N/A')}")
    print(f"   货币: {shop_data.get('currencyCode', 'N/A')}")

    if args.list_shop_only:
        await service.close()
        return

    # 获取所有商品
    print(f"\n🔍 开始获取商品列表...")
    all_products = []
    page = 1
    has_more = True
    after = None
    limit = 50  # Shopify GraphQL API 限制

    while has_more:
        result = await service.get_products(limit=limit, after=after)
        if not result.get("success"):
            print(f"❌ 获取商品失败: {result.get('error')}")
            break

        products = result.get("products", [])
        all_products.extend(products)
        page_info = result.get("pageInfo", {})

        print(f"   已获取 {len(all_products)} 个商品...")

        if page_info.get("hasNextPage"):
            after = page_info.get("endCursor")
            page += 1
            await asyncio.sleep(0.5)  # 避免速率限制
        else:
            has_more = False

    # 保存结果
    output_data = {
        "shop_id": shop_id,
        "shop_info": shop_data,
        "total_count": len(all_products),
        "products": all_products,
    }

    output_file = args.output
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 商品数据已保存到: {output_file}")
    print(f"   共 {len(all_products)} 个商品")

    # 显示商品摘要
    if all_products:
        print(f"\n📊 商品摘要:")
        print(f"   - 已发布: {sum(1 for p in all_products if p.get('status') == 'ACTIVE')}")
        print(f"   - 草稿: {sum(1 for p in all_products if p.get('status') == 'DRAFT')}")
        print(f"   - 已归档: {sum(1 for p in all_products if p.get('status') == 'ARCHIVED')}")
        print(f"\n   前 5 个商品:")
        for i, product in enumerate(all_products[:5], 1):
            price_range = product.get("priceRangeV2", {})
            min_price = price_range.get("minVariantPrice", {})
            print(f"   {i}. {product.get('title', 'N/A')} - {min_price.get('amount', 'N/A')} {min_price.get('currencyCode', 'USD')}")

    await service.close()


if __name__ == "__main__":
    asyncio.run(main())
