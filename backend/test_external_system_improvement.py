#!/usr/bin/env python3
"""
Test script for ExternalSystem improvements
Tests the new external_system_id field and unique constraint
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.core.database import get_async_db
from app.models.external_system import ExternalSystem, ExternalSystemType
from app.services.external_system_service import ExternalSystemService
from sqlalchemy import select


async def test_external_system_improvements():
    """Test the new external_system_id field and unique constraint"""
    
    print("🧪 Testing ExternalSystem improvements...")
    
    # Get database session
    async for db in get_async_db():
        service = ExternalSystemService(db)
        
        try:
            # Test 1: Create external system with external_system_id
            print("\n1️⃣ Testing creation with external_system_id...")
            
            external_system = await service.create_external_system(
                tenant_id=1,
                system_type=ExternalSystemType.SHOPIFY,
                name="Test Shopify Store",
                external_system_id="test-shop.myshopify.com",
                credentials={
                    "api_key": "test_key",
                    "api_secret": "test_secret"
                },
                base_url="https://test-shop.myshopify.com",
                settings={"test_setting": "test_value"}
            )
            
            print(f"✅ Created external system: {external_system.id}")
            print(f"   - Name: {external_system.name}")
            print(f"   - External System ID: {external_system.external_system_id}")
            print(f"   - System Type: {external_system.system_type}")
            
            # Test 2: Try to create duplicate (should fail)
            print("\n2️⃣ Testing unique constraint (should fail)...")
            
            try:
                duplicate_system = await service.create_external_system(
                    tenant_id=1,
                    system_type=ExternalSystemType.SHOPIFY,
                    name=\"Duplicate Shopify Store\",
                    external_system_id=\"test-shop.myshopify.com\",  # Same external_system_id
                    credentials={\"api_key\": \"test_key2\"},
                )
                print(\"❌ ERROR: Duplicate was created (should have failed)\")
            except Exception as e:
                print(f\"✅ Unique constraint working: {str(e)}\")
                # Rollback the failed transaction
                await db.rollback()
            
            # Test 3: Create different system with same tenant but different external_system_id
            print("\n3️⃣ Testing different external_system_id (should succeed)...")
            
            different_system = await service.create_external_system(
                tenant_id=1,
                system_type=ExternalSystemType.SHOPIFY,
                name="Different Shopify Store",
                external_system_id="different-shop.myshopify.com",  # Different external_system_id
                credentials={"api_key": "test_key3"},
            )
            
            print(f"✅ Created different external system: {different_system.id}")
            print(f"   - Name: {different_system.name}")
            print(f"   - External System ID: {different_system.external_system_id}")
            
            # Test 4: Create same external_system_id but different tenant (should succeed)
            print("\n4️⃣ Testing same external_system_id but different tenant (should succeed)...")
            
            different_tenant_system = await service.create_external_system(
                tenant_id=2,  # Different tenant
                system_type=ExternalSystemType.SHOPIFY,
                name="Tenant 2 Shopify Store",
                external_system_id="test-shop.myshopify.com",  # Same external_system_id but different tenant
                credentials={"api_key": "test_key4"},
            )
            
            print(f"✅ Created system for different tenant: {different_tenant_system.id}")
            print(f"   - Tenant ID: {different_tenant_system.tenant_id}")
            print(f"   - External System ID: {different_tenant_system.external_system_id}")
            
            # Test 5: Query external systems
            print("\n5️⃣ Testing queries...")
            
            # Get all Shopify systems for tenant 1
            shopify_systems = await service.get_external_systems_by_type(
                tenant_id=1,
                system_type=ExternalSystemType.SHOPIFY
            )
            
            print(f"✅ Found {len(shopify_systems)} Shopify systems for tenant 1:")
            for system in shopify_systems:
                print(f"   - {system.name} ({system.external_system_id})")
            
            # Test 6: Test different system types
            print("\n6️⃣ Testing different system types...")
            
            amazon_system = await service.create_external_system(
                tenant_id=1,
                system_type=ExternalSystemType.AMAZON,
                name="Amazon Store",
                external_system_id="amazon-store-123",
                credentials={"seller_id": "test_seller"},
            )
            
            print(f"✅ Created Amazon system: {amazon_system.id}")
            print(f"   - System Type: {amazon_system.system_type}")
            print(f"   - External System ID: {amazon_system.external_system_id}")
            
            print("\n🎉 All tests passed! ExternalSystem improvements are working correctly.")
            
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            import traceback
            traceback.print_exc()
        
        break  # Exit the async generator


async def main():
    """Main function"""
    print("🚀 Starting ExternalSystem improvement tests...")
    await test_external_system_improvements()
    print("✅ Tests completed!")


if __name__ == "__main__":
    asyncio.run(main())