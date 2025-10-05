from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.tenant_auth_dependency import verify_tenant_auth
from app.core.logging import get_logger

router = APIRouter()


@router.get("/{store_id}/products", response_model=dict)
async def get_shopify_products(
    store_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    sort_by: str = Query("title"),
    sort_order: str = Query("asc"),
    status: str = Query(""),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_tenant_auth),
) -> Any:
    """
    Get Shopify products for a specific store
    """
    logger = get_logger(__name__)

    try:
        logger.info(f"🔍 开始获取 Shopify 商品列表: store_id={store_id}")
        tenant, user = auth
        logger.info(f"✅ 认证成功: tenant_id={tenant.id}, user_id={user.id}")

        # Import here to avoid circular imports
        from app.services.external_system_service import ExternalSystemService
        from app.services.shopify_service import ShopifyService

        # Get external system by store_id (convert to int for database ID)
        external_system_service = ExternalSystemService(db)
        external_system = await external_system_service.get_external_system(
            int(store_id), tenant.id
        )

        if not external_system:
            logger.error(
                f"❌ 未找到外部系统: store_id={store_id}, tenant_id={tenant.id}"
            )
            raise HTTPException(status_code=404, detail="Store not found")

        if external_system.system_type.value != "SHOPIFY":
            logger.error(
                f"❌ 不是Shopify系统: system_type={external_system.system_type}"
            )
            raise HTTPException(status_code=400, detail="Not a Shopify store")

        logger.info(f"✅ 找到Shopify店铺: {external_system.name}")

        # Get credentials from external system
        from app.core.security import decrypt_data

        credentials = external_system.credentials
        if not credentials or "access_token" not in credentials:
            logger.error(f"❌ 店铺凭据未配置: store_id={store_id}")
            raise HTTPException(
                status_code=400, detail="Store credentials not configured"
            )

        # Decrypt access token
        try:
            access_token = decrypt_data(credentials["access_token"])
            shop_id = external_system.external_system_id
            api_version = credentials.get("api_version", "2024-10")
            logger.info(f"✅ 凭据解密成功: shop_id={shop_id}")
        except Exception as e:
            logger.error(f"❌ 凭据解密失败: {str(e)}")
            raise HTTPException(status_code=400, detail="Failed to decrypt credentials")

        # Initialize Shopify service and get products
        shopify_service = ShopifyService(db)

        # Get products from Shopify API
        products_data = await shopify_service.get_products(
            shop_id=shop_id, access_token=access_token, api_version=api_version
        )

        logger.info(
            f"✅ 成功获取商品数据: count={len(products_data.get('products', []))}"
        )

        return {
            "success": True,
            "products": products_data.get("products", []),
            "pagination": products_data.get("pagination", {}),
            "total": products_data.get("total", 0),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取商品列表失败: {str(e)}")
        import traceback

        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get products: {str(e)}",
        )


