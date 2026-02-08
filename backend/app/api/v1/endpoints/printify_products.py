"""
Printify Products API endpoints
管理 Printify 商品的本地数据库操作
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.schemas.base import BaseResponse

from app.core.database import get_async_db
from app.core.tenant_auth_dependency import verify_tenant_auth
from app.core.logging import get_logger
from app.core.hashids_utils import encode_id, decode_id
from app.models.tenant import Tenant
from app.models.user import User
from app.models.printify_product import PrintifyProduct, PrintifyVariant
from app.models.external_system import ExternalSystem
from app.services.printify_product_service import PrintifyProductService
from sqlalchemy import select

logger = get_logger(__name__)

router = APIRouter()


class PrintifyProductResponse(BaseResponse):
    """Printify 商品响应模型"""
    id: int
    id_hashid: str
    tenant_id: int
    external_system_id: int
    printify_product_id: str
    printify_shop_id: Optional[str]
    title: str
    description: Optional[str]
    tags: Optional[List[str]]
    visible: bool
    is_locked: bool
    is_published: bool = True  # 是否已发布到销售渠道，用于筛选
    external: Optional[Dict[str, Any]]
    user_id: Optional[int]
    print_provider_id: Optional[int]
    options: Optional[List[Dict[str, Any]]]
    variants: Optional[List[Dict[str, Any]]]
    images: Optional[List[Dict[str, Any]]]
    print_areas: Optional[List[Dict[str, Any]]]
    raw_data: Optional[Dict[str, Any]]
    last_synced_at: Optional[str]
    sync_status: str
    sync_error: Optional[str]
    pass


class PrintifyVariantResponse(BaseModel):
    """Printify 变体响应模型"""
    id: int
    id_hashid: str
    tenant_id: int
    printify_product_id: int
    printify_variant_id: int
    sku: Optional[str]
    title: Optional[str]
    cost: Optional[float]
    price: Optional[float]
    grams: Optional[int]
    is_enabled: bool
    is_default: bool
    is_available: bool
    options: Optional[List[int]]
    raw_data: Optional[Dict[str, Any]]
    pass


class PrintifyProductListResponse(BaseModel):
    """Printify 商品列表响应模型"""
    products: List[PrintifyProductResponse]
    pagination: Dict[str, Any]


@router.get("/", response_model=PrintifyProductListResponse)
async def get_printify_products(
    external_system_id_hashid: Optional[str] = Query(None, description="外部系统 ID (hashid)"),
    external_system_id: Optional[str] = Query(None, description="外部系统 ID (hashid)，与 external_system_id_hashid 同义，前端常用"),
    limit: int = Query(50, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    visible_only: bool = Query(True, description="只显示可见商品"),
    published_only: Optional[bool] = Query(None, description="按发布状态筛选: true=仅已发布, false=仅未发布, 不传=全部"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """获取 Printify 商品列表"""
    tenant, user = auth
    hashid = external_system_id_hashid or external_system_id

    try:
        logger.info("🔍 开始获取 Printify 商品列表",
                   tenant_id=tenant.id,
                   external_system_id_hashid=hashid)

        # 解码外部系统 ID，并读取首选店铺（用于只显示当前店铺商品，避免店铺不一致）
        external_system_id = None
        printify_shop_id: Optional[str] = None
        if hashid:
            try:
                external_system_id = decode_id(hashid)
                logger.info(f"✅ 外部系统ID解码成功: {hashid} -> {external_system_id}")
            except Exception as e:
                logger.error(f"❌ 外部系统ID解码失败: {hashid} -> {str(e)}")
                raise HTTPException(status_code=400, detail="Invalid external system ID")
            # 若外部系统配置了首选店铺，只返回该店铺商品
            es_result = await db.execute(
                select(ExternalSystem.settings).where(
                    ExternalSystem.id == external_system_id,
                    ExternalSystem.tenant_id == tenant.id,
                )
            )
            row = es_result.one_or_none()
            settings = None
            if row is not None:
                if isinstance(row, dict):
                    settings = row
                elif hasattr(row, "_mapping"):
                    settings = row._mapping.get("settings")
                else:
                    settings = getattr(row, "settings", None)
            if settings and isinstance(settings, dict):
                raw = settings.get("printify_shop_id")
                if raw is not None:
                    printify_shop_id = str(raw).strip() or None

        # 获取商品列表（按店铺、发布状态过滤）
        service = PrintifyProductService(db)
        products = await service.get_products_by_tenant(
            tenant_id=tenant.id,
            external_system_id=external_system_id,
            limit=limit,
            offset=offset,
            published_only=published_only,
            printify_shop_id=printify_shop_id,
        )
        
        # 过滤可见商品
        if visible_only:
            products = [p for p in products if p.visible]
        
        # 构建响应
        product_responses = []
        for product in products:
            product_responses.append(PrintifyProductResponse(
                id=product.id,
                id_hashid=encode_id(product.id),
                tenant_id=product.tenant_id,
                external_system_id=product.external_system_id,
                printify_product_id=product.printify_product_id,
                printify_shop_id=product.printify_shop_id,
                title=product.title,
                description=product.description,
                tags=product.tags,
                visible=product.visible,
                is_locked=product.is_locked,
                is_published=product.is_published,
                external=product.external,
                user_id=product.user_id,
                print_provider_id=product.print_provider_id,
                options=product.options,
                variants=product.variants,
                images=product.images,
                print_areas=product.print_areas,
                raw_data=product.raw_data,
                last_synced_at=product.last_synced_at.isoformat() if product.last_synced_at else None,
                sync_status=product.sync_status,
                sync_error=product.sync_error,
                created_at=product.created_at.isoformat(),
                updated_at=product.updated_at.isoformat() if product.updated_at else None
            ))
        
        logger.info(f"✅ Printify 商品列表获取成功: 共 {len(product_responses)} 条记录")
        
        return PrintifyProductListResponse(
            products=product_responses,
            pagination={
                "limit": limit,
                "offset": offset,
                "total": len(product_responses),
                "has_more": len(products) == limit
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取 Printify 商品列表失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to get Printify products: {str(e)}")


class ClearByExternalSystemRequest(BaseModel):
    """按外部系统清空 Printify 本地数据请求"""
    external_system_id_hashid: str


@router.post("/clear-by-external-system", response_model=dict)
async def clear_printify_products_by_external_system(
    body: ClearByExternalSystemRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
):
    """
    清空该外部系统下所有 Printify 本地数据（printify_products、printify_variants、对应 external_products）。
    清空后可再点击「同步商品到本地」重新拉取。
    """
    tenant, user = auth
    try:
        external_system_id = decode_id(body.external_system_id_hashid)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid external system ID")
    service = PrintifyProductService(db)
    result = await service.clear_products_by_external_system(tenant.id, external_system_id)
    return {"message": "Printify data cleared", **result}


@router.get("/verify-data", response_model=dict)
async def verify_printify_data(
    external_system_id_hashid: str = Query(..., description="外部系统 hashid"),
    limit: int = Query(2, ge=1, le=10, description="抽查商品数量"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
):
    """
    同步后校验：返回若干商品的 options 与 variants 摘要，用于确认维度/变体数据是否正确
    （如 product.options 含 name/values、variant 含 options 或 title，便于匹配 White 等）
    """
    tenant, user = auth
    try:
        external_system_id = decode_id(external_system_id_hashid)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid external system ID")
    service = PrintifyProductService(db)
    products = await service.get_products_by_tenant(
        tenant_id=tenant.id,
        external_system_id=external_system_id,
        limit=limit,
        offset=0,
    )
    summary = []
    for p in products:
        opts = p.options or []
        option_summary = [
            {
                "name": o.get("name"),
                "values_count": len(o.get("values") or []),
                "value_titles": [v.get("title") for v in (o.get("values") or [])[:8]],
            }
            for o in opts
        ]
        variants = p.variants or []
        variant_sample = []
        for v in variants[:5]:
            opt_ids = v.get("options")
            variant_sample.append({
                "id": v.get("id"),
                "title": v.get("title"),
                "has_options": isinstance(opt_ids, list) and len(opt_ids) > 0,
                "options": opt_ids,
            })
        summary.append({
            "printify_product_id": p.printify_product_id,
            "title": p.title,
            "options": option_summary,
            "variants_count": len(variants),
            "variant_sample": variant_sample,
        })
    return {"external_system_id_hashid": external_system_id_hashid, "products": summary}


@router.get("/{product_id_hashid}", response_model=PrintifyProductResponse)
async def get_printify_product(
    product_id_hashid: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """获取单个 Printify 商品"""
    tenant, user = auth
    
    try:
        logger.info("🔍 开始获取 Printify 商品详情", 
                   tenant_id=tenant.id,
                   product_id_hashid=product_id_hashid)
        
        # 解码商品 ID
        try:
            product_id = decode_id(product_id_hashid)
            logger.info(f"✅ 商品ID解码成功: {product_id_hashid} -> {product_id}")
        except Exception as e:
            logger.error(f"❌ 商品ID解码失败: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid product ID")
        
        # 获取商品
        service = PrintifyProductService(db)
        product = await service.get_product_by_id(product_id)
        
        if not product:
            logger.error(f"❌ Printify 商品不存在: product_id={product_id}")
            raise HTTPException(status_code=404, detail="Printify product not found")
        
        # 检查租户权限
        if product.tenant_id != tenant.id:
            logger.error(f"❌ 无权限访问商品: product_tenant={product.tenant_id}, user_tenant={tenant.id}")
            raise HTTPException(status_code=403, detail="Access denied")
        
        logger.info(f"✅ Printify 商品获取成功: {product.title}")
        
        return PrintifyProductResponse(
            id=product.id,
            id_hashid=encode_id(product.id),
            tenant_id=product.tenant_id,
            external_system_id=product.external_system_id,
            printify_product_id=product.printify_product_id,
            printify_shop_id=product.printify_shop_id,
            title=product.title,
            description=product.description,
            tags=product.tags,
            visible=product.visible,
            is_locked=product.is_locked,
            is_published=product.is_published,
            external=product.external,
            user_id=product.user_id,
            print_provider_id=product.print_provider_id,
            options=product.options,
            variants=product.variants,
            images=product.images,
            print_areas=product.print_areas,
            raw_data=product.raw_data,
            last_synced_at=product.last_synced_at.isoformat() if product.last_synced_at else None,
            sync_status=product.sync_status,
            sync_error=product.sync_error,
            created_at=product.created_at.isoformat(),
            updated_at=product.updated_at.isoformat() if product.updated_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取 Printify 商品失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to get Printify product: {str(e)}")


@router.delete("/{product_id_hashid}")
async def delete_printify_product(
    product_id_hashid: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """删除 Printify 商品"""
    tenant, user = auth
    
    try:
        logger.info("🗑️ 开始删除 Printify 商品", 
                   tenant_id=tenant.id,
                   product_id_hashid=product_id_hashid)
        
        # 解码商品 ID
        try:
            product_id = decode_id(product_id_hashid)
            logger.info(f"✅ 商品ID解码成功: {product_id_hashid} -> {product_id}")
        except Exception as e:
            logger.error(f"❌ 商品ID解码失败: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid product ID")
        
        # 检查商品是否存在和权限
        service = PrintifyProductService(db)
        product = await service.get_product_by_id(product_id)
        
        if not product:
            logger.error(f"❌ Printify 商品不存在: product_id={product_id}")
            raise HTTPException(status_code=404, detail="Printify product not found")
        
        if product.tenant_id != tenant.id:
            logger.error(f"❌ 无权限删除商品: product_tenant={product.tenant_id}, user_tenant={tenant.id}")
            raise HTTPException(status_code=403, detail="Access denied")
        
        # 删除商品
        success = await service.delete_product(product_id)
        
        if success:
            logger.info(f"✅ Printify 商品删除成功: product_id={product_id}")
            return {"message": "Printify product deleted successfully"}
        else:
            logger.error(f"❌ Printify 商品删除失败: product_id={product_id}")
            raise HTTPException(status_code=500, detail="Failed to delete Printify product")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除 Printify 商品失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to delete Printify product: {str(e)}")


@router.post("/sync")
async def sync_printify_products(
    external_system_id_hashid: str,
    products_data: List[Dict[str, Any]],
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """同步 Printify 商品到本地数据库"""
    tenant, user = auth
    
    try:
        logger.info("🔄 开始同步 Printify 商品", 
                   tenant_id=tenant.id,
                   external_system_id_hashid=external_system_id_hashid,
                   product_count=len(products_data))
        
        # 解码外部系统 ID
        try:
            external_system_id = decode_id(external_system_id_hashid)
            logger.info(f"✅ 外部系统ID解码成功: {external_system_id_hashid} -> {external_system_id}")
        except Exception as e:
            logger.error(f"❌ 外部系统ID解码失败: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid external system ID")
        
        # 同步商品
        service = PrintifyProductService(db)
        result = await service.sync_products_from_api(
            tenant_id=tenant.id,
            external_system_id=external_system_id,
            api_products=products_data
        )
        
        logger.info("✅ Printify 商品同步完成", **result)
        
        return {
            "message": "Printify products synced successfully",
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 同步 Printify 商品失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to sync Printify products: {str(e)}")
