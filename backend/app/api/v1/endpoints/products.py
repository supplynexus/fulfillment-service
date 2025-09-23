"""
Product management endpoints - 新的商品系统API
"""

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_async_db
from app.core.tenant_auth_dependency import verify_tenant_auth
from app.core.logging import get_logger
from app.core.hashids_utils import encode_id, decode_id
from app.models.tenant import Tenant
from app.models.user import User
from app.models.external_system import ExternalSystem, ExternalSystemType
from app.models.product_new import (
    Product, ProductDimension, ProductVariant, VariantAttribute,
    ProductTag, Tag, ProductMapping, ExternalProduct
)
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
            
            # 构建映射响应
            mappings = []
            if include_mappings and product.mappings:
                for mapping in product.mappings:
                    # 获取外部系统名称 - 安全访问，避免懒加载
                    external_system_name = "Unknown"
                    try:
                        # 检查是否有外部系统ID，如果有则查询外部系统名称
                        if mapping.external_system_id:
                            # 这里我们暂时使用 "External System" 作为默认名称
                            # 在实际应用中，可以通过额外的查询获取外部系统名称
                            external_system_name = f"External System {mapping.external_system_id}"
                    except Exception as e:
                        logger.warning(f"无法获取外部系统名称: {str(e)}")
                        external_system_name = "Unknown"
                    
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
        
        # 构建映射数据
        if include_mappings and hasattr(product, 'mappings') and product.mappings:
            for mapping in product.mappings:
                mappings.append(ProductMappingResponse(
                    id_hashid=encode_id(mapping.id),
                    core_variant_id_hashid=encode_id(mapping.core_variant_id) if mapping.core_variant_id else None,
                    external_system_name="Shopify",  # 这里应该从external_system表获取
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
        
        # 软删除
        product.is_active = False
        product.status = "archived"
        
        # 提交事务
        await db.commit()
        
        logger.info(f"✅ 商品删除成功: {product.title} (ID: {product.id})")
        
        return {"message": "Product deleted successfully", "product_id": product_hashid}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除商品失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete product: {str(e)}")


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
