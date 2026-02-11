"""
Product management endpoints - 新的商品系统API
"""

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, or_, and_, cast
from sqlalchemy import String, Text
from sqlalchemy.orm import selectinload
from typing import Any, List, Optional
from pydantic import BaseModel

from app.core.database import get_async_db
from app.core.tenant_auth_dependency import verify_tenant_auth
from app.core.logging import get_logger
from app.core.hashids_utils import encode_id, decode_id
from app.models.tenant import Tenant
from app.models.user import User
from app.models.external_system import ExternalSystem, ExternalSystemType
from app.models.product import (
    Product, ProductDimension, ProductVariant, VariantAttribute,
    ProductTag, Tag, ProductMapping, ExternalProduct
)
from app.models.printify_product import PrintifyProduct
from app.models.order import OrderItem
from app.schemas.product import (
    ProductResponse, ProductListResponse, ProductCreateRequest, 
    ProductUpdateRequest, ProductVariantCreateRequest, ProductVariantUpdateRequest,
    ProductDimensionResponse, ProductVariantResponse, ProductTagResponse, 
    ProductMappingResponse, ProductSyncResponse
)
from app.services.printify_service import PrintifyService
from app.services.shopify.product_service import ShopifyProductService
from app.tasks.shopify_tasks import sync_shopify_products_task

router = APIRouter()
logger = get_logger(__name__)


class ProductSyncResponse(BaseModel):
    success: bool
    products_fetched: int = 0
    products_saved: int = 0
    products_updated: int = 0
    errors: List[str] = []
    error: Optional[str] = None


