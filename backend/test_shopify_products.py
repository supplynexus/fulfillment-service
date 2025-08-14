#!/usr/bin/env python3
"""
Test script for Shopify Products API
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.shopify_product_service import ShopifyProductService
from app.core.database import get_async_db


async def test_shopify_products():
    """Test Shopify products functionality"""
    
    print("🧪 Testing Shopify Products API...")
    
    async for db in get_async_db():
        try:
            # Initialize service
            service = ShopifyProductService(db)
            
            # Test 1: Get products list
            print("\n1️⃣ Testing products list...")
            result = await service.fetch_products(tenant_id=1, limit=5)
            products = result.get("data", {}).get("products", {}).get("nodes", [])
            print(f"✅ Retrieved {len(products)} products")
            
            if products:
                # Test 2: Get single product
                product_id = products[0]["id"]
                print(f"\n2️⃣ Testing single product: {product_id}")
                product_result = await service.fetch_product_by_id(tenant_id=1, product_id=product_id)
                product = product_result.get("data", {}).get("product")
                if product:
                    print(f"✅ Retrieved product: {product.get('title', 'Unknown')}")
                else:
                    print("❌ Failed to retrieve product")
            
            # Test 3: Search products
            print("\n3️⃣ Testing product search...")
            search_result = await service.search_products(tenant_id=1, search_term="test", limit=3)
            search_products = search_result.get("data", {}).get("products", {}).get("nodes", [])
            print(f"✅ Search returned {len(search_products)} products")
            
            # Test 4: Get products by status
            print("\n4️⃣ Testing products by status...")
            status_result = await service.get_products_by_status(tenant_id=1, status="ACTIVE", limit=3)
            status_products = status_result.get("data", {}).get("products", {}).get("nodes", [])
            print(f"✅ Active products: {len(status_products)}")
            
            print("\n🎉 All tests completed successfully!")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            break


if __name__ == "__main__":
    asyncio.run(test_shopify_products())
