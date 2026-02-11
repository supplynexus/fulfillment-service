#!/usr/bin/env python3
"""
获取 Printify 绿色店铺的所有商品

使用方法:

方法 1: 使用 tenant 配置（推荐，最安全）
   python scripts/get_printify_green_store_products.py --tenant impeach

方法 2: 从文件读取 token
   python scripts/get_printify_green_store_products.py --token-file tenants/impeach/printify/api_token.token

方法 3: 直接提供 API key
   python scripts/get_printify_green_store_products.py --api-key YOUR_API_KEY

方法 4: 指定店铺 ID
   python scripts/get_printify_green_store_products.py --tenant impeach --shop-id SHOP_ID

方法 5: 仅列出店铺（用于查找绿色店铺）
   python scripts/get_printify_green_store_products.py --tenant impeach --list-shops-only

获取 API key:
1. 登录 https://printify.com/
2. 进入 My Profile -> Connections
3. 生成 Personal Access Token
4. 保存到 scripts/printify-keys/{token_name}.token
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


def read_token_from_file(token_file: str) -> str:
    """从文件读取 API token"""
    token_path = Path(token_file)
    if not token_path.exists():
        raise FileNotFoundError(f"Token file not found: {token_path}")
    
    with open(token_path, "r", encoding="utf-8") as f:
        token = f.read().strip()
    
    if not token:
        raise ValueError(f"Token file is empty: {token_path}")
    
    return token


async def get_shops(api_key: str) -> list:
    """获取所有 Printify 店铺列表"""
    base_url = "https://api.printify.com/v1"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "SupplyNexus/1.0",
    }
    
    print("🔍 正在获取 Printify 店铺列表...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/shops.json",
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            shops = response.json()
            
            print(f"✅ 成功获取 {len(shops) if isinstance(shops, list) else 0} 个店铺")
            return shops if isinstance(shops, list) else []
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP 错误: {e.response.status_code}")
        print(f"   响应内容: {e.response.text}")
        return []
    except Exception as e:
        print(f"❌ 获取店铺列表失败: {e}")
        return []


async def get_products(api_key: str, shop_id: str) -> list:
    """获取指定店铺的所有商品"""
    base_url = "https://api.printify.com/v1"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "SupplyNexus/1.0",
    }
    
    print(f"🔍 正在获取店铺 {shop_id} 的商品列表...")
    
    all_products = []
    page = 1
    limit = 50  # Printify API 限制：最大 50
    
    try:
        async with httpx.AsyncClient() as client:
            while True:
                # Printify API 使用分页
                params = {"limit": limit, "page": page}
                
                response = await client.get(
                    f"{base_url}/shops/{shop_id}/products.json",
                    headers=headers,
                    params=params,
                    timeout=30.0
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Printify API 返回格式可能是 {"data": [...]} 或直接是列表
                if isinstance(data, dict):
                    products = data.get("data", [])
                    total = data.get("total", len(products))
                else:
                    products = data if isinstance(data, list) else []
                    total = len(products) if products else 0
                
                if not products:
                    break
                
                all_products.extend(products)
                print(f"   已获取 {len(all_products)} / {total if total > 0 else '?'} 个商品...")
                
                # 如果返回的商品数量少于 limit，说明已经是最后一页
                if len(products) < limit:
                    break
                
                page += 1
                
                # 防止无限循环
                if page > 100:
                    print("⚠️  已达到最大页数限制 (100页)")
                    break
            
            print(f"✅ 成功获取 {len(all_products)} 个商品")
            return all_products
            
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP 错误: {e.response.status_code}")
        print(f"   响应内容: {e.response.text}")
        return []
    except Exception as e:
        print(f"❌ 获取商品列表失败: {e}")
        import traceback
        print(f"   错误堆栈: {traceback.format_exc()}")
        return []


def find_green_store(shops: list) -> dict:
    """查找绿色店铺（已连接的店铺）"""
    print("\n📋 店铺列表:")
    print("-" * 80)
    
    connected_shop = None
    
    for i, shop in enumerate(shops, 1):
        shop_id = shop.get("id", "N/A")
        shop_title = shop.get("title", "N/A")
        sales_channel = shop.get("sales_channel", "disconnected")
        is_connected = sales_channel != "disconnected"
        
        # 显示连接状态
        connection_status = "✅ 已连接" if is_connected else "❌ 未连接"
        if is_connected:
            connection_status += f" ({sales_channel})"
        
        print(f"{i}. ID: {shop_id}, 名称: {shop_title}, {connection_status}")
        
        # 记录已连接的店铺（绿色店铺）
        if is_connected:
            connected_shop = shop
            print(f"   ⭐ 这是绿色店铺（已连接）!")
    
    print("-" * 80)
    
    # 优先返回已连接的店铺（绿色店铺）
    if connected_shop:
        return connected_shop
    
    # 如果没有已连接的店铺，返回第一个店铺
    if shops:
        return shops[0]
    return None


async def main():
    parser = argparse.ArgumentParser(description="获取 Printify 绿色店铺的所有商品")
    parser.add_argument("--api-key", help="Printify API key（直接提供）")
    parser.add_argument("--token-file", help="从文件读取 API token（例如：tenants/impeach/printify/api_token.token）")
    parser.add_argument("--tenant", help="Tenant 名称（例如：impeach），会自动从 tenants/{tenant}/printify/ 读取配置")
    parser.add_argument("--shop-id", help="店铺 ID（可选，如果不提供则自动查找绿色店铺）")
    parser.add_argument("--output", default="printify_products.json", help="输出文件路径")
    parser.add_argument("--list-shops-only", action="store_true", help="仅列出店铺，不获取商品")
    
    args = parser.parse_args()
    
    # 获取 API key 和店铺信息
    shop_id_from_config = None
    
    if args.tenant:
        # 从 tenant 配置读取
        tenant_dir = project_root / "tenants" / args.tenant / "printify"
        token_file = tenant_dir / "api_token.token"
        login_info_file = tenant_dir / "login_info.json"
        
        if not token_file.exists():
            print(f"❌ 错误: Tenant {args.tenant} 的 API token 文件不存在: {token_file}")
            exit(1)
        
        api_key = read_token_from_file(str(token_file))
        print(f"✅ 从 tenant '{args.tenant}' 读取 token: {token_file}")
        
        # 读取登录信息和店铺配置
        if login_info_file.exists():
            import json
            with open(login_info_file, "r", encoding="utf-8") as f:
                login_info = json.load(f)
            
            active_shop = login_info.get("active_shop", {})
            shop_id_from_config = active_shop.get("shop_id")
            shop_name = active_shop.get("shop_name", "N/A")
            print(f"✅ 从配置读取店铺信息: {shop_name} (ID: {shop_id_from_config})")
            
            # 如果没有指定 shop-id，使用配置中的店铺
            if not args.shop_id and shop_id_from_config:
                args.shop_id = shop_id_from_config
    elif args.token_file:
        api_key = read_token_from_file(args.token_file)
        print(f"✅ 从文件读取 token: {args.token_file}")
    elif args.api_key:
        api_key = args.api_key
    else:
        parser.error("必须提供 --api-key、--token-file 或 --tenant 参数")
    
    print("=" * 80)
    print("Printify 绿色店铺商品获取工具")
    print("=" * 80)
    print()
    
    # 获取店铺列表
    shops = await get_shops(api_key)
    
    if not shops:
        print("❌ 未找到任何店铺，请检查 API key 是否正确")
        return
    
    print(f"\n✅ 找到 {len(shops)} 个店铺")
    
    # 如果只是列出店铺，则退出
    if args.list_shops_only:
        find_green_store(shops)
        return
    
    # 确定要使用的店铺 ID
    shop_id = args.shop_id
    
    if not shop_id:
        print("\n🔍 自动查找绿色店铺...")
        green_store = find_green_store(shops)
        
        if not green_store:
            print("❌ 未找到绿色店铺")
            return
        
        shop_id = green_store.get("id")
        shop_title = green_store.get("title", "N/A")
        print(f"\n✅ 选择店铺: {shop_title} (ID: {shop_id})")
    else:
        print(f"\n✅ 使用指定的店铺 ID: {shop_id}")
    
    # 获取商品列表
    products = await get_products(api_key, shop_id)
    
    if not products:
        print("❌ 未获取到任何商品")
        return
    
    # 保存到文件
    output_path = Path(args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "shop_id": shop_id,
            "total_count": len(products),
            "products": products
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 商品数据已保存到: {output_path}")
    print(f"   共 {len(products)} 个商品")
    
    # 显示商品摘要
    print("\n📦 商品摘要:")
    print("-" * 80)
    for i, product in enumerate(products[:10], 1):  # 只显示前10个
        product_id = product.get("id", "N/A")
        product_title = product.get("title", "N/A")
        is_visible = product.get("is_visible", False)
        print(f"{i}. {product_title} (ID: {product_id}, 可见: {is_visible})")
    
    if len(products) > 10:
        print(f"... 还有 {len(products) - 10} 个商品")
    print("-" * 80)


if __name__ == "__main__":
    asyncio.run(main())
