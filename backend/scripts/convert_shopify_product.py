#!/usr/bin/env python3
"""
将 Shopify 商品转换为核心系统商品的脚本
"""

import asyncio
import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_async_db
from app.models.tenant import Tenant
from app.models.external_system import ExternalSystem, ExternalSystemType
from app.models.product_new import (
    Product, ProductDimension, ProductVariant, VariantAttribute,
    ExternalProduct, ProductMapping, ProductStatus
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# Shopify 商品数据
SHOPIFY_PRODUCT_DATA = {
    "id": "gid://shopify/Product/8040175042660",
    "title": "Unisex Oversized Boxy Tee",
    "handle": "unisex-oversized-boxy-tee",
    "status": "ACTIVE",
    "created_at": "2025-04-08T04:55:39Z",
    "updated_at": "2025-08-28T03:22:34Z",
    "total_inventory": 0,
    "price": "41.17",
    "currency": "USD",
    "image": {
        "id": "gid://shopify/ProductImage/36354959540324",
        "url": "https://cdn.shopify.com/s/files/1/0704/6460/2212/files/4640691171255970951_2048.jpg?v=1744088150",
        "alt_text": "",
        "width": 2048,
        "height": 2048
    },
    "variant": {
        "id": "gid://shopify/ProductVariant/45663476547684",
        "title": "Black / S",
        "price": "41.17",
        "inventory_quantity": 0,
        "image": {
            "id": "gid://shopify/ProductImage/36354959540324",
            "url": "https://cdn.shopify.com/s/files/1/0704/6460/2212/files/4640691171255970951_2048.jpg?v=1744088150",
            "alt_text": None
        }
    }
}


async def get_tenant_and_external_system(db: AsyncSession) -> tuple[Tenant, ExternalSystem]:
    """获取租户和外部系统信息"""
    logger.info("🔍 获取租户和外部系统信息")
    
    # 获取租户
    tenant_result = await db.execute(select(Tenant).where(Tenant.name == "impeach"))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise ValueError("未找到 'impeach' 租户")
    
    logger.info(f"✅ 找到租户: {tenant.name} (ID: {tenant.id})")
    
    # 获取 Shopify 外部系统
    external_system_result = await db.execute(
        select(ExternalSystem).where(
            ExternalSystem.tenant_id == tenant.id,
            ExternalSystem.system_type == ExternalSystemType.SHOPIFY
        )
    )
    external_system = external_system_result.scalar_one_or_none()
    if not external_system:
        raise ValueError("未找到 Shopify 外部系统")
    
    logger.info(f"✅ 找到外部系统: {external_system.name} (ID: {external_system.id})")
    
    return tenant, external_system


async def create_core_product(db: AsyncSession, tenant: Tenant, shopify_data: Dict[str, Any]) -> Product:
    """创建核心商品"""
    logger.info("🔍 创建核心商品")
    
    # 检查是否已存在相同 handle 的商品
    existing_product = await db.execute(
        select(Product).where(
            Product.tenant_id == tenant.id,
            Product.handle == shopify_data["handle"]
        )
    )
    if existing_product.scalar_one_or_none():
        raise ValueError(f"商品 handle '{shopify_data['handle']}' 已存在")
    
    # 创建核心商品
    product = Product(
        tenant_id=tenant.id,
        title=shopify_data["title"],
        handle=shopify_data["handle"],
        description=f"从 Shopify 导入的商品: {shopify_data['title']}",
        product_type="Apparel",
        vendor="Unknown",
        status=ProductStatus.ACTIVE if shopify_data["status"] == "ACTIVE" else ProductStatus.DRAFT,
        is_active=True,
        is_available=True,
        images=[shopify_data["image"]] if shopify_data.get("image") else None,
        seo={"currency": shopify_data.get("currency", "USD")}
    )
    
    db.add(product)
    await db.flush()  # 获取 ID
    
    logger.info(f"✅ 创建核心商品: {product.title} (ID: {product.id})")
    return product


async def create_product_dimensions(db: AsyncSession, tenant: Tenant, product: Product) -> tuple[ProductDimension, ProductDimension]:
    """创建商品维度（颜色和尺寸）"""
    logger.info("🔍 创建商品维度")
    
    # 创建颜色维度
    color_dimension = ProductDimension(
        tenant_id=tenant.id,
        product_id=product.id,
        dimension_name="color",
        dimension_type="select",
        display_name="颜色",
        description="商品颜色",
        options=["Black", "White", "Red", "Blue", "Green"],  # 预设选项
        is_required=True,
        display_order=1
    )
    
    # 创建尺寸维度
    size_dimension = ProductDimension(
        tenant_id=tenant.id,
        product_id=product.id,
        dimension_name="size",
        dimension_type="select",
        display_name="尺寸",
        description="商品尺寸",
        options=["XS", "S", "M", "L", "XL", "XXL"],  # 预设选项
        is_required=True,
        display_order=2
    )
    
    db.add(color_dimension)
    db.add(size_dimension)
    await db.flush()
    
    logger.info(f"✅ 创建维度: 颜色 (ID: {color_dimension.id}), 尺寸 (ID: {size_dimension.id})")
    return color_dimension, size_dimension


async def create_product_variant(
    db: AsyncSession, 
    tenant: Tenant, 
    product: Product, 
    shopify_data: Dict[str, Any]
) -> ProductVariant:
    """创建商品变体"""
    logger.info("🔍 创建商品变体")
    
    variant_data = shopify_data["variant"]
    
    # 解析变体标题获取颜色和尺寸
    title_parts = variant_data["title"].split(" / ")
    color = title_parts[0] if len(title_parts) > 0 else "Unknown"
    size = title_parts[1] if len(title_parts) > 1 else "Unknown"
    
    # 创建变体
    variant = ProductVariant(
        tenant_id=tenant.id,
        product_id=product.id,
        sku=f"SHOPIFY-{shopify_data['id'].split('/')[-1]}-{variant_data['id'].split('/')[-1]}",
        barcode=None,  # 可以后续添加
        attributes={"color": color, "size": size},
        price=Decimal(variant_data["price"]),
        inventory_quantity=int(variant_data["inventory_quantity"]),
        inventory_policy="deny",
        tracks_inventory=True,
        is_active=True,
        is_available=True,
        image_url=variant_data.get("image", {}).get("url") if variant_data.get("image") else None
    )
    
    db.add(variant)
    await db.flush()
    
    logger.info(f"✅ 创建变体: {variant.sku} (ID: {variant.id})")
    return variant


async def create_variant_attributes(
    db: AsyncSession,
    tenant: Tenant,
    variant: ProductVariant,
    color_dimension: ProductDimension,
    size_dimension: ProductDimension,
    shopify_data: Dict[str, Any]
) -> None:
    """创建变体属性"""
    logger.info("🔍 创建变体属性")
    
    variant_data = shopify_data["variant"]
    title_parts = variant_data["title"].split(" / ")
    color = title_parts[0] if len(title_parts) > 0 else "Unknown"
    size = title_parts[1] if len(title_parts) > 1 else "Unknown"
    
    # 创建颜色属性
    color_attr = VariantAttribute(
        tenant_id=tenant.id,
        variant_id=variant.id,
        dimension_id=color_dimension.id,
        value=color,
        display_value=color,
        sort_order=1
    )
    
    # 创建尺寸属性
    size_attr = VariantAttribute(
        tenant_id=tenant.id,
        variant_id=variant.id,
        dimension_id=size_dimension.id,
        value=size,
        display_value=size,
        sort_order=2
    )
    
    db.add(color_attr)
    db.add(size_attr)
    
    logger.info(f"✅ 创建变体属性: 颜色={color}, 尺寸={size}")


async def create_external_product(
    db: AsyncSession,
    tenant: Tenant,
    external_system: ExternalSystem,
    product: Product,
    variant: ProductVariant,
    shopify_data: Dict[str, Any]
) -> ExternalProduct:
    """创建外部商品记录"""
    logger.info("🔍 创建外部商品记录")
    
    external_product = ExternalProduct(
        tenant_id=tenant.id,
        external_system_id=external_system.id,
        external_product_id=shopify_data["id"],
        external_variant_id=shopify_data["variant"]["id"],
        title=shopify_data["title"],
        description=None,
        handle=shopify_data["handle"],
        status=shopify_data["status"],
        is_active=True,
        is_available=True,
        price=Decimal(shopify_data["price"]),
        inventory_quantity=int(shopify_data["total_inventory"]),
        product_type="Apparel",
        vendor="Unknown",
        tags=None,
        images=[shopify_data["image"]] if shopify_data.get("image") else None,
        variants=[shopify_data["variant"]] if shopify_data.get("variant") else None,
        external_data=shopify_data,
        sync_status="synced",
        last_synced_at=datetime.now()
    )
    
    db.add(external_product)
    await db.flush()
    
    logger.info(f"✅ 创建外部商品记录: {external_product.external_product_id}")
    return external_product


async def create_product_mapping(
    db: AsyncSession,
    tenant: Tenant,
    external_system: ExternalSystem,
    product: Product,
    variant: ProductVariant,
    external_product: ExternalProduct
) -> ProductMapping:
    """创建商品映射关系"""
    logger.info("🔍 创建商品映射关系")
    
    mapping = ProductMapping(
        tenant_id=tenant.id,
        core_product_id=product.id,
        core_variant_id=variant.id,
        external_system_id=external_system.id,
        external_product_id=external_product.external_product_id,
        external_variant_id=external_product.external_variant_id,
        mapping_type="sync",
        sync_direction="bidirectional",
        sync_status="synced",
        last_synced_at=datetime.now(),
        sync_config={"auto_sync": True},
        field_mappings={
            "title": "title",
            "handle": "handle",
            "price": "price",
            "inventory": "inventory_quantity"
        }
    )
    
    db.add(mapping)
    
    logger.info(f"✅ 创建映射关系: 核心商品 {product.id} <-> 外部商品 {external_product.external_product_id}")
    return mapping


async def convert_shopify_product():
    """主函数：转换 Shopify 商品到核心系统"""
    logger.info("🚀 开始转换 Shopify 商品到核心系统")
    
    async for db in get_async_db():
        try:
            # 1. 获取租户和外部系统
            tenant, external_system = await get_tenant_and_external_system(db)
            
            # 2. 创建核心商品
            product = await create_core_product(db, tenant, SHOPIFY_PRODUCT_DATA)
            
            # 3. 创建商品维度
            color_dimension, size_dimension = await create_product_dimensions(db, tenant, product)
            
            # 4. 创建商品变体
            variant = await create_product_variant(db, tenant, product, SHOPIFY_PRODUCT_DATA)
            
            # 5. 创建变体属性
            await create_variant_attributes(
                db, tenant, variant, color_dimension, size_dimension, SHOPIFY_PRODUCT_DATA
            )
            
            # 6. 创建外部商品记录
            external_product = await create_external_product(
                db, tenant, external_system, product, variant, SHOPIFY_PRODUCT_DATA
            )
            
            # 7. 创建映射关系
            await create_product_mapping(
                db, tenant, external_system, product, variant, external_product
            )
            
            # 8. 提交事务
            await db.commit()
            
            logger.info("🎉 Shopify 商品转换完成！")
            logger.info(f"核心商品 ID: {product.id}")
            logger.info(f"变体 ID: {variant.id}")
            logger.info(f"外部商品 ID: {external_product.id}")
            
        except Exception as e:
            await db.rollback()
            logger.error(f"❌ 转换失败: {str(e)}")
            raise
        finally:
            await db.close()


if __name__ == "__main__":
    asyncio.run(convert_shopify_product())