@router.get("/", response_model=ProductListResponse)
async def get_products(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(10, ge=1, le=100, description="每页记录数"),
    status: Optional[str] = Query(None, description="商品状态过滤"),
    product_type: Optional[str] = Query(None, description="商品类型过滤"),
    vendor: Optional[str] = Query(None, description="供应商过滤"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    include_variants: bool = Query(True, description="是否包含变体信息"),
    include_dimensions: bool = Query(True, description="是否包含维度信息"),
    include_tags: bool = Query(True, description="是否包含标签信息"),
    include_mappings: bool = Query(True, description="是否包含映射信息"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    获取商品列表 - 新的商品系统API
    
    支持完整的商品信息查询，包括变体、维度、标签和映射关系
    """
    tenant, user = auth
    
    try:
        logger.info(f"🔍 开始查询商品列表: tenant_id={tenant.id}, user_id={user.id}")
        logger.info(f"   查询参数: skip={skip}, limit={limit}, status={status}, product_type={product_type}")
        logger.info(f"   包含信息: variants={include_variants}, dimensions={include_dimensions}, tags={include_tags}, mappings={include_mappings}")
        
        # 构建查询条件
        conditions = [Product.tenant_id == tenant.id]
        
        if status:
            conditions.append(Product.status == status)
            logger.info(f"   添加状态过滤: {status}")
            
        if product_type:
            conditions.append(Product.product_type == product_type)
            logger.info(f"   添加类型过滤: {product_type}")
            
        if vendor:
            conditions.append(Product.vendor == vendor)
            logger.info(f"   添加供应商过滤: {vendor}")
            
        if search:
            search_condition = Product.title.ilike(f"%{search}%")
            conditions.append(search_condition)
            logger.info(f"   添加搜索过滤: {search}")
        
        # 构建查询语句
        stmt = select(Product).where(*conditions)
        
        # 添加关联查询
        if include_variants:
            stmt = stmt.options(selectinload(Product.variants))
            logger.info("   包含变体信息")
            
        if include_dimensions:
            stmt = stmt.options(selectinload(Product.dimensions))
            logger.info("   包含维度信息")
            
        if include_tags:
            stmt = stmt.options(selectinload(Product.tags).selectinload(ProductTag.tag))
            logger.info("   包含标签信息")
            
        if include_mappings:
            stmt = stmt.options(selectinload(Product.mappings))
            logger.info("   包含映射信息")
        
        # 执行查询
        result = await db.execute(stmt)
        products = result.scalars().all()
        
        logger.info(f"✅ 查询到 {len(products)} 个商品")
        
        # 批量加载当前页商品映射涉及的外部系统，用于显示「映射到谁」(SHOPIFY/PRINTIFY 等)
        external_system_id_to_type: dict[int, str] = {}
        if include_mappings and products:
            es_ids = set()
            for p in products:
                if p.mappings:
                    for m in p.mappings:
                        if m.external_system_id:
                            es_ids.add(m.external_system_id)
            if es_ids:
                es_result = await db.execute(
                    select(ExternalSystem.id, ExternalSystem.system_type).where(
                        ExternalSystem.id.in_(es_ids)
                    )
                )
                for row in es_result.all():
                    external_system_id_to_type[row.id] = row.system_type.value if row.system_type else "Unknown"
        
        # 转换为响应格式
        product_responses = []
        for product in products:
            # 构建维度响应
            dimensions = []
            if include_dimensions and product.dimensions:
                for dimension in product.dimensions:
                    dimensions.append(ProductDimensionResponse(
                        id_hashid=encode_id(dimension.id),
                        dimension_name=dimension.dimension_name,
                        dimension_type=dimension.dimension_type,
                        display_name=dimension.display_name,
                        description=dimension.description,
                        options=dimension.options,
                        is_required=dimension.is_required,
                        display_order=dimension.display_order,
                        is_active=dimension.is_active
                    ))
            
            # 构建变体响应
            variants = []
            if include_variants and product.variants:
                for variant in product.variants:
                    variants.append(ProductVariantResponse(
                        id_hashid=encode_id(variant.id),
                        sku=variant.sku,
                        barcode=variant.barcode,
                        attributes=variant.attributes or {},
                        price=float(variant.price) if variant.price else None,
                        compare_at_price=float(variant.compare_at_price) if variant.compare_at_price else None,
                        cost_price=float(variant.cost_price) if variant.cost_price else None,
                        inventory_quantity=variant.inventory_quantity,
                        inventory_policy=variant.inventory_policy,
                        tracks_inventory=variant.tracks_inventory,
                        is_active=variant.is_active,
                        is_available=variant.is_available,
                        image_url=variant.image_url,
                        weight=float(variant.weight) if variant.weight else None,
                        dimensions=variant.dimensions
                    ))
            
            # 构建标签响应
            tags = []
            if include_tags and product.tags:
                for product_tag in product.tags:
                    if product_tag.tag:
                        tags.append(ProductTagResponse(
                            id_hashid=encode_id(product_tag.tag.id),
                            name=product_tag.tag.name,
                            display_name=product_tag.tag.display_name,
                            color=product_tag.tag.color,
                            category=product_tag.tag.category,
                            is_primary=product_tag.is_primary,
                            sort_order=product_tag.sort_order
                        ))
            
            # 构建映射响应（external_system_name 使用真实系统类型，如 SHOPIFY/PRINTIFY）
            mappings = []
            if include_mappings and product.mappings:
                for mapping in product.mappings:
                    external_system_name = (
                        external_system_id_to_type.get(mapping.external_system_id)
                        if mapping.external_system_id
                        else "Unknown"
                    )
                    mappings.append(ProductMappingResponse(
                        id_hashid=encode_id(mapping.id),
                        external_system_name=external_system_name,
                        external_product_id=mapping.external_product_id,
                        external_variant_id=mapping.external_variant_id,
                        mapping_type=mapping.mapping_type,
                        sync_direction=mapping.sync_direction,
                        sync_status=mapping.sync_status,
                        last_synced_at=mapping.last_synced_at
                    ))
            has_printify_mapping = (
                any(
                    external_system_id_to_type.get(m.external_system_id) == "PRINTIFY"
                    for m in (product.mappings or [])
                )
                if include_mappings and product.mappings
                else None
            )
            # 构建商品响应
            product_response = ProductResponse(
                id_hashid=encode_id(product.id),
                title=product.title,
                description=product.description,
                handle=product.handle,
                product_type=product.product_type,
                vendor=product.vendor,
                status=product.status,
                is_active=product.is_active,
                is_available=product.is_available,
                images=product.images,
                seo=product.seo,
                created_at=product.created_at,
                updated_at=product.updated_at,
                dimensions=dimensions,
                variants=variants,
                tags=tags,
                has_printify_mapping=has_printify_mapping,
                mappings=mappings
            )
            
            product_responses.append(product_response)
        
        # 计算总数
        count_stmt = select(func.count(Product.id)).where(*conditions)
        count_result = await db.execute(count_stmt)
        total = count_result.scalar()
        
        has_more = (skip + limit) < total
        
        logger.info(f"✅ 返回 {len(product_responses)} 个商品，总计 {total} 个")
        logger.info(f"   分页信息: skip={skip}, limit={limit}, has_more={has_more}")
        
        return ProductListResponse(
            products=product_responses,
            total=total,
            skip=skip,
            limit=limit,
            has_more=has_more
        )
        
    except Exception as e:
        logger.error(f"❌ 查询商品失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to get products: {str(e)}")


@router.get("/{product_hashid}", response_model=ProductResponse)
async def get_product(
    product_hashid: str,
    include_variants: bool = Query(True, description="是否包含变体信息"),
    include_dimensions: bool = Query(True, description="是否包含维度信息"),
    include_tags: bool = Query(True, description="是否包含标签信息"),
    include_mappings: bool = Query(True, description="是否包含映射信息"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    获取单个商品详情
    
    通过hashid获取商品的完整信息，包括变体、维度、标签和映射关系
    """
    tenant, user = auth
    
    try:
        logger.info(f"🔍 开始查询商品详情: product_hashid={product_hashid}, tenant_id={tenant.id}, user_id={user.id}")
        
        # 解码hashid
        try:
            product_id = decode_id(product_hashid)
            logger.info(f"✅ Hashid解码成功: {product_hashid} -> {product_id}")
        except Exception as e:
            logger.error(f"❌ Hashid解码失败: {product_hashid}, 错误: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid product ID")
        
        # 构建查询语句
        stmt = select(Product).where(
            Product.id == product_id,
            Product.tenant_id == tenant.id
        )
        
        # 添加关联查询
        if include_variants:
            stmt = stmt.options(selectinload(Product.variants))
            logger.info("   包含变体信息")
            
        if include_dimensions:
            stmt = stmt.options(selectinload(Product.dimensions))
            logger.info("   包含维度信息")
            
        if include_tags:
            stmt = stmt.options(selectinload(Product.tags).selectinload(ProductTag.tag))
            logger.info("   包含标签信息")
            
        if include_mappings:
            stmt = stmt.options(selectinload(Product.mappings))
            logger.info("   包含映射信息")
        
        # 执行查询
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()
        
        if not product:
            logger.error(f"❌ 商品不存在: product_id={product_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="Product not found")
        
        logger.info(f"✅ 找到商品: {product.title} (ID: {product.id})")
        
        # 单商品详情：加载映射涉及的外部系统类型，用于 external_system_name
        external_system_id_to_type_detail: dict[int, str] = {}
        if include_mappings and getattr(product, "mappings", None):
            es_ids = {m.external_system_id for m in product.mappings if m.external_system_id}
            if es_ids:
                es_result = await db.execute(
                    select(ExternalSystem.id, ExternalSystem.system_type).where(
                        ExternalSystem.id.in_(es_ids)
                    )
                )
                for row in es_result.all():
                    external_system_id_to_type_detail[row.id] = row.system_type.value if row.system_type else "Unknown"
        
        # 构建响应数据
        dimensions = []
        variants = []
        tags = []
        mappings = []
        
        # 构建维度数据
        if include_dimensions and hasattr(product, 'dimensions') and product.dimensions:
            for dimension in product.dimensions:
                dimensions.append(ProductDimensionResponse(
                    id_hashid=encode_id(dimension.id),
                    dimension_name=dimension.dimension_name,
                    dimension_type=dimension.dimension_type,
                    display_name=dimension.display_name,
                    description=dimension.description,
                    options=dimension.options,
                    is_required=dimension.is_required,
                    display_order=dimension.display_order,
                    validation_rules=dimension.validation_rules,
                    is_active=dimension.is_active,
                    created_at=dimension.created_at,
                    updated_at=dimension.updated_at
                ))
        
        # 构建变体数据
        if include_variants and hasattr(product, 'variants') and product.variants:
            for variant in product.variants:
                variants.append(ProductVariantResponse(
                    id_hashid=encode_id(variant.id),
                    sku=variant.sku,
                    barcode=variant.barcode,
                    attributes=variant.attributes,
                    price=variant.price,
                    compare_at_price=variant.compare_at_price,
                    cost_price=variant.cost_price,
                    inventory_quantity=variant.inventory_quantity,
                    inventory_policy=variant.inventory_policy,
                    tracks_inventory=variant.tracks_inventory,
                    is_active=variant.is_active,
                    is_available=variant.is_available,
                    image_url=variant.image_url,
                    weight=variant.weight,
                    dimensions=variant.dimensions,
                    external_variant_id=variant.external_variant_id,
                    created_at=variant.created_at,
                    updated_at=variant.updated_at
                ))
        
        # 构建标签数据
        if include_tags and hasattr(product, 'tags') and product.tags:
            for product_tag in product.tags:
                if product_tag.tag:
                    tags.append(ProductTagResponse(
                        id_hashid=encode_id(product_tag.id),
                        name=product_tag.tag.name,
                        description=product_tag.tag.description,
                        color=product_tag.tag.color,
                        is_primary=product_tag.is_primary,
                        sort_order=product_tag.sort_order,
                        created_at=product_tag.created_at
                    ))
        
        # 构建映射数据（external_system_name 使用真实系统类型）
        if include_mappings and hasattr(product, 'mappings') and product.mappings:
            for mapping in product.mappings:
                ext_name = (
                    external_system_id_to_type_detail.get(mapping.external_system_id)
                    if mapping.external_system_id
                    else "Unknown"
                )
                mappings.append(ProductMappingResponse(
                    id_hashid=encode_id(mapping.id),
                    core_variant_id_hashid=encode_id(mapping.core_variant_id) if mapping.core_variant_id else None,
                    external_system_name=ext_name,
                    external_product_id=mapping.external_product_id,
                    external_variant_id=mapping.external_variant_id,
                    mapping_type=mapping.mapping_type,
                    sync_direction=mapping.sync_direction,
                    sync_status=mapping.sync_status,
                    last_synced_at=mapping.last_synced_at,
                    sync_error=mapping.sync_error,
                    sync_config=mapping.sync_config,
                    field_mappings=mapping.field_mappings,
                    created_at=mapping.created_at,
                    updated_at=mapping.updated_at
                ))
        
        logger.info(f"✅ 构建响应数据完成: 变体={len(variants)}, 维度={len(dimensions)}, 标签={len(tags)}, 映射={len(mappings)}")
        
        return ProductResponse(
            id_hashid=encode_id(product.id),
            title=product.title,
            description=product.description,
            handle=product.handle,
            product_type=product.product_type,
            vendor=product.vendor,
            status=product.status,
            is_active=product.is_active,
            is_available=product.is_available,
            images=product.images,
            seo=product.seo,
            created_at=product.created_at,
            updated_at=product.updated_at,
            dimensions=dimensions,
            variants=variants,
            tags=tags,
            mappings=mappings
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 查询商品详情失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to get product: {str(e)}")


@router.post("/", response_model=ProductResponse)
async def create_product(
    product_data: ProductCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    创建新商品
    
    创建核心系统的商品，支持基本信息和元数据
    """
    tenant, user = auth
    
    try:
        logger.info(f"🔍 开始创建商品: tenant_id={tenant.id}, user_id={user.id}")
        logger.info(f"   商品信息: title={product_data.title}, handle={product_data.handle}")
        
        # 检查handle是否已存在
        if product_data.handle:
            existing_stmt = select(Product).where(
                Product.tenant_id == tenant.id,
                Product.handle == product_data.handle
            )
            existing_result = await db.execute(existing_stmt)
            existing_product = existing_result.scalar_one_or_none()
            
            if existing_product:
                logger.error(f"❌ Handle已存在: {product_data.handle}")
                raise HTTPException(status_code=400, detail="Product handle already exists")
        
        # 创建商品
        product = Product(
            tenant_id=tenant.id,
            title=product_data.title,
            description=product_data.description,
            handle=product_data.handle,
            product_type=product_data.product_type,
            vendor=product_data.vendor,
            status=product_data.status,
            is_active=product_data.is_active,
            is_available=product_data.is_available,
            images=product_data.images,
            seo=product_data.seo
        )
        
        db.add(product)
        await db.flush()  # 获取ID
        
        logger.info(f"✅ 商品创建成功: {product.title} (ID: {product.id})")
        
        # 提交事务
        await db.commit()
        
        return ProductResponse(
            id_hashid=encode_id(product.id),
            title=product.title,
            description=product.description,
            handle=product.handle,
            product_type=product.product_type,
            vendor=product.vendor,
            status=product.status,
            is_active=product.is_active,
            is_available=product.is_available,
            images=product.images,
            seo=product.seo,
            created_at=product.created_at,
            updated_at=product.updated_at,
            dimensions=[],
            variants=[],
            tags=[],
            mappings=[]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 创建商品失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create product: {str(e)}")


@router.put("/{product_hashid}", response_model=ProductResponse)
async def update_product(
    product_hashid: str,
    product_data: ProductUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    更新商品信息
    
    更新核心系统的商品基本信息
    """
    tenant, user = auth
    
    try:
        logger.info(f"🔍 开始更新商品: product_hashid={product_hashid}, tenant_id={tenant.id}, user_id={user.id}")
        
        # 解码hashid
        try:
            product_id = decode_id(product_hashid)
            logger.info(f"✅ Hashid解码成功: {product_hashid} -> {product_id}")
        except Exception as e:
            logger.error(f"❌ Hashid解码失败: {product_hashid}, 错误: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid product ID")
        
        # 查找商品
        stmt = select(Product).where(
            Product.id == product_id,
            Product.tenant_id == tenant.id
        )
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()
    
        if not product:
            logger.error(f"❌ 商品不存在: product_id={product_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="Product not found")
        
        logger.info(f"✅ 找到商品: {product.title} (ID: {product.id})")
        
        # 更新字段
        update_fields = []
        if product_data.title is not None:
            product.title = product_data.title
            update_fields.append("title")
            
        if product_data.description is not None:
            product.description = product_data.description
            update_fields.append("description")
            
        if product_data.handle is not None:
            # 检查新handle是否已存在
            if product_data.handle != product.handle:
                existing_stmt = select(Product).where(
                    Product.tenant_id == tenant.id,
                    Product.handle == product_data.handle,
                    Product.id != product_id
                )
                existing_result = await db.execute(existing_stmt)
                existing_product = existing_result.scalar_one_or_none()
                
                if existing_product:
                    logger.error(f"❌ Handle已存在: {product_data.handle}")
                    raise HTTPException(status_code=400, detail="Product handle already exists")
            
            product.handle = product_data.handle
            update_fields.append("handle")
            
            if product_data.product_type is not None:
                product.product_type = product_data.product_type
                update_fields.append("product_type")
                
            if product_data.vendor is not None:
                product.vendor = product_data.vendor
                update_fields.append("vendor")
                
            if product_data.status is not None:
                product.status = product_data.status
                update_fields.append("status")
                
            if product_data.is_active is not None:
                product.is_active = product_data.is_active
                update_fields.append("is_active")
                
            if product_data.is_available is not None:
                product.is_available = product_data.is_available
                update_fields.append("is_available")
                
            if product_data.images is not None:
                product.images = product_data.images
                update_fields.append("images")
                
            if product_data.seo is not None:
                product.seo = product_data.seo
                update_fields.append("seo")
            
            logger.info(f"✅ 更新字段: {', '.join(update_fields)}")
            
            # 提交事务
            await db.commit()
            
            logger.info(f"✅ 商品更新成功: {product.title} (ID: {product.id})")
            
            return ProductResponse(
                id_hashid=encode_id(product.id),
                title=product.title,
                description=product.description,
                handle=product.handle,
                product_type=product.product_type,
                vendor=product.vendor,
                status=product.status,
                is_active=product.is_active,
                is_available=product.is_available,
                images=product.images,
                seo=product.seo,
                created_at=product.created_at,
                updated_at=product.updated_at,
                dimensions=[],
                variants=[],
                tags=[],
                mappings=[]
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 更新商品失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update product: {str(e)}")


@router.delete("/{product_hashid}")
async def delete_product(
    product_hashid: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    删除商品
    
    软删除商品（设置is_active=False）
    """
    tenant, user = auth
    
    try:
        logger.info(f"🔍 开始删除商品: product_hashid={product_hashid}, tenant_id={tenant.id}, user_id={user.id}")
        
        # 解码hashid
        try:
            product_id = decode_id(product_hashid)
            logger.info(f"✅ Hashid解码成功: {product_hashid} -> {product_id}")
        except Exception as e:
            logger.error(f"❌ Hashid解码失败: {product_hashid}, 错误: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid product ID")
        
        # 查找商品
        stmt = select(Product).where(
            Product.id == product_id,
            Product.tenant_id == tenant.id
        )
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()
        
        if not product:
            logger.error(f"❌ 商品不存在: product_id={product_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="Product not found")
        
        logger.info(f"✅ 找到商品: {product.title} (ID: {product.id})")
        
        # 禁止删除：已映射到外部商品
        mapping_check = await db.execute(
            select(func.count(ProductMapping.id)).where(
                ProductMapping.core_product_id == product_id,
                ProductMapping.tenant_id == tenant.id
            )
        )
        mapping_count = mapping_check.scalar() or 0
        if mapping_count > 0:
            logger.warning(f"⚠️ 商品已映射到外部商品，禁止删除: product_id={product_id}, mapping_count={mapping_count}")
            raise HTTPException(
                status_code=400,
                detail="不能删除：该商品已映射到外部商品，请先解除映射"
            )
        
        # 禁止删除：已有订单
        order_item_check = await db.execute(
            select(func.count(OrderItem.id)).where(
                OrderItem.core_product_id == product_id,
                OrderItem.tenant_id == tenant.id
            )
        )
        order_item_count = order_item_check.scalar() or 0
        if order_item_count > 0:
            logger.warning(f"⚠️ 商品已有订单，禁止删除: product_id={product_id}, order_item_count={order_item_count}")
            raise HTTPException(
                status_code=400,
                detail="不能删除：该商品已有订单记录"
            )
        
        # 硬删除：删除所有相关数据
        logger.info(f"🔍 开始删除商品相关数据...")
        
        # 1. 删除商品映射关系
        mapping_stmt = delete(ProductMapping).where(
            ProductMapping.core_product_id == product_id,
            ProductMapping.tenant_id == tenant.id
        )
        mapping_result = await db.execute(mapping_stmt)
        logger.info(f"✅ 删除映射关系: {mapping_result.rowcount} 条")
        
        # 2. 删除商品变体
        variant_stmt = delete(ProductVariant).where(
            ProductVariant.product_id == product_id,
            ProductVariant.tenant_id == tenant.id
        )
        variant_result = await db.execute(variant_stmt)
        logger.info(f"✅ 删除商品变体: {variant_result.rowcount} 条")
        
        # 3. 删除商品维度
        dimension_stmt = delete(ProductDimension).where(
            ProductDimension.product_id == product_id,
            ProductDimension.tenant_id == tenant.id
        )
        dimension_result = await db.execute(dimension_stmt)
        logger.info(f"✅ 删除商品维度: {dimension_result.rowcount} 条")
        
        # 4. 删除商品标签关联
        tag_stmt = delete(ProductTag).where(
            ProductTag.product_id == product_id,
            ProductTag.tenant_id == tenant.id
        )
        tag_result = await db.execute(tag_stmt)
        logger.info(f"✅ 删除商品标签关联: {tag_result.rowcount} 条")
        
        # 5. 删除商品本身
        product_stmt = delete(Product).where(
            Product.id == product_id,
            Product.tenant_id == tenant.id
        )
        product_result = await db.execute(product_stmt)
        logger.info(f"✅ 删除商品: {product_result.rowcount} 条")
        
        # 提交事务
        await db.commit()
        
        logger.info(f"✅ 商品硬删除成功: {product.title} (ID: {product.id})")
        
        return {"message": "Product deleted successfully", "product_id": product_hashid}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除商品失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete product: {str(e)}")


class BatchDeleteProductsByFilterRequest(BaseModel):
    """按当前筛选条件批量删除核心商品请求（与列表筛选参数一致）"""
    search: Optional[str] = None
    status: Optional[str] = None
    product_type: Optional[str] = None
    vendor: Optional[str] = None


@router.post("/batch-delete-by-filter", response_model=dict)
async def batch_delete_products_by_filter(
    request: BatchDeleteProductsByFilterRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    按当前筛选条件删除所有符合条件的核心商品。
    仅删除无映射、无订单记录的商品；至少需传一个筛选条件。
    """
    from fastapi import status
    tenant, user = auth
    req = request
    has_filter = any([
        bool(req.search and req.search.strip()),
        bool(req.status),
        bool(req.product_type),
        bool(req.vendor),
    ])
    if not has_filter:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请至少选择一个筛选条件（如状态、类型、供应商或搜索关键词），避免误删全部商品",
        )
    conditions = [Product.tenant_id == tenant.id]
    if req.status:
        conditions.append(Product.status == req.status)
    if req.product_type:
        conditions.append(Product.product_type == req.product_type)
    if req.vendor:
        conditions.append(Product.vendor == req.vendor)
    if req.search and req.search.strip():
        conditions.append(Product.title.ilike(f"%{req.search.strip()}%"))
    # 仅可删除：无映射、无订单的商品
    mapping_ids = select(ProductMapping.core_product_id).where(
        ProductMapping.tenant_id == tenant.id
    )
    order_ids = select(OrderItem.core_product_id).where(
        OrderItem.tenant_id == tenant.id
    )
    stmt = (
        select(Product.id)
        .where(*conditions)
        .where(Product.id.not_in(mapping_ids))
        .where(Product.id.not_in(order_ids))
    )
    result = await db.execute(stmt)
    ids_to_delete = [row[0] for row in result.all()]
    deleted = 0
    for product_id in ids_to_delete:
        await db.execute(
            delete(ProductMapping).where(
                ProductMapping.core_product_id == product_id,
                ProductMapping.tenant_id == tenant.id,
            )
        )
        await db.execute(
            delete(ProductVariant).where(
                ProductVariant.product_id == product_id,
                ProductVariant.tenant_id == tenant.id,
            )
        )
        await db.execute(
            delete(ProductDimension).where(
                ProductDimension.product_id == product_id,
                ProductDimension.tenant_id == tenant.id,
            )
        )
        await db.execute(
            delete(ProductTag).where(
                ProductTag.product_id == product_id,
                ProductTag.tenant_id == tenant.id,
            )
        )
        await db.execute(
            delete(Product).where(
                Product.id == product_id,
                Product.tenant_id == tenant.id,
            )
        )
        deleted += 1
    await db.commit()
    logger.info(
        f"✅ 按条件批量删除核心商品: deleted={deleted}, tenant_id={tenant.id}, filters={req.model_dump()}"
    )
    return {
        "deleted": deleted,
        "message": f"已按条件删除 {deleted} 条商品（仅删除无映射、无订单的记录）",
    }


@router.get("/catalog")
async def sync_product_catalog(
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    Sync product catalog from Printify
    """
    tenant, user = auth
    
    # 从数据库获取 Printify external system 的 credentials
    stmt = select(ExternalSystem).where(
        ExternalSystem.tenant_id == tenant.id,
        ExternalSystem.system_type == ExternalSystemType.PRINTIFY,
        ExternalSystem.is_active == True
    )
    result = await db.execute(stmt)
    printify_system = result.scalar_one_or_none()
    
    if not printify_system or not printify_system.credentials.get("api_token"):
        raise HTTPException(status_code=400, detail="Printify API token not configured for this tenant")
    
    printify_service = PrintifyService(printify_system.credentials["api_token"])
    shops = await printify_service.get_shops()
    return {"message": "Product catalog sync initiated", "shops": shops}


@router.post("/sync", response_model=ProductSyncResponse)
async def sync_shopify_products(
    sync_recent_only: bool = True,
    max_products: Optional[int] = 100,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> ProductSyncResponse:
    """
    手动触发Shopify商品同步
    
    Args:
        sync_recent_only: 是否只同步最近的商品（False表示完全重新同步）
        max_products: 最大商品数量（None表示不限制）
    """
    tenant, user = auth
    
    product_service = ShopifyProductService(db)
    
    try:
        result = await product_service.sync_products(
            tenant_id=tenant.id,
            sync_recent_only=sync_recent_only,
            max_products=max_products
        )
        
        return ProductSyncResponse(**result)
        
    except Exception as e:
        return ProductSyncResponse(
            success=False,
            error=str(e),
            products_fetched=0,
            products_saved=0,
            products_updated=0,
            errors=[str(e)]
        )


@router.post("/sync/background")
async def sync_shopify_products_background(
    sync_recent_only: bool = True,
    max_products: Optional[int] = 100,
    background_tasks: BackgroundTasks = None,
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    后台异步同步Shopify商品
    """
    tenant, user = auth
    
    # 启动后台任务
    task = sync_shopify_products_task.delay(
        tenant_id=tenant.id,
        sync_recent_only=sync_recent_only,
        max_products=max_products
    )
    
    return {
        "message": "商品同步任务已启动",
        "task_id": task.id,
        "status": "PENDING"
    }


@router.post("/sync/full")
async def full_sync_shopify_products(
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    完全重新同步所有Shopify商品（不限制数量和时间）
    """
    tenant, user = auth
    
    # 启动后台任务，完全重新同步
    task = sync_shopify_products_task.delay(
        tenant_id=tenant.id,
        sync_recent_only=False,  # 完全重新同步
        max_products=None  # 不限制数量
    )
    
    return {
        "message": "完全重新同步任务已启动",
        "task_id": task.id,
        "status": "PENDING",
        "sync_type": "full_resync"
    }


# External Products API endpoints
@router.post("/external-products/", response_model=dict)
async def create_external_product(
    product_data: dict,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    创建或更新外部商品
    """
    tenant, user = auth
    
    try:
        logger.info("🔍 开始处理外部商品同步请求", 
                   tenant_id=tenant.id, 
                   external_product_id=product_data.get('external_product_id'))
        
        # 检查是否已存在相同的外部商品
        existing_product = await db.execute(
            select(ExternalProduct).where(
                ExternalProduct.tenant_id == tenant.id,
                ExternalProduct.external_system_id == product_data.get('external_system_id'),
                ExternalProduct.external_product_id == product_data.get('external_product_id')
            )
        )
        existing = existing_product.scalar_one_or_none()
        
        if existing:
            # 更新现有商品
            logger.info("🔄 更新现有外部商品", 
                       external_product_id=product_data.get('external_product_id'))
            
            field_mappings = {'product_name': 'title', 'raw_data': 'external_data'}
            allowed_keys = {
                'external_system_id', 'external_product_id', 'external_variant_id',
                'title', 'description', 'handle', 'status', 'is_active', 'is_available',
                'price', 'compare_at_price', 'cost_price', 'inventory_quantity', 'inventory_policy',
                'product_type', 'vendor', 'tags', 'images', 'variants', 'external_data',
                'last_synced_at', 'sync_status', 'sync_error',
            }
            for key, value in product_data.items():
                db_key = field_mappings.get(key, key)
                if db_key in allowed_keys and hasattr(existing, db_key):
                    setattr(existing, db_key, value)
            existing.updated_at = func.now()
            await db.commit()
            await db.refresh(existing)
            
            logger.info("✅ 外部商品更新成功", 
                       external_product_id=product_data.get('external_product_id'),
                       product_id=existing.id)
            
            return {
                "id": encode_id(existing.id),
                "message": "外部商品更新成功",
                "action": "updated"
            }
        else:
            # 创建新商品
            logger.info("🆕 创建新外部商品", 
                       external_product_id=product_data.get('external_product_id'))
            
            # 处理字段映射
            mapped_data = product_data.copy()
            field_mappings = {
                'product_name': 'title',
                'raw_data': 'external_data'
            }
            for frontend_field, db_field in field_mappings.items():
                if frontend_field in mapped_data:
                    mapped_data[db_field] = mapped_data.pop(frontend_field)

            # 只保留 ExternalProduct 模型存在的列，避免传入 published_at 等前端字段导致报错
            allowed_keys = {
                'external_system_id', 'external_product_id', 'external_variant_id',
                'title', 'description', 'handle', 'status', 'is_active', 'is_available',
                'price', 'compare_at_price', 'cost_price', 'inventory_quantity', 'inventory_policy',
                'product_type', 'vendor', 'tags', 'images', 'variants', 'external_data',
                'last_synced_at', 'sync_status', 'sync_error',
            }
            filtered_data = {k: v for k, v in mapped_data.items() if k in allowed_keys}

            external_product = ExternalProduct(
                tenant_id=tenant.id,
                **filtered_data
            )
            
            db.add(external_product)
            await db.commit()
            await db.refresh(external_product)
            
            logger.info("✅ 外部商品创建成功", 
                       external_product_id=product_data.get('external_product_id'),
                       product_id=external_product.id)
            
            return {
                "id": encode_id(external_product.id),
                "message": "外部商品创建成功",
                "action": "created"
            }
            
    except Exception as e:
        logger.error("❌ 外部商品同步失败", 
                    error=str(e), 
                    tenant_id=tenant.id)
        import traceback
        logger.error("   异常堆栈", stack=traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"外部商品同步失败: {str(e)}")


@router.get("/external-products/", response_model=dict)
async def get_external_products(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(10, ge=1, le=200, description="每页记录数（如从外部商品创建弹窗可请求 200）"),
    external_system_id: Optional[str] = Query(None, description="外部系统ID过滤（支持 hashid 或数字 id）"),
    status: Optional[str] = Query(None, description="商品状态过滤"),
    search: Optional[str] = Query(None, description="搜索关键词（匹配标题、handle、供应商）"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    获取外部商品列表。external_system_id 可为 hashid（前端常用）或数字 id。
    search 对 title、handle、vendor 做模糊匹配。
    """
    tenant, user = auth

    # 将 external_system_id 统一解码为数字 id（支持 hashid）
    external_system_id_int: Optional[int] = None
    if external_system_id:
        try:
            external_system_id_int = decode_id(external_system_id)
        except Exception:
            try:
                external_system_id_int = int(external_system_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid external_system_id")
    
    try:
        logger.info("🔍 获取外部商品列表", 
                   tenant_id=tenant.id, 
                   user_id=user.id,
                   skip=skip, 
                   limit=limit,
                   search=search)
        
        # 构建查询条件
        query = select(ExternalProduct).where(ExternalProduct.tenant_id == tenant.id)
        count_query = select(func.count(ExternalProduct.id)).where(ExternalProduct.tenant_id == tenant.id)
        
        if external_system_id_int is not None:
            query = query.where(ExternalProduct.external_system_id == external_system_id_int)
            count_query = count_query.where(ExternalProduct.external_system_id == external_system_id_int)
        
        if status:
            query = query.where(ExternalProduct.status == status)
            count_query = count_query.where(ExternalProduct.status == status)
        
        if search and search.strip():
            search_term = f"%{search.strip()}%"
            search_condition = or_(
                ExternalProduct.title.ilike(search_term),
                ExternalProduct.handle.ilike(search_term),
                ExternalProduct.vendor.ilike(search_term),
            )
            query = query.where(search_condition)
            count_query = count_query.where(search_condition)
            logger.info(f"   添加外部商品搜索: {search.strip()!r}")
        
        # Printify：仅展示已发布商品 = visible 非 false 且已发布到销售渠道（sales_channel_properties 非空）
        # 使用 Text 做 cast 避免方言差异；对 NULL external_data 已用 is_(None) 排除
        _visible_text = ExternalProduct.external_data.op("->>")("visible")
        _scp = ExternalProduct.external_data.op("->")("sales_channel_properties")
        _visible_ok = or_(
            ExternalProduct.external_data.is_(None),
            _visible_text.is_(None),
            _visible_text != "false",
        )
        _scp_not_empty = and_(
            _scp.isnot(None),
            cast(_scp, Text).notin_(["[]", "{}"]),
        )
        _printify_published = and_(
            ExternalProduct.external_data.isnot(None),
            _visible_ok,
            _scp_not_empty,
        )
        query = query.join(
            ExternalSystem, ExternalProduct.external_system_id == ExternalSystem.id
        ).where(
            or_(
                ExternalSystem.system_type != ExternalSystemType.PRINTIFY,
                _printify_published,
            )
        )
        count_query = count_query.join(
            ExternalSystem, ExternalProduct.external_system_id == ExternalSystem.id
        ).where(
            or_(
                ExternalSystem.system_type != ExternalSystemType.PRINTIFY,
                _printify_published,
            )
        )
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # 获取分页数据
        query = query.offset(skip).limit(limit).order_by(ExternalProduct.updated_at.desc())
        result = await db.execute(query)
        products = result.scalars().all()
        
        # 获取所有外部系统信息
        external_systems = {}
        if products:
            system_ids = list(set(p.external_system_id for p in products if p.external_system_id))
            if system_ids:
                systems_query = select(ExternalSystem).where(ExternalSystem.id.in_(system_ids))
                systems_result = await db.execute(systems_query)
                systems = systems_result.scalars().all()
                for system in systems:
                    external_systems[system.id] = system

        # 批量查询：每个外部商品在 product_mappings 中的映射（用于列表「已映射/未映射」）
        mappings_by_key = {}  # (external_system_id, external_product_id) -> [{"id": encoded_id}, ...]
        if products:
            keys = set((p.external_system_id, p.external_product_id) for p in products if p.external_system_id and p.external_product_id)
            if keys:
                conds = [and_(
                    ProductMapping.external_system_id == es_id,
                    ProductMapping.external_product_id == ep_id,
                ) for (es_id, ep_id) in keys]
                if hasattr(ProductMapping, "is_deleted"):
                    q = select(ProductMapping).where(
                        ProductMapping.tenant_id == tenant.id,
                        or_(*conds),
                        or_(ProductMapping.is_deleted.is_(None), ProductMapping.is_deleted == False),
                    )
                else:
                    q = select(ProductMapping).where(ProductMapping.tenant_id == tenant.id, or_(*conds))
                mapping_result = await db.execute(q)
                mapping_rows = mapping_result.scalars().all()
                for m in mapping_rows:
                    k = (m.external_system_id, m.external_product_id)
                    if k not in mappings_by_key:
                        mappings_by_key[k] = []
                    mappings_by_key[k].append({"id": encode_id(m.id)})
        
        # 转换为响应格式
        product_list = []
        for product in products:
            # 获取外部系统信息
            external_system_name = "Unknown"
            shop_name = "Unknown"
            
            logger.info(f"🔍 处理外部商品: {product.title}, external_system_id={product.external_system_id}")
            
            if product.external_system_id in external_systems:
                system = external_systems[product.external_system_id]
                external_system_name = system.system_type.value
                # 列表显示真实店铺名：优先用 ExternalSystem.name（如 Impeach Printify Store）
                shop_name = (getattr(system, "name", None) or "").strip() or "Unknown"
                logger.info(f"   外部系统类型: {external_system_name}, 店铺名称: {shop_name}")
            else:
                logger.warning(f"   ⚠️ 外部系统未找到: external_system_id={product.external_system_id}")
            
            mapping_list = mappings_by_key.get(
                (product.external_system_id, product.external_product_id), []
            )
            product_list.append({
                "id": encode_id(product.id),
                "external_system_id": product.external_system_id,
                "external_system_name": external_system_name,
                "shop_name": shop_name,
                "external_product_id": product.external_product_id,
                "external_variant_id": product.external_variant_id,
                "title": product.title,
                "description": product.description,
                "handle": product.handle,
                "product_type": product.product_type,
                "vendor": product.vendor,
                "status": product.status,
                "is_active": product.is_active,
                "is_available": product.is_available,
                "price": float(product.price) if product.price else None,
                "compare_at_price": float(product.compare_at_price) if product.compare_at_price else None,
                "cost_price": float(product.cost_price) if product.cost_price else None,
                "inventory_quantity": product.inventory_quantity,
                "inventory_policy": product.inventory_policy,
                "tags": product.tags,
                "images": product.images,
                "variants": product.variants,
                "external_data": product.external_data,
                "sync_status": product.sync_status,
                "sync_error": product.sync_error,
                "last_synced_at": product.last_synced_at,
                "created_at": product.created_at,
                "updated_at": product.updated_at,
                "mappings": mapping_list,
            })
        
        logger.info("✅ 外部商品列表获取成功", 
                   tenant_id=tenant.id, 
                   total=total, 
                   count=len(product_list))
        
        return {
            "products": product_list,
            "total": total,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error("❌ 获取外部商品列表失败", 
                    error=str(e), 
                    tenant_id=tenant.id)
        import traceback
        logger.error("   异常堆栈", stack=traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"获取外部商品列表失败: {str(e)}")


# 从外部商品创建核心商品的API端点
@router.post("/create-from-external", response_model=ProductResponse)
async def create_product_from_external(
    request_data: dict,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    从外部商品创建核心商品
    
    基于外部商品数据创建核心系统的商品，并建立映射关系
    """
    tenant, user = auth
    
    try:
        # 从请求体中获取external_product_id
        external_product_id = request_data.get('external_product_id')
        if not external_product_id:
            logger.error("❌ 缺少external_product_id参数")
            raise HTTPException(status_code=400, detail="Missing external_product_id")
        
        logger.info(f"🔍 开始从外部商品创建核心商品: external_product_id={external_product_id}, tenant_id={tenant.id}, user_id={user.id}")
        
        # 解码外部商品ID
        try:
            external_product_id_decoded = decode_id(external_product_id)
            logger.info(f"✅ 外部商品ID解码成功: {external_product_id} -> {external_product_id_decoded}")
        except Exception as e:
            logger.error(f"❌ 外部商品ID解码失败: {external_product_id}, 错误: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid external product ID")
        
        # 查询外部商品
        external_product_stmt = select(ExternalProduct).where(
            ExternalProduct.id == external_product_id_decoded,
            ExternalProduct.tenant_id == tenant.id
        )
        external_product_result = await db.execute(external_product_stmt)
        external_product = external_product_result.scalar_one_or_none()
        
        if not external_product:
            logger.error(f"❌ 外部商品不存在: external_product_id={external_product_id_decoded}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="External product not found")
        
        logger.info(f"✅ 找到外部商品: {external_product.title} (ID: {external_product.id})")
        
        # 检查是否已经存在映射的核心商品
        existing_mapping_stmt = select(ProductMapping).where(
            ProductMapping.tenant_id == tenant.id,
            ProductMapping.external_system_id == external_product.external_system_id,
            ProductMapping.external_product_id == external_product.external_product_id,
            ProductMapping.mapping_type == "product"
        )
        existing_mapping_result = await db.execute(existing_mapping_stmt)
        existing_mapping = existing_mapping_result.scalar_one_or_none()
        
        if existing_mapping:
            logger.warning(f"⚠️ 外部商品已存在映射: external_product_id={external_product.external_product_id}")
            logger.info(f"🔄 开始更新现有商品和变体...")
            
            # 获取现有的核心商品
            core_product = await db.get(Product, existing_mapping.core_product_id)
            if not core_product:
                raise HTTPException(status_code=404, detail="Core product not found")
            
                # 检查是否需要同步变体
                variant_list = _normalize_variant_list(external_product.variants)
                if variant_list:
                    logger.info(f"🔍 开始同步变体数据: 发现 {len(variant_list)} 个变体")

                    # 获取现有的变体映射
                    existing_variant_mappings = await db.execute(
                        select(ProductMapping).where(
                            ProductMapping.core_product_id == core_product.id,
                            ProductMapping.mapping_type == "variant",
                            ProductMapping.tenant_id == tenant.id
                        )
                    )
                    existing_variant_mappings = existing_variant_mappings.scalars().all()
                    existing_variant_ids = {m.external_variant_id for m in existing_variant_mappings}

                    for variant_data in variant_list:
                        external_variant_id = variant_data.get("id") or variant_data.get("external_variant_id")
                        if external_variant_id in existing_variant_ids:
                            logger.info(f"ℹ️ 变体已存在，跳过: {variant_data.get('sku')}")
                            continue

                        sku = _get_variant_sku(variant_data, external_product.external_product_id)
                        try:
                            core_variant = ProductVariant(
                                tenant_id=tenant.id,
                                product_id=core_product.id,
                                sku=sku,
                                barcode=variant_data.get("barcode"),
                                attributes=_extract_variant_attributes(variant_data),
                                price=variant_data.get("price"),
                                compare_at_price=variant_data.get("compare_at_price") or variant_data.get("compareAtPrice"),
                                cost_price=variant_data.get("cost_price"),
                                inventory_quantity=variant_data.get("inventory_quantity") or variant_data.get("inventoryQuantity", 0),
                                inventory_policy=variant_data.get("inventory_policy") or variant_data.get("inventoryPolicy", "DENY"),
                                tracks_inventory=True,
                                is_active=True,
                                is_available=(variant_data.get("inventory_quantity") or variant_data.get("inventoryQuantity", 0)) > 0,
                                weight=variant_data.get("weight", 0),
                                external_variant_id=external_variant_id,
                            )
                            db.add(core_variant)
                            await db.flush()

                            variant_mapping = ProductMapping(
                                tenant_id=tenant.id,
                                core_product_id=core_product.id,
                                core_variant_id=core_variant.id,
                                external_system_id=external_product.external_system_id,
                                external_product_id=external_product.external_product_id,
                                external_variant_id=external_variant_id,
                                mapping_type="variant",
                                sync_direction="bidirectional",
                                sync_status="active",
                            )
                            db.add(variant_mapping)
                            logger.info(f"✅ 新变体创建成功: SKU={core_variant.sku}, 外部变体ID={external_variant_id}")
                        except Exception as e:
                            logger.error(f"❌ 创建变体失败: {variant_data.get('sku')}, 错误: {str(e)}")
                            await db.rollback()
                            raise HTTPException(status_code=400, detail=f"创建变体失败（如 SKU 重复）: {str(e)}")
            
            await db.commit()
            await db.refresh(core_product)
            
            # 重新查询变体和映射关系
            variants_result = await db.execute(
                select(ProductVariant).where(
                    ProductVariant.product_id == core_product.id,
                    ProductVariant.tenant_id == tenant.id
                )
            )
            variants = variants_result.scalars().all()
            
            mappings_result = await db.execute(
                select(ProductMapping).where(
                    ProductMapping.core_product_id == core_product.id,
                    ProductMapping.tenant_id == tenant.id
                )
            )
            mappings = mappings_result.scalars().all()
            
            # 构建变体响应
            variant_responses = []
            for variant in variants:
                variant_responses.append(ProductVariantResponse(
                    id_hashid=encode_id(variant.id),
                    sku=variant.sku,
                    barcode=variant.barcode,
                    attributes=variant.attributes,
                    price=variant.price,
                    compare_at_price=variant.compare_at_price,
                    cost_price=variant.cost_price,
                    inventory_quantity=variant.inventory_quantity,
                    inventory_policy=variant.inventory_policy,
                    tracks_inventory=variant.tracks_inventory,
                    is_active=variant.is_active,
                    is_available=variant.is_available,
                    image_url=variant.image_url,
                    weight=variant.weight,
                    external_variant_id=variant.external_variant_id,
                    created_at=variant.created_at,
                    updated_at=variant.updated_at
                ))
            
            # 构建映射响应
            mapping_responses = []
            for mapping in mappings:
                # 获取外部系统名称 - 避免懒加载问题
                external_system_name = "Unknown"
                if mapping.external_system_id:
                    # 直接通过ID查询，避免访问关系属性
                    external_system = await db.get(ExternalSystem, mapping.external_system_id)
                    if external_system:
                        external_system_name = external_system.name
                
                mapping_responses.append(ProductMappingResponse(
                    id_hashid=encode_id(mapping.id),
                    external_system_name=external_system_name,
                    external_product_id=mapping.external_product_id,
                    external_variant_id=mapping.external_variant_id,
                    mapping_type=mapping.mapping_type,
                    sync_direction=mapping.sync_direction,
                    sync_status=mapping.sync_status,
                    last_synced_at=mapping.last_synced_at
                ))
            
            return ProductResponse(
                id_hashid=encode_id(core_product.id),
                title=core_product.title,
                description=core_product.description,
                handle=core_product.handle,
                product_type=core_product.product_type,
                vendor=core_product.vendor,
                status=core_product.status,
                is_active=core_product.is_active,
                is_available=core_product.is_available,
                images=core_product.images,
                seo=core_product.seo,
                variants=variant_responses,
                mappings=mapping_responses,
                created_at=core_product.created_at,
                updated_at=core_product.updated_at
            )
        
        # 创建核心商品
        core_product = Product(
            tenant_id=tenant.id,
            title=external_product.title,
            description=external_product.description,
            handle=external_product.handle,
            product_type=external_product.product_type,
            vendor=external_product.vendor,
            status=external_product.status,
            is_active=external_product.is_active,
            is_available=external_product.is_available,
            images=external_product.images,
            seo=external_product.external_data.get("seo") if external_product.external_data else None
        )
        
        db.add(core_product)
        await db.flush()  # 获取ID
        
        logger.info(f"✅ 核心商品创建成功: {core_product.title} (ID: {core_product.id})")
        
        # 创建映射关系
        product_mapping = ProductMapping(
            tenant_id=tenant.id,
            core_product_id=core_product.id,
            external_system_id=external_product.external_system_id,
            external_product_id=external_product.external_product_id,
            mapping_type="product",
            sync_direction="bidirectional",
            sync_status="active"
        )
        
        db.add(product_mapping)
        await db.flush()
        
        logger.info(f"✅ 映射关系创建成功: core_product_id={core_product.id}, external_product_id={external_product.external_product_id}")
        
        # 处理外部商品的变体数据
        variant_list = _normalize_variant_list(external_product.variants)
        if variant_list:
            logger.info(f"🔍 开始同步变体数据: 发现 {len(variant_list)} 个变体")

            for variant_data in variant_list:
                external_variant_id = variant_data.get("id") or variant_data.get("external_variant_id")
                sku = _get_variant_sku(variant_data, external_product.external_product_id)
                try:
                    core_variant = ProductVariant(
                        tenant_id=tenant.id,
                        product_id=core_product.id,
                        sku=sku,
                        barcode=variant_data.get("barcode"),
                        attributes=_extract_variant_attributes(variant_data),
                        price=variant_data.get("price"),
                        compare_at_price=variant_data.get("compare_at_price") or variant_data.get("compareAtPrice"),
                        cost_price=variant_data.get("cost_price"),
                        inventory_quantity=variant_data.get("inventory_quantity") or variant_data.get("inventoryQuantity", 0),
                        inventory_policy=variant_data.get("inventory_policy") or variant_data.get("inventoryPolicy", "DENY"),
                        tracks_inventory=True,
                        is_active=True,
                        is_available=(variant_data.get("inventory_quantity") or variant_data.get("inventoryQuantity", 0)) > 0,
                        weight=variant_data.get("weight", 0),
                        external_variant_id=external_variant_id,
                    )
                    db.add(core_variant)
                    await db.flush()

                    variant_mapping = ProductMapping(
                        tenant_id=tenant.id,
                        core_product_id=core_product.id,
                        core_variant_id=core_variant.id,
                        external_system_id=external_product.external_system_id,
                        external_product_id=external_product.external_product_id,
                        external_variant_id=external_variant_id,
                        mapping_type="variant",
                        sync_direction="bidirectional",
                        sync_status="active",
                    )
                    db.add(variant_mapping)
                    logger.info(f"✅ 变体创建成功: SKU={core_variant.sku}, 外部变体ID={external_variant_id}")
                except Exception as e:
                    logger.error(f"❌ 创建变体失败: {variant_data.get('sku')}, 错误: {str(e)}")
                    await db.rollback()
                    raise HTTPException(status_code=400, detail=f"创建变体失败（如 SKU 重复）: {str(e)}")
        
        # 提交事务
        await db.commit()
        
        logger.info(f"✅ 从外部商品创建核心商品完成: {core_product.title}")
        
        # 重新查询商品以获取完整的变体和映射数据
        await db.refresh(core_product)
        
        # 查询变体数据
        variants_stmt = select(ProductVariant).where(
            ProductVariant.product_id == core_product.id,
            ProductVariant.tenant_id == tenant.id
        )
        variants_result = await db.execute(variants_stmt)
        variants = variants_result.scalars().all()
        
        # 查询映射数据
        mappings_stmt = select(ProductMapping).where(
            ProductMapping.core_product_id == core_product.id,
            ProductMapping.tenant_id == tenant.id
        )
        mappings_result = await db.execute(mappings_stmt)
        mappings = mappings_result.scalars().all()
        
        # 构建变体响应
        variant_responses = []
        for variant in variants:
            variant_responses.append(ProductVariantResponse(
                id_hashid=encode_id(variant.id),
                sku=variant.sku,
                barcode=variant.barcode,
                attributes=variant.attributes,
                price=variant.price,
                compare_at_price=variant.compare_at_price,
                cost_price=variant.cost_price,
                inventory_quantity=variant.inventory_quantity,
                inventory_policy=variant.inventory_policy,
                tracks_inventory=variant.tracks_inventory,
                is_active=variant.is_active,
                is_available=variant.is_available,
                weight=variant.weight,
                external_variant_id=variant.external_variant_id,
                created_at=variant.created_at,
                updated_at=variant.updated_at
            ))
        
        # 构建映射响应
        mapping_responses = []
        for mapping in mappings:
            # 获取外部系统名称 - 避免懒加载问题
            external_system_name = "Unknown"
            if mapping.external_system_id:
                # 直接通过ID查询，避免访问关系属性
                external_system = await db.get(ExternalSystem, mapping.external_system_id)
                if external_system:
                    external_system_name = external_system.name
            
            mapping_responses.append(ProductMappingResponse(
                id_hashid=encode_id(mapping.id),
                external_system_name=external_system_name,
                external_product_id=mapping.external_product_id,
                external_variant_id=mapping.external_variant_id,
                mapping_type=mapping.mapping_type,
                sync_direction=mapping.sync_direction,
                sync_status=mapping.sync_status,
                last_synced_at=mapping.last_synced_at
            ))
        
        return ProductResponse(
            id_hashid=encode_id(core_product.id),
            title=core_product.title,
            description=core_product.description,
            handle=core_product.handle,
            product_type=core_product.product_type,
            vendor=core_product.vendor,
            status=core_product.status,
            is_active=core_product.is_active,
            is_available=core_product.is_available,
            images=core_product.images,
            seo=core_product.seo,
            created_at=core_product.created_at,
            updated_at=core_product.updated_at,
            dimensions=[],
            variants=variant_responses,
            tags=[],
            mappings=mapping_responses
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 从外部商品创建核心商品失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create product from external: {str(e)}")

def _normalize_variant_list(variants: Any) -> list:
    """
    将外部变体数据归一化为变体字典列表。
    支持 GraphQL edges/node 格式和已平铺的列表格式。
    """
    if not variants:
        return []
    if isinstance(variants, dict) and "edges" in variants:
        return [e.get("node", e) for e in variants.get("edges", [])]
    if isinstance(variants, list):
        return [v.get("node", v) if isinstance(v, dict) else v for v in variants]
    return []


def _get_variant_sku(variant_data: dict, external_product_id: str = "") -> Optional[str]:
    """
    获取变体 SKU，空时用 external_variant_id 占位，避免 (tenant_id, '') 唯一约束冲突。
    """
    raw = (variant_data.get("sku") or "").strip()
    if raw:
        return raw
    vid = variant_data.get("id") or variant_data.get("external_variant_id") or ""
    if vid:
        vid = str(vid).replace("gid://shopify/ProductVariant/", "").strip()
    pid = (external_product_id or "").replace("gid://shopify/Product/", "").strip()
    if vid:
        return f"VAR-{pid}-{vid}" if pid else vid
    return None


def _extract_variant_attributes(variant_data: dict) -> dict:
    """
    从外部变体数据中提取「规格维度」属性，且仅以来源平台的商品定义为准。

    - Shopify：维度来自商品的 options（如 Color, Size），在 API 中体现为
      variant.selectedOptions / selected_options，每项为 { name, value }，
      name 即商品选项名（product option name），value 即该变体的取值。
      variant 的 title 字段是展示用组合字符串（如 "S / White"），不是选项名，
      因此绝不写入 attributes，否则会与 Printify 的 Color/Size 等真实维度不一致。
    - 其他平台：同样只使用其「选项/维度」结构，不写入展示用 title。
    """
    attributes = {}

    # 仅使用平台定义的选项：Shopify 为 selected_options / selectedOptions（name = 选项名，value = 取值）
    opts = variant_data.get("selected_options") or variant_data.get("selectedOptions") or []
    for option in opts:
        if isinstance(option, dict) and option.get("name") is not None and option.get("value") is not None:
            attributes[option["name"]] = option["value"]

    # 禁止把 variant.title（展示用）写入 attributes，维度以商品定义为准
    return attributes


# 商品映射相关API端点
class ProductMappingCreateRequest(BaseModel):
    """创建商品映射的请求"""
    core_product_id_hashid: str
    core_variant_id_hashid: Optional[str] = None
    external_system_id_hashid: str
    external_product_id: str
    external_variant_id: Optional[str] = None
    mapping_type: str = "manual"
    sync_direction: str = "bidirectional"
    sync_status: str = "active"


@router.post("/mappings/", response_model=ProductMappingResponse)
async def create_product_mapping(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    创建商品映射关系
    """
    tenant, user = auth
    
    try:
        # 手动解析请求体
        body = await request.body()
        logger.info("📦 接收到的原始请求体", body=body.decode('utf-8'))
        
        try:
            import json
            request_data = json.loads(body)
            logger.info("📦 解析后的请求数据", request_data=request_data)
        except Exception as e:
            logger.error(f"❌ 解析请求体失败: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid JSON in request body")
        
        # 手动验证数据
        try:
            mapping_data = ProductMappingCreateRequest(**request_data)
            logger.info("✅ Pydantic 验证成功")
        except Exception as e:
            logger.error(f"❌ Pydantic 验证失败: {str(e)}")
            logger.error(f"   请求数据: {request_data}")
            raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
        
        logger.info("🔍 开始创建商品映射", 
                   core_product_id=mapping_data.core_product_id_hashid,
                   core_variant_id=mapping_data.core_variant_id_hashid,
                   external_system_id=mapping_data.external_system_id_hashid,
                   external_product_id=mapping_data.external_product_id,
                   external_variant_id=mapping_data.external_variant_id,
                   tenant_id=tenant.id)
        
        # 解码核心商品ID
        try:
            core_product_id = decode_id(mapping_data.core_product_id_hashid)
            logger.info(f"✅ 核心商品ID解码成功: {mapping_data.core_product_id_hashid} -> {core_product_id}")
        except Exception as e:
            logger.error(f"❌ 核心商品ID解码失败: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid core product ID")
        
        # 解码核心变体ID（如果提供）
        core_variant_id = None
        if mapping_data.core_variant_id_hashid:
            try:
                core_variant_id = decode_id(mapping_data.core_variant_id_hashid)
                logger.info(f"✅ 核心变体ID解码成功: {mapping_data.core_variant_id_hashid} -> {core_variant_id}")
            except Exception as e:
                logger.error(f"❌ 核心变体ID解码失败: {str(e)}")
                raise HTTPException(status_code=400, detail="Invalid core variant ID")
        
        # 解码外部系统ID
        try:
            external_system_id = decode_id(mapping_data.external_system_id_hashid)
            logger.info(f"外部系统ID解码成功: {mapping_data.external_system_id_hashid} -> {external_system_id}")
        except Exception as e:
            logger.error(f"外部系统ID解码失败: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid external system ID")
        
        # 验证核心商品是否存在
        core_product_stmt = select(Product).where(
            Product.id == core_product_id,
            Product.tenant_id == tenant.id
        )
        core_product_result = await db.execute(core_product_stmt)
        core_product = core_product_result.scalar_one_or_none()
        
        if not core_product:
            logger.error(f"❌ 核心商品不存在: core_product_id={core_product_id}")
            raise HTTPException(status_code=404, detail="Core product not found")
        
        logger.info(f"✅ 找到核心商品: {core_product.title}")
        
        # 验证核心变体是否存在（如果提供）
        if core_variant_id:
            logger.info(f"🔍 查找核心变体: core_variant_id={core_variant_id}, product_id={core_product_id}")
            core_variant_stmt = select(ProductVariant).where(
                ProductVariant.id == core_variant_id,
                ProductVariant.product_id == core_product_id,
                ProductVariant.tenant_id == tenant.id
            )
            core_variant_result = await db.execute(core_variant_stmt)
            core_variant = core_variant_result.scalar_one_or_none()
            
            if not core_variant:
                logger.error(f"❌ 核心变体不存在: core_variant_id={core_variant_id}, product_id={core_product_id}")
                # 查询该商品的所有变体
                all_variants_stmt = select(ProductVariant).where(
                    ProductVariant.product_id == core_product_id,
                    ProductVariant.tenant_id == tenant.id
                )
                all_variants_result = await db.execute(all_variants_stmt)
                all_variants = all_variants_result.scalars().all()
                logger.error(f"❌ 该商品的所有变体: {[v.id for v in all_variants]}")
                raise HTTPException(status_code=404, detail="Core variant not found")
            
            logger.info(f"✅ 找到核心变体: {core_variant.sku}")
        
        # 验证外部系统是否存在
        external_system_stmt = select(ExternalSystem).where(
            ExternalSystem.id == external_system_id,
            ExternalSystem.tenant_id == tenant.id
        )
        external_system_result = await db.execute(external_system_stmt)
        external_system = external_system_result.scalar_one_or_none()
        
        if not external_system:
            logger.error(f"❌ 外部系统不存在: external_system_id={external_system_id}")
            raise HTTPException(status_code=404, detail="External system not found")
        
        logger.info(f"✅ 找到外部系统: {external_system.name}")
        
        # 检查是否已存在相同的映射（基于新的唯一约束）
        existing_mapping_stmt = select(ProductMapping).where(
            ProductMapping.tenant_id == tenant.id,
            ProductMapping.core_product_id == core_product_id,
            ProductMapping.core_variant_id == core_variant_id,
            ProductMapping.external_system_id == external_system_id
        )
        existing_mapping_result = await db.execute(existing_mapping_stmt)
        existing_mapping = existing_mapping_result.scalar_one_or_none()
        
        if existing_mapping:
            logger.warning(f"⚠️ 映射已存在，将更新现有映射: mapping_id={existing_mapping.id}")
            
            # 更新现有映射
            existing_mapping.external_product_id = mapping_data.external_product_id
            existing_mapping.external_variant_id = mapping_data.external_variant_id
            existing_mapping.mapping_type = mapping_data.mapping_type
            existing_mapping.sync_direction = mapping_data.sync_direction
            existing_mapping.sync_status = mapping_data.sync_status
            existing_mapping.sync_config = {"manual_mapping": True}
            existing_mapping.field_mappings = {
                "title": "title",
                "sku": "sku",
                "price": "price"
            }
            
            await db.commit()
            await db.refresh(existing_mapping)
            
            logger.info(f"✅ 商品映射更新成功: mapping_id={existing_mapping.id}")
            product_mapping = existing_mapping
        else:
            # 创建新的映射
            product_mapping = ProductMapping(
                tenant_id=tenant.id,
                core_product_id=core_product_id,
                core_variant_id=core_variant_id,
                external_system_id=external_system_id,
                external_product_id=mapping_data.external_product_id,
                external_variant_id=mapping_data.external_variant_id,
                mapping_type=mapping_data.mapping_type,
                sync_direction=mapping_data.sync_direction,
                sync_status=mapping_data.sync_status,
                sync_config={"manual_mapping": True},
                field_mappings={
                    "title": "title",
                    "sku": "sku",
                    "price": "price"
                }
            )
            
            db.add(product_mapping)
            await db.commit()
            await db.refresh(product_mapping)
            
            logger.info(f"✅ 商品映射创建成功: mapping_id={product_mapping.id}")
        
        # 构建响应
        return ProductMappingResponse(
            id_hashid=encode_id(product_mapping.id),
            external_system_name=external_system.name,
            external_product_id=product_mapping.external_product_id,
            external_variant_id=product_mapping.external_variant_id,
            mapping_type=product_mapping.mapping_type,
            sync_direction=product_mapping.sync_direction,
            sync_status=product_mapping.sync_status,
            last_synced_at=product_mapping.last_synced_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 创建商品映射失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create product mapping: {str(e)}")


class AutoBindPrintifyByShopifyResponse(BaseModel):
    """按 Printify raw_data.external.id 与 Shopify 映射自动绑定：预览或执行结果"""
    dry_run: bool
    candidates: List[dict]  # [{ "core_product_id", "core_title", "printify_product_id", "printify_title", "shopify_product_id" }]
    created_count: int = 0
    skipped_already_mapped: int = 0
    error: Optional[str] = None


@router.post("/mappings/auto-bind-printify-by-shopify", response_model=AutoBindPrintifyByShopifyResponse)
async def auto_bind_printify_by_shopify(
    dry_run: bool = Query(True, description="True=仅预览不写入，False=执行创建"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    根据 Printify 商品 raw_data.external.id（= Shopify product id）与核心商品已有的 Shopify 映射，
    自动为「有 Shopify 映射、无 Printify 映射」的核心商品创建与 Printify 的商品级映射（仅商品级，变体依赖 SKU/options 回退）。
    详见: docs/integrations/printify/printify-shopify-binding-from-api.md
    同一逻辑已接入「自动化管理」商品同步步骤，可定时或手动触发。
    """
    from app.services.printify_shopify_binding_service import auto_bind_printify_by_shopify as run_auto_bind

    tenant, user = auth
    try:
        result = await run_auto_bind(db, tenant.id, dry_run=dry_run)
        return AutoBindPrintifyByShopifyResponse(
            dry_run=result.get("dry_run", dry_run),
            candidates=result.get("candidates", []),
            created_count=result.get("created_count", 0),
            skipped_already_mapped=result.get("skipped_already_mapped", 0),
            error=result.get("error"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ auto_bind_printify_by_shopify 失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        await db.rollback()
        return AutoBindPrintifyByShopifyResponse(
            dry_run=dry_run,
            candidates=[],
            created_count=0,
            error=str(e),
        )


@router.get("/mappings/", response_model=dict)
async def get_product_mappings(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(50, ge=1, le=100, description="每页数量"),
    core_product_id: Optional[int] = Query(None, description="核心商品ID"),
    core_product_title: Optional[str] = Query(None, description="核心商品标题模糊搜索"),
    external_system_id: Optional[int] = Query(None, description="外部系统ID"),
    external_product_ids: Optional[str] = Query(
        None, description="外部商品ID列表，逗号分隔（用于按外部商品批量过滤映射）"
    ),
    sync_status: Optional[str] = Query(None, description="同步状态"),
    mapping_type: Optional[str] = Query(None, description="映射类型"),
    system_type: Optional[str] = Query(None, description="外部系统类型，如 SHOPIFY/PRINTIFY"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    获取商品映射列表。支持按核心商品、外部系统类型等筛选，便于只查 Shopify 映射等。
    """
    tenant, user = auth
    
    try:
        logger.info("🔍 开始获取商品映射列表",
                   page=page, limit=limit, tenant_id=tenant.id,
                   system_type=system_type, core_product_title=bool(core_product_title))
        
        # 构建基础条件（与 count 和 list 共用）
        base = select(ProductMapping).where(ProductMapping.tenant_id == tenant.id)
        count_stmt = select(func.count(ProductMapping.id)).where(ProductMapping.tenant_id == tenant.id)

        if core_product_id:
            base = base.where(ProductMapping.core_product_id == core_product_id)
            count_stmt = count_stmt.where(ProductMapping.core_product_id == core_product_id)
        if core_product_title and core_product_title.strip():
            term = f"%{core_product_title.strip()}%"
            base = base.join(Product, ProductMapping.core_product_id == Product.id).where(
                Product.tenant_id == tenant.id,
                Product.title.ilike(term)
            )
            count_stmt = count_stmt.join(Product, ProductMapping.core_product_id == Product.id).where(
                Product.tenant_id == tenant.id,
                Product.title.ilike(term)
            )
        if external_system_id:
            base = base.where(ProductMapping.external_system_id == external_system_id)
            count_stmt = count_stmt.where(ProductMapping.external_system_id == external_system_id)
        if external_product_ids and external_product_ids.strip():
            external_product_id_list = [
                pid.strip() for pid in external_product_ids.split(",") if pid.strip()
            ]
            if external_product_id_list:
                base = base.where(ProductMapping.external_product_id.in_(external_product_id_list))
                count_stmt = count_stmt.where(
                    ProductMapping.external_product_id.in_(external_product_id_list)
                )
        if sync_status:
            base = base.where(ProductMapping.sync_status == sync_status)
            count_stmt = count_stmt.where(ProductMapping.sync_status == sync_status)
        if mapping_type:
            base = base.where(ProductMapping.mapping_type == mapping_type)
            count_stmt = count_stmt.where(ProductMapping.mapping_type == mapping_type)
        if system_type:
            base = base.join(ExternalSystem, ProductMapping.external_system_id == ExternalSystem.id)
            base = base.where(ExternalSystem.system_type == system_type)
            count_stmt = count_stmt.join(ExternalSystem, ProductMapping.external_system_id == ExternalSystem.id)
            count_stmt = count_stmt.where(ExternalSystem.system_type == system_type)
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0
        
        # 分页列表
        offset = (page - 1) * limit
        stmt = base.order_by(ProductMapping.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        mappings = result.scalars().all()
        
        logger.info(f"✅ 查询到 {len(mappings)} 条商品映射记录, 总数 {total}")
        
        # 批量加载关联：核心商品、核心变体、外部系统
        product_ids = list({m.core_product_id for m in mappings if m.core_product_id})
        variant_ids = list({m.core_variant_id for m in mappings if m.core_variant_id})
        system_ids = list({m.external_system_id for m in mappings if m.external_system_id})
        
        products_by_id = {}
        if product_ids:
            prod_result = await db.execute(select(Product).where(Product.id.in_(product_ids)))
            for p in prod_result.scalars().all():
                products_by_id[p.id] = p
        variants_by_id = {}
        if variant_ids:
            var_result = await db.execute(select(ProductVariant).where(ProductVariant.id.in_(variant_ids)))
            for v in var_result.scalars().all():
                variants_by_id[v.id] = v
        systems_by_id = {}
        if system_ids:
            sys_result = await db.execute(select(ExternalSystem).where(ExternalSystem.id.in_(system_ids)))
            for s in sys_result.scalars().all():
                systems_by_id[s.id] = s
        
        mapping_responses = []
        for mapping in mappings:
            core_product = products_by_id.get(mapping.core_product_id) if mapping.core_product_id else None
            core_variant = variants_by_id.get(mapping.core_variant_id) if mapping.core_variant_id else None
            external_system = systems_by_id.get(mapping.external_system_id) if mapping.external_system_id else None
            mapping_responses.append({
                "id": mapping.id,
                "id_hashid": encode_id(mapping.id),
                "core_product_id": mapping.core_product_id,
                "core_variant_id": mapping.core_variant_id,
                "external_system_id": mapping.external_system_id,
                "external_product_id": mapping.external_product_id,
                "external_variant_id": mapping.external_variant_id,
                "mapping_type": mapping.mapping_type,
                "sync_direction": mapping.sync_direction,
                "sync_status": mapping.sync_status,
                "created_at": mapping.created_at.isoformat() if mapping.created_at else None,
                "core_product_title": core_product.title if core_product else "未知商品",
                "core_variant_sku": core_variant.sku if core_variant else None,
                "external_system_name": external_system.name if external_system else "未知系统",
                "system_type": external_system.system_type.value if external_system else "UNKNOWN"
            })
        
        pages = (total + limit - 1) // limit if total else 0
        logger.info(f"✅ 商品映射列表获取成功: 本页 {len(mapping_responses)} 条, 总 {total}")
        
        return {
            "mappings": mapping_responses,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": pages
            }
        }
        
    except Exception as e:
        logger.error(f"❌ 获取商品映射列表失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to get product mappings: {str(e)}")


class BatchDeleteMappingsRequest(BaseModel):
    """批量删除商品映射请求"""
    mapping_id_hashids: List[str]


class BatchDeleteByFilterRequest(BaseModel):
    """按当前筛选条件批量删除映射请求（与列表筛选参数一致）"""
    core_product_id: Optional[int] = None
    core_product_title: Optional[str] = None
    external_system_id: Optional[int] = None
    sync_status: Optional[str] = None
    mapping_type: Optional[str] = None
    system_type: Optional[str] = None


def _build_mapping_filter_subquery(tenant_id: int, req: BatchDeleteByFilterRequest):
    """构建与 get_product_mappings 一致的筛选子查询，返回 select(ProductMapping.id)。"""
    subq = select(ProductMapping.id).where(ProductMapping.tenant_id == tenant_id)
    if req.core_product_id:
        subq = subq.where(ProductMapping.core_product_id == req.core_product_id)
    if req.core_product_title and req.core_product_title.strip():
        term = f"%{req.core_product_title.strip()}%"
        subq = subq.join(Product, ProductMapping.core_product_id == Product.id).where(
            Product.tenant_id == tenant_id,
            Product.title.ilike(term)
        )
    if req.external_system_id is not None:
        subq = subq.where(ProductMapping.external_system_id == req.external_system_id)
    if req.sync_status:
        subq = subq.where(ProductMapping.sync_status == req.sync_status)
    if req.mapping_type:
        subq = subq.where(ProductMapping.mapping_type == req.mapping_type)
    if req.system_type:
        subq = subq.join(ExternalSystem, ProductMapping.external_system_id == ExternalSystem.id)
        subq = subq.where(ExternalSystem.system_type == req.system_type)
    return subq


@router.post("/mappings/batch-delete-by-filter", response_model=dict)
async def batch_delete_product_mappings_by_filter(
    request: BatchDeleteByFilterRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    按当前筛选条件删除所有符合条件的商品映射（如：外部系统=Shopify 时删除全部 Shopify 映射）。
    至少需传一个筛选条件，避免误删全表。
    """
    tenant, user = auth
    req = request
    has_filter = any([
        req.core_product_id is not None,
        bool(req.core_product_title and req.core_product_title.strip()),
        req.external_system_id is not None,
        bool(req.sync_status),
        bool(req.mapping_type),
        bool(req.system_type),
    ])
    if not has_filter:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请至少选择一个筛选条件（如外部系统=Shopify），避免误删全部映射",
        )
    try:
        id_subq = _build_mapping_filter_subquery(tenant.id, req)
        delete_stmt = delete(ProductMapping).where(ProductMapping.id.in_(id_subq))
        result = await db.execute(delete_stmt)
        await db.commit()
        deleted = result.rowcount or 0
        logger.info(f"✅ 按条件批量删除商品映射: deleted={deleted}, tenant_id={tenant.id}, filters={req.model_dump()}")
        return {
            "deleted": deleted,
            "message": f"已按条件删除 {deleted} 条映射",
        }
    except Exception as e:
        logger.error(f"❌ 按条件批量删除商品映射失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mappings/batch-delete", response_model=dict)
async def batch_delete_product_mappings(
    request: BatchDeleteMappingsRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    批量删除商品映射。仅删除当前租户下且存在的映射。
    """
    tenant, user = auth
    ids = request.mapping_id_hashids or []
    if not ids:
        return {"deleted": 0, "failed": 0, "message": "No mapping IDs provided"}

    deleted = 0
    failed = 0
    try:
        for mapping_id_hashid in ids:
            try:
                mapping_id = decode_id(mapping_id_hashid)
            except Exception:
                failed += 1
                continue
            mapping_stmt = select(ProductMapping).where(
                ProductMapping.id == mapping_id,
                ProductMapping.tenant_id == tenant.id
            )
            mapping_result = await db.execute(mapping_stmt)
            mapping = mapping_result.scalar_one_or_none()
            if mapping:
                await db.delete(mapping)
                deleted += 1
            else:
                failed += 1
        await db.commit()
        logger.info(f"✅ 批量删除商品映射: deleted={deleted}, failed={failed}, tenant_id={tenant.id}")
        return {
            "deleted": deleted,
            "failed": failed,
            "message": f"已删除 {deleted} 条映射" + (f"，{failed} 条无效或不存在" if failed else ""),
        }
    except Exception as e:
        logger.error(f"❌ 批量删除商品映射失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/mappings/{mapping_id_hashid}")
async def delete_product_mapping(
    mapping_id_hashid: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    删除商品映射
    """
    tenant, user = auth
    
    try:
        logger.info("🗑️ 开始删除商品映射", 
                   mapping_id_hashid=mapping_id_hashid, tenant_id=tenant.id)
        
        # 解码映射ID
        try:
            mapping_id = decode_id(mapping_id_hashid)
            logger.info(f"✅ 映射ID解码成功: {mapping_id_hashid} -> {mapping_id}")
        except Exception as e:
            logger.error(f"❌ 映射ID解码失败: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid mapping ID")
        
        # 查找映射记录
        mapping_stmt = select(ProductMapping).where(
            ProductMapping.id == mapping_id,
            ProductMapping.tenant_id == tenant.id
        )
        mapping_result = await db.execute(mapping_stmt)
        mapping = mapping_result.scalar_one_or_none()
        
        if not mapping:
            logger.error(f"❌ 商品映射不存在: mapping_id={mapping_id}")
            raise HTTPException(status_code=404, detail="Product mapping not found")
        
        logger.info(f"✅ 找到商品映射: {mapping.id}")
        
        # 删除映射记录
        await db.delete(mapping)
        await db.commit()
        
        logger.info(f"✅ 商品映射删除成功: mapping_id={mapping.id}")
        
        return {"message": "Product mapping deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除商品映射失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete product mapping: {str(e)}")
