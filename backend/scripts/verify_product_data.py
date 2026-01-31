#!/usr/bin/env python3
"""
验证商品数据是否正确写入
"""

import asyncio
from sqlalchemy import select
from app.core.database import get_async_db
from app.models.product_new import Product, ProductVariant, ExternalProduct, ProductMapping

async def verify_data():
    print("🔍 验证商品数据...")
    
    async for db in get_async_db():
        try:
            # 查询核心商品
            product_result = await db.execute(select(Product).where(Product.id == 1))
            product = product_result.scalar_one_or_none()
            if product:
                print(f'✅ 核心商品: {product.title} (ID: {product.id})')
                print(f'   Handle: {product.handle}')
                print(f'   状态: {product.status}')
                print(f'   类型: {product.product_type}')
                print(f'   供应商: {product.vendor}')
            else:
                print('❌ 未找到核心商品')
            
            # 查询变体
            variant_result = await db.execute(select(ProductVariant).where(ProductVariant.id == 1))
            variant = variant_result.scalar_one_or_none()
            if variant:
                print(f'✅ 变体: {variant.sku} (ID: {variant.id})')
                print(f'   价格: ${variant.price}')
                print(f'   库存: {variant.inventory_quantity}')
                print(f'   属性: {variant.attributes}')
            else:
                print('❌ 未找到变体')
            
            # 查询外部商品
            external_result = await db.execute(select(ExternalProduct).where(ExternalProduct.id == 1))
            external = external_result.scalar_one_or_none()
            if external:
                print(f'✅ 外部商品: {external.title} (ID: {external.id})')
                print(f'   外部ID: {external.external_product_id}')
                print(f'   同步状态: {external.sync_status}')
            else:
                print('❌ 未找到外部商品')
            
            # 查询映射关系
            mapping_result = await db.execute(select(ProductMapping).where(ProductMapping.id == 1))
            mapping = mapping_result.scalar_one_or_none()
            if mapping:
                print(f'✅ 映射关系: 核心商品 {mapping.core_product_id} <-> 外部商品 {mapping.external_product_id}')
                print(f'   映射类型: {mapping.mapping_type}')
                print(f'   同步方向: {mapping.sync_direction}')
            else:
                print('❌ 未找到映射关系')
                
        except Exception as e:
            print(f'❌ 验证失败: {str(e)}')
        finally:
            await db.close()
        break

if __name__ == "__main__":
    asyncio.run(verify_data())
