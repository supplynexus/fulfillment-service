#!/usr/bin/env python3
"""
Test script for Shopify product sync functionality
"""

import asyncio
import httpx
import json
from datetime import datetime
import hashlib
import hmac
import base64

# Configuration
BASE_URL = "http://localhost:8000"
TENANT_ID = 1  # impeach tenant
TENANT_HASHID = "PoRpOk2e"

# Test private key (from your system)
PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7VJTUt9Us8cKB
zVcQmx/8VKUVyH2/2R4DR+03qGnVO0iUXhe1u5C5i1ypHzhkJ0Xm3OVpxeAiB0W2
0fzHyqQnC/7aJsG+lL/1p76F9P8Fmh+rDgExcagI7QIDAQABAoIBADM1.7m1dku0
XSKiS/v/5vcnpyjQIDAQABAoIBADM1.7m1dku0XSKiS/v/5vcnpyjQIDAQABAoIB
ADM1.7m1dku0XSKiS/v/5vcnpyjQIDAQABAoIBADM1.7m1dku0XSKiS/v/5vcnpyj
QIDAQABAoIBADM1.7m1dku0XSKiS/v/5vcnpyjQIDAQABAoIBADM1.7m1dku0XSKi
S/v/5vcnpyjQIDAQABAoIBADM1.7m1dku0XSKiS/v/5vcnpyjQIDAQABAoIBADM1
-----END PRIVATE KEY-----"""


def generate_signature(message: str, private_key: str) -> str:
    """Generate RSA signature for authentication"""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    
    # Load private key
    key = serialization.load_pem_private_key(
        private_key.encode(),
        password=None
    )
    
    # Sign the message
    signature = key.sign(
        message.encode(),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    
    return base64.b64encode(signature).decode()


def generate_headers(tenant_id: int, tenant_hashid: str, private_key: str) -> dict:
    """Generate authentication headers"""
    timestamp = str(int(datetime.utcnow().timestamp()))
    nonce = hashlib.sha256(f"{timestamp}{tenant_id}".encode()).hexdigest()[:16]
    
    # Create message to sign
    message = f"{tenant_id}:{timestamp}:{nonce}"
    
    # Generate signature
    signature = generate_signature(message, private_key)
    
    return {
        "X-Tenant-ID": tenant_hashid,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": signature,
        "Content-Type": "application/json"
    }


async def test_product_sync():
    """Test product sync functionality"""
    print("🔄 Testing Shopify Product Sync...")
    
    headers = generate_headers(TENANT_ID, TENANT_HASHID, PRIVATE_KEY)
    
    async with httpx.AsyncClient() as client:
        try:
            # Test 1: Sync products from Shopify
            print("\n📦 Test 1: Syncing products from Shopify...")
            response = await client.post(
                f"{BASE_URL}/api/v1/shopify/products/sync",
                params={"tenant_id": TENANT_ID, "limit": 5},
                headers=headers
            )
            
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success: {data.get('message')}")
                saved_products = data.get('saved_products', {})
                print(f"📊 Synced {saved_products.get('count', 0)} products")
                
                if saved_products.get('products'):
                    print("📋 Synced products:")
                    for product in saved_products['products']:
                        print(f"  - {product.get('title')} (ID: {product.get('id')})")
            else:
                print(f"❌ Error: {response.text}")
            
            # Test 2: Get local products
            print("\n🏪 Test 2: Getting local products...")
            response = await client.get(
                f"{BASE_URL}/api/v1/products",
                params={"tenant_id": TENANT_ID, "limit": 10},
                headers=headers
            )
            
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success: {data.get('message')}")
                products = data.get('data', {}).get('products', [])
                print(f"📊 Found {len(products)} local products")
                
                if products:
                    print("📋 Local products:")
                    for product in products[:3]:  # Show first 3
                        print(f"  - {product.get('title')} (Type: {product.get('product_type')}, Vendor: {product.get('vendor')})")
                        print(f"    Price: ${product.get('price')}, Inventory: {product.get('total_inventory')}")
            else:
                print(f"❌ Error: {response.text}")
            
            # Test 3: Get raw Shopify products (without saving)
            print("\n🛍️ Test 3: Getting raw Shopify products...")
            response = await client.get(
                f"{BASE_URL}/api/v1/shopify/products",
                params={"tenant_id": TENANT_ID, "limit": 3},
                headers=headers
            )
            
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success: {data.get('message')}")
                shopify_products = data.get('data', {}).get('products', {}).get('nodes', [])
                print(f"📊 Found {len(shopify_products)} Shopify products")
                
                if shopify_products:
                    print("📋 Shopify products:")
                    for product in shopify_products[:2]:  # Show first 2
                        print(f"  - {product.get('title')} (Handle: {product.get('handle')})")
                        print(f"    Type: {product.get('productType')}, Vendor: {product.get('vendor')}")
                        print(f"    Status: {product.get('status')}, Inventory: {product.get('totalInventory')}")
            else:
                print(f"❌ Error: {response.text}")
            
        except Exception as e:
            print(f"❌ Exception: {e}")


async def test_product_search():
    """Test product search functionality"""
    print("\n🔍 Testing Product Search...")
    
    headers = generate_headers(TENANT_ID, TENANT_HASHID, PRIVATE_KEY)
    
    async with httpx.AsyncClient() as client:
        try:
            # Test search by product type
            print("\n📦 Test: Search by product type...")
            response = await client.get(
                f"{BASE_URL}/api/v1/shopify/products/type/Shirt",
                params={"tenant_id": TENANT_ID, "limit": 5},
                headers=headers
            )
            
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success: {data.get('message')}")
                products = data.get('data', {}).get('products', {}).get('nodes', [])
                print(f"📊 Found {len(products)} products of type 'Shirt'")
            else:
                print(f"❌ Error: {response.text}")
            
        except Exception as e:
            print(f"❌ Exception: {e}")


if __name__ == "__main__":
    print("🚀 Starting Shopify Product Sync Tests...")
    print(f"📍 Base URL: {BASE_URL}")
    print(f"🏢 Tenant ID: {TENANT_ID}")
    print(f"🔑 Tenant HashID: {TENANT_HASHID}")
    
    # Run tests
    asyncio.run(test_product_sync())
    asyncio.run(test_product_search())
    
    print("\n✨ Tests completed!")
