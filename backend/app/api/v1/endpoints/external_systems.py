"""
External system management API endpoints
"""

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.tenant_auth_dependency import verify_tenant_auth
from app.core.logging import get_logger
from app.models.tenant import Tenant
from app.models.user import User
from app.models.external_system import ExternalSystemType
from app.services.external_system_service import ExternalSystemService
from app.schemas.external_system import (
    ExternalSystemCreate,
    ExternalSystemUpdate,
    ExternalSystemResponse,
    ExternalSystemSecureResponse,
    ExternalSystemSecureListResponse,
)

router = APIRouter()


@router.post("/", response_model=ExternalSystemResponse)
async def create_external_system(
    external_system_data: ExternalSystemCreate,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    Create a new external system integration
    """
    tenant, user = auth
    logger = get_logger(__name__)

    logger.info(
        "🔍 开始创建外部系统",
        {
            "tenant_id": tenant.id,
            "tenant_name": tenant.name,
            "system_type": external_system_data.system_type,
            "name": external_system_data.name,
            "external_system_id": external_system_data.external_system_id,
        },
    )

    service = ExternalSystemService(db)

    try:
        # Convert to uppercase to match enum values
        system_type_upper = external_system_data.system_type.upper()
        logger.info(
            "🔍 系统类型转换",
            {
                "original": external_system_data.system_type,
                "converted": system_type_upper,
            },
        )
        system_type = ExternalSystemType(system_type_upper)
        logger.info("✅ 系统类型验证成功", {"system_type": system_type.value})
    except ValueError as e:
        logger.error(
            "❌ 系统类型验证失败",
            {"system_type": system_type_upper, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid system type: {system_type_upper}",
        )

    try:
        external_system = await service.create_external_system(
            tenant_id=tenant.id,
            system_type=system_type,
            name=external_system_data.name,
            external_system_id=external_system_data.external_system_id,
            credentials=external_system_data.credentials,
            base_url=external_system_data.base_url,
            webhook_url=external_system_data.webhook_url,
            settings=external_system_data.settings,
        )
        logger.info(
            "✅ 外部系统创建成功",
            {
                "external_system_id": external_system.id,
                "name": external_system.name,
                "system_type": external_system.system_type.value,
            },
        )
        return external_system
    except ValueError as e:
        logger.error(
            "❌ 外部系统创建失败 - 业务逻辑错误",
            {
                "error": str(e),
                "tenant_id": tenant.id,
                "system_type": external_system_data.system_type,
                "external_system_id": external_system_data.external_system_id,
            },
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            "❌ 外部系统创建失败 - 系统错误",
            {
                "error": str(e),
                "tenant_id": tenant.id,
                "system_type": external_system_data.system_type,
                "external_system_id": external_system_data.external_system_id,
            },
        )
        import traceback

        logger.error("   异常堆栈", stack=traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/", response_model=ExternalSystemSecureListResponse)
async def get_external_systems(
    system_type: Optional[str] = Query(None, description="Filter by system type"),
    active_only: bool = Query(True, description="Show only active systems"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    Get external systems for the authenticated tenant
    """
    logger = get_logger(__name__)

    try:
        logger.info(
            f"🔍 开始处理外部系统列表请求: system_type={system_type}, active_only={active_only}, skip={skip}, limit={limit}"
        )

        tenant, user = auth
        logger.info(
            f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}"
        )

        logger.info(f"🔍 初始化 ExternalSystemService...")
        service = ExternalSystemService(db)
        logger.info(f"✅ ExternalSystemService 初始化成功")

        # Convert system_type string to enum if provided
        system_type_enum = None
        if system_type:
            logger.info(f"🔍 转换 system_type 字符串到枚举: {system_type}")
            try:
                system_type_enum = ExternalSystemType(system_type)
                logger.info(f"✅ system_type 转换成功: {system_type_enum}")
            except ValueError as e:
                logger.error(f"❌ system_type 转换失败: {system_type}, 错误: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid system type: {system_type}",
                )

        logger.info(
            f"🔍 查询外部系统: tenant_id={tenant.id}, system_type={system_type_enum}, active_only={active_only}"
        )
        try:
            external_systems = await service.get_external_systems_by_tenant(
                tenant_id=tenant.id,
                system_type=system_type_enum,
                active_only=active_only,
            )
            logger.info(f"✅ 查询外部系统成功: 找到 {len(external_systems)} 个系统")
        except Exception as e:
            logger.error(f"❌ 查询外部系统失败: {str(e)}")
            import traceback

            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            raise HTTPException(
                status_code=500, detail=f"Failed to get external systems: {str(e)}"
            )

        # Apply pagination
        total = len(external_systems)
        external_systems = external_systems[skip : skip + limit]
        logger.info(f"✅ 分页处理完成: total={total}, 返回={len(external_systems)}")

        # Decrypt credentials for each external system and add hashids
        from app.core.security import decrypt_data
        from app.core.hashids_utils import encode_id, decode_id

        decrypted_systems = []
        for system in external_systems:
            # Debug: Test encode_id function
            try:
                encoded_id = encode_id(system.id)
                logger.info(
                    f"🔍 Hashids 编码测试: id={system.id} -> hashid={encoded_id}"
                )
            except Exception as e:
                logger.error(f"❌ Hashids 编码失败: id={system.id}, 错误: {str(e)}")
                import traceback

                logger.error(f"   异常堆栈: {traceback.format_exc()}")
                encoded_id = f"error-{system.id}"  # Fallback

            # Decrypt credentials
            decrypted_credentials = {}
            for key, encrypted_value in system.credentials.items():
                try:
                    decrypted_credentials[key] = decrypt_data(encrypted_value)
                except Exception as e:
                    logger.warning(
                        f"Failed to decrypt credential {key} for system {system.id}: {e}"
                    )
                    decrypted_credentials[key] = (
                        ""  # Use empty string if decryption fails
                    )

            # Create ExternalSystemSecureResponse object
            secure_system = ExternalSystemSecureResponse(
                id_hashid=encoded_id,
                system_type=system.system_type.value,
                name=system.name,
                external_system_id=system.external_system_id,
                base_url=system.base_url,
                webhook_url=system.webhook_url,
                credentials=decrypted_credentials,
                settings=system.settings,
                sync_enabled=system.sync_enabled,
                webhook_enabled=system.webhook_enabled,
                sync_interval_minutes=system.sync_interval_minutes,
                external_id=system.external_id,
                is_active=system.is_active,
                last_sync_at=system.last_sync_at,
                last_product_sync_at=system.last_product_sync_at,
                created_at=system.created_at,
                updated_at=system.updated_at,
            )

            decrypted_systems.append(secure_system)

        result = ExternalSystemSecureListResponse(
            external_systems=decrypted_systems, total=total, skip=skip, limit=limit
        )

        logger.info(
            f"✅ 外部系统列表请求处理成功: total={total}, skip={skip}, limit={limit}"
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 外部系统列表请求处理失败: {str(e)}")
        import traceback

        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{external_system_id}", response_model=ExternalSystemResponse)
async def get_external_system(
    external_system_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    Get specific external system
    """
    tenant, user = auth

    service = ExternalSystemService(db)
    external_system = await service.get_external_system(external_system_id, tenant.id)

    if not external_system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="External system not found"
        )

    return external_system


@router.put("/{external_system_id}", response_model=ExternalSystemResponse)
async def update_external_system(
    external_system_id: int,
    external_system_data: ExternalSystemUpdate,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    Update external system
    """
    tenant, user = auth
    logger = get_logger(__name__)

    logger.info(
        "🔍 开始更新外部系统",
        {
            "tenant_id": tenant.id,
            "tenant_name": tenant.name,
            "external_system_id": external_system_id,
            "system_type": external_system_data.system_type,
            "name": external_system_data.name,
        },
    )

    service = ExternalSystemService(db)

    try:
        # Convert system_type string to enum if provided
        system_type_enum = None
        if external_system_data.system_type:
            # Convert to uppercase to match enum values
            system_type_upper = external_system_data.system_type.upper()
            logger.info(
                "🔍 系统类型转换",
                {
                    "original": external_system_data.system_type,
                    "converted": system_type_upper,
                },
            )
            try:
                system_type_enum = ExternalSystemType(system_type_upper)
                logger.info(
                    "✅ 系统类型验证成功", {"system_type": system_type_enum.value}
                )
            except ValueError as e:
                logger.error(
                    "❌ 系统类型验证失败",
                    {"system_type": system_type_upper, "error": str(e)},
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid system type: {system_type_upper}",
                )

        # Prepare update data
        update_data = external_system_data.dict(exclude_unset=True)
        if system_type_enum:
            update_data["system_type"] = system_type_enum

        # Remove external_system_id from update_data to avoid conflict with the parameter
        update_data.pop("external_system_id", None)

        logger.info("🔍 准备更新数据", {"update_data_keys": list(update_data.keys())})

        external_system = await service.update_external_system(
            external_system_id=external_system_id, tenant_id=tenant.id, **update_data
        )

        if not external_system:
            logger.error(
                "❌ 外部系统未找到",
                {"external_system_id": external_system_id, "tenant_id": tenant.id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="External system not found",
            )

        logger.info(
            "✅ 外部系统更新成功",
            {
                "external_system_id": external_system.id,
                "name": external_system.name,
                "system_type": external_system.system_type.value,
            },
        )

        return external_system

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "❌ 外部系统更新失败",
            {
                "error": str(e),
                "tenant_id": tenant.id,
                "external_system_id": external_system_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update external system: {str(e)}",
        )


@router.delete("/{external_system_id}")
async def delete_external_system(
    external_system_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    Delete external system (soft delete)
    """
    tenant, user = auth

    service = ExternalSystemService(db)
    success = await service.delete_external_system(external_system_id, tenant.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="External system not found"
        )

    return {"message": "External system deleted successfully"}


@router.post("/printify/test-connection", response_model=dict)
async def test_printify_connection(
    request_data: dict,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    Test Printify connection using provided credentials
    """
    logger = get_logger(__name__)

    try:
        logger.info(f"🔍 开始处理 Printify 测试连接请求")

        tenant, user = auth
        logger.info(
            f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}"
        )

        # Extract credentials from request
        encrypted_access_token = request_data.get("access_token")
        encrypted_shop_id = request_data.get("shop_id")
        base_url = request_data.get("base_url", "https://api.printify.com")

        logger.info(
            f"🔍 提取的加密凭据: shop_id={encrypted_shop_id}, base_url={base_url}, has_access_token={bool(encrypted_access_token)}"
        )

        if not encrypted_access_token or not encrypted_shop_id:
            logger.error(
                f"❌ 缺少必要参数: access_token={bool(encrypted_access_token)}, shop_id={bool(encrypted_shop_id)}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required parameters: access_token and shop_id",
            )

        # Handle credentials - try to decrypt first, if fails use as plain text (for test connection)
        from app.core.security import decrypt_data

        try:
            # Try to decrypt first (for saved stores)
            access_token = decrypt_data(encrypted_access_token)
            shop_id = decrypt_data(encrypted_shop_id)
            logger.info(
                f"✅ 凭据解密成功: shop_id={shop_id}, has_access_token={bool(access_token)}"
            )
        except Exception as e:
            # If decryption fails, use as plain text (for test connection from dialog)
            logger.info(f"ℹ️ 凭据解密失败，使用明文凭据进行测试连接: {str(e)}")
            access_token = encrypted_access_token
            shop_id = encrypted_shop_id
            logger.info(
                f"✅ 使用明文凭据: shop_id={shop_id}, has_access_token={bool(access_token)}"
            )

        # Import PrintifyService
        from app.services.printify_service import PrintifyService

        logger.info(f"🔍 初始化 PrintifyService...")
        printify_service = PrintifyService(printify_api_token=access_token)
        logger.info(f"✅ PrintifyService 初始化成功")

        logger.info(f"🔍 开始测试 Printify 连接...")
        try:
            result = await printify_service.test_connection()
            logger.info(f"✅ Printify 连接测试成功: {result}")

            # Add shop_id to the result for frontend compatibility
            result["shop_id"] = shop_id
            logger.info(f"✅ 添加 shop_id 到响应: {shop_id}")

            return result
        except Exception as e:
            logger.error(f"❌ Printify 连接测试失败: {str(e)}")
            import traceback

            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Printify connection test failed: {str(e)}",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Printify 测试连接请求处理失败: {str(e)}")
        import traceback

        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.post("/shopify/test-connection", response_model=dict)
async def test_shopify_connection(
    request_data: dict,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    Test Shopify connection using provided credentials
    """
    logger = get_logger(__name__)

    try:
        logger.info(f"🔍 开始处理 Shopify 测试连接请求")

        tenant, user = auth
        logger.info(
            f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}"
        )

        # Extract credentials from request
        encrypted_access_token = request_data.get("access_token")
        encrypted_shop_id = request_data.get("shop_id")
        api_version = request_data.get("api_version", "2024-10")

        logger.info(
            f"🔍 提取的加密凭据: shop_id={encrypted_shop_id}, api_version={api_version}, has_access_token={bool(encrypted_access_token)}"
        )

        if not encrypted_access_token or not encrypted_shop_id:
            logger.error(
                f"❌ 缺少必要参数: access_token={bool(encrypted_access_token)}, shop_id={bool(encrypted_shop_id)}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required parameters: access_token and shop_id",
            )

        # Handle credentials - try to decrypt first, if fails use as plain text (for test connection)
        from app.core.security import decrypt_data

        try:
            # Try to decrypt first (for saved stores)
            access_token = decrypt_data(encrypted_access_token)
            shop_id = decrypt_data(encrypted_shop_id)
            logger.info(
                f"✅ 凭据解密成功: shop_id={shop_id}, has_access_token={bool(access_token)}"
            )
        except Exception as e:
            # If decryption fails, use as plain text (for test connection from dialog)
            logger.info(f"ℹ️ 凭据解密失败，使用明文凭据进行测试连接: {str(e)}")
            access_token = encrypted_access_token
            shop_id = encrypted_shop_id
            logger.info(
                f"✅ 使用明文凭据: shop_id={shop_id}, has_access_token={bool(access_token)}"
            )

        # Import ShopifyService
        from app.services.shopify_service import ShopifyService

        logger.info(f"🔍 初始化 ShopifyService...")
        shopify_service = ShopifyService(db)
        logger.info(f"✅ ShopifyService 初始化成功")

        logger.info(f"🔍 开始测试 Shopify 连接...")
        try:
            result = await shopify_service.test_connection_with_params(
                shop_id=shop_id,
                access_token=access_token,
                base_url=f"https://{shop_id}.myshopify.com",
                api_version=api_version,
            )
            logger.info(f"✅ Shopify 连接测试成功: {result}")

            # Add shop_id to the result for frontend compatibility
            result["shop_id"] = shop_id
            logger.info(f"✅ 添加 shop_id 到响应: {shop_id}")

            return result
        except Exception as e:
            logger.error(f"❌ Shopify 连接测试失败: {str(e)}")
            import traceback

            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Shopify connection test failed: {str(e)}",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Shopify 测试连接请求处理失败: {str(e)}")
        import traceback

        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.get("/printify/{external_system_hashid}/products", response_model=dict)
async def get_printify_products(
    external_system_hashid: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    Get products from Printify store by external system ID (hashid)
    """
    logger = get_logger(__name__)

    try:
        logger.info(
            f"🔍 开始处理 Printify 商品列表请求: external_system_hashid={external_system_hashid}"
        )

        tenant, user = auth
        logger.info(
            f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}"
        )

        # Decode hashid to get external system ID
        from app.core.hashids_utils import decode_id

        try:
            external_system_id = decode_id(external_system_hashid)
            if not external_system_id:
                logger.error(f"❌ 无效的 hashid: {external_system_hashid}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid external system ID",
                )
            logger.info(
                f"✅ hashid 解码成功: {external_system_hashid} -> {external_system_id}"
            )
        except Exception as e:
            logger.error(f"❌ hashid 解码失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to decode external system ID",
            )

        # Get external system by ID
        service = ExternalSystemService(db)
        external_system = await service.get_external_system(
            external_system_id, tenant.id
        )

        if not external_system:
            logger.error(f"❌ 未找到外部系统: external_system_id={external_system_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="External system not found",
            )

        if external_system.system_type != ExternalSystemType.PRINTIFY:
            logger.error(
                f"❌ 外部系统类型错误: expected=PRINTIFY, actual={external_system.system_type}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="External system is not a Printify store",
            )

        # Get decrypted credentials
        decrypted_credentials = await service.get_decrypted_credentials(
            external_system.id, tenant.id
        )
        if not decrypted_credentials:
            logger.error(
                f"❌ 无法获取解密后的凭据: external_system_id={external_system.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get decrypted credentials",
            )

        access_token = decrypted_credentials.get("access_token")
        shop_id = decrypted_credentials.get("shop_id")

        if not access_token:
            logger.error(
                f"❌ 缺少 access_token: external_system_id={external_system.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access Token not configured for this store",
            )

        if not shop_id:
            logger.error(f"❌ 缺少 shop_id: external_system_id={external_system.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shop ID not configured for this store",
            )

        # Get products using PrintifyService
        from app.services.printify_service import PrintifyService

        printify_service = PrintifyService(printify_api_token=access_token)

        logger.info(f"🔍 开始调用 Printify API 获取商品列表: shop_id={shop_id}")
        products = await printify_service.get_products(shop_id)

        logger.info(f"✅ Printify 商品列表获取成功: 数量={len(products)}")

        return {
            "success": True,
            "external_system_id": external_system_hashid,
            "shop_id": shop_id,
            "products": products,
            "total_count": len(products),
            "message": "Products retrieved successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Printify 商品列表请求处理失败: {str(e)}")
        import traceback

        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get products: {str(e)}",
        )


@router.get("/printify/{external_system_hashid}/orders/{order_id}", response_model=dict)
async def get_printify_order_details(
    external_system_hashid: str,
    order_id: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """Get Printify order details by order ID"""
    logger = get_logger(__name__)
    try:
        logger.info(
            f"🔍 开始处理 Printify 订单详情请求: external_system_hashid={external_system_hashid}, order_id={order_id}"
        )
        tenant, user = auth
        logger.info(
            f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}"
        )

        # Decode hashids to get external_system_id
        from app.core.hashids_utils import decode_id

        try:
            external_system_id = decode_id(external_system_hashid)
            logger.info(
                f"✅ Hashids 解码成功: {external_system_hashid} -> {external_system_id}"
            )
        except Exception as e:
            logger.error(
                f"❌ Hashids 解码失败: {external_system_hashid}, 错误: {str(e)}"
            )
            raise HTTPException(status_code=400, detail="Invalid external system ID")

        # Get external system by primary key
        service = ExternalSystemService(db)
        external_system = await service.get_external_system(
            external_system_id, tenant.id
        )
        if not external_system:
            logger.error(
                f"❌ 未找到外部系统: external_system_id={external_system_id}, tenant_id={tenant.id}"
            )
            raise HTTPException(status_code=404, detail="External system not found")

        logger.info(
            f"✅ 找到外部系统: id={external_system.id}, name={external_system.name}, system_type={external_system.system_type}"
        )

        # Get decrypted credentials
        decrypted_credentials = await service.get_decrypted_credentials(
            external_system.id, tenant.id
        )
        if not decrypted_credentials:
            logger.error(
                f"❌ 无法获取解密后的凭据: external_system_id={external_system.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get decrypted credentials",
            )
        logger.info(f"✅ 凭据解密成功: external_system_id={external_system.id}")

        access_token = decrypted_credentials.get("access_token")
        shop_id = decrypted_credentials.get("shop_id")

        if not access_token:
            logger.error(
                f"❌ 缺少 access_token: external_system_id={external_system.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access Token not configured for this store",
            )

        if not shop_id:
            logger.error(f"❌ 缺少 shop_id: external_system_id={external_system.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shop ID not configured for this store",
            )

        # Get order details using PrintifyService
        from app.services.printify_service import PrintifyService

        printify_service = PrintifyService(printify_api_token=access_token)

        logger.info(
            f"🔍 开始调用 Printify API 获取订单详情: shop_id={shop_id}, order_id={order_id}"
        )
        order_details = await printify_service.get_order(shop_id, order_id)

        if not order_details:
            logger.error(f"❌ Printify 订单详情获取失败: order_id={order_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Printify order not found",
            )

        logger.info(f"✅ Printify 订单详情获取成功: order_id={order_id}")
        # Log the order_details structure for debugging
        import json

        logger.info(
            f"📦 订单详情数据结构: {json.dumps(order_details, ensure_ascii=False, indent=2)}"
        )

        return {
            "success": True,
            "order": order_details,
            "details": {
                "shop_id": shop_id,
                "order_id": order_id,
                "base_url": external_system.base_url,
                "system_type": "PRINTIFY",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Printify 订单详情请求处理失败: {str(e)}")
        import traceback

        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get order details: {str(e)}",
        )


@router.get("/printify/{external_system_hashid}/orders", response_model=dict)
async def get_printify_orders(
    external_system_hashid: str,
    limit: int = 50,
    page: int = 1,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """Get Printify orders for a specific store"""
    logger = get_logger(__name__)
    try:
        logger.info(
            f"🔍 开始处理 Printify 订单列表请求: external_system_hashid={external_system_hashid}, limit={limit}, page={page}"
        )
        tenant, user = auth
        logger.info(
            f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}"
        )

        # Decode hashids to get external_system_id
        from app.core.hashids_utils import decode_id

        try:
            external_system_id = decode_id(external_system_hashid)
            logger.info(
                f"✅ Hashids 解码成功: {external_system_hashid} -> {external_system_id}"
            )
        except Exception as e:
            logger.error(
                f"❌ Hashids 解码失败: {external_system_hashid}, 错误: {str(e)}"
            )
            raise HTTPException(status_code=400, detail="Invalid external system ID")

        # Get external system by primary key
        service = ExternalSystemService(db)
        external_system = await service.get_external_system(
            external_system_id, tenant.id
        )
        if not external_system:
            logger.error(
                f"❌ 未找到外部系统: external_system_id={external_system_id}, tenant_id={tenant.id}"
            )
            raise HTTPException(status_code=404, detail="External system not found")

        logger.info(
            f"✅ 找到外部系统: id={external_system.id}, name={external_system.name}, system_type={external_system.system_type}"
        )

        # Get decrypted credentials
        decrypted_credentials = await service.get_decrypted_credentials(
            external_system.id, tenant.id
        )
        if not decrypted_credentials:
            logger.error(
                f"❌ 无法获取解密后的凭据: external_system_id={external_system.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get decrypted credentials",
            )
        logger.info(f"✅ 凭据解密成功: external_system_id={external_system.id}")

        access_token = decrypted_credentials.get("access_token")
        shop_id = decrypted_credentials.get("shop_id")

        if not access_token:
            logger.error(
                f"❌ 缺少 access_token: external_system_id={external_system.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access Token not configured for this store",
            )

        if not shop_id:
            logger.error(f"❌ 缺少 shop_id: external_system_id={external_system.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shop ID not configured for this store",
            )

        # Get orders using PrintifyService
        from app.services.printify_service import PrintifyService

        printify_service = PrintifyService(printify_api_token=access_token)

        logger.info(
            f"🔍 开始调用 Printify API 获取订单列表: shop_id={shop_id}, limit={limit}, page={page}"
        )
        orders_result = await printify_service.get_orders(shop_id, limit, page)

        if not orders_result.get("success"):
            logger.error(f"❌ Printify API 返回错误: {orders_result}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=orders_result.get(
                    "message", "Failed to get orders from Printify"
                ),
            )

        orders = orders_result.get("orders", [])
        logger.info(f"✅ Printify 订单列表获取成功: 数量={len(orders)}")

        # 处理订单数据，映射字段名以匹配前端期望
        processed_orders = []
        for order in orders:
            # 提取物流信息
            shipments = order.get("shipments", [])
            tracking_number = None
            tracking_url = None
            tracking_company = None
            shipped_at = None
            delivered_at = None
            
            if shipments and len(shipments) > 0:
                # 取第一个包裹的物流信息
                first_shipment = shipments[0]
                tracking_number = first_shipment.get("number")
                tracking_url = first_shipment.get("url")
                tracking_company = first_shipment.get("carrier")
                shipped_at = first_shipment.get("shipped_at")
                delivered_at = first_shipment.get("delivered_at")
            
            # 构建处理后的订单数据
            processed_order = {
                **order,  # 保留原始数据
                "tracking_number": tracking_number,
                "tracking_url": tracking_url,
                "tracking_company": tracking_company,
                "shipped_at": shipped_at,
                "delivered_at": delivered_at,
            }
            processed_orders.append(processed_order)

        return {
            "success": True,
            "external_system_id": external_system_hashid,
            "shop_id": shop_id,
            "orders": processed_orders,
            "total_count": orders_result.get("total_count", 0),
            "current_page": orders_result.get("current_page", page),
            "per_page": orders_result.get("per_page", limit),
            "has_more": orders_result.get("has_more", False),
            "message": "Orders retrieved successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Printify 订单列表请求处理失败: {str(e)}")
        import traceback

        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get orders: {str(e)}",
        )


@router.post("/shopify/{shop_id}/sync-orders", response_model=dict)
async def sync_shopify_orders_by_shop_id(
    shop_id: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """Sync Shopify orders for a specific shop"""
    logger = get_logger(__name__)
    try:
        logger.info(f"🔍 开始处理 Shopify 订单同步请求: shop_id={shop_id}")
        tenant, user = auth
        logger.info(
            f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}"
        )

        # Decode hashid to get external system ID
        from app.core.hashids_utils import decode_id

        try:
            external_system_id = decode_id(shop_id)
            if not external_system_id:
                logger.error(f"❌ 无效的 hashid: {shop_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid external system ID",
                )
            logger.info(f"✅ hashid 解码成功: {shop_id} -> {external_system_id}")
        except Exception as e:
            logger.error(f"❌ hashid 解码失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to decode external system ID",
            )

        # Get external system by ID
        service = ExternalSystemService(db)
        external_system = await service.get_external_system(
            external_system_id, tenant.id
        )
        if not external_system:
            logger.error(
                f"❌ 未找到 Shopify 店铺: external_system_id={external_system_id}, tenant_id={tenant.id}"
            )
            raise HTTPException(status_code=404, detail="Shopify store not found")

        logger.info(
            f"✅ 找到 Shopify 店铺: id={external_system.id}, name={external_system.name}"
        )

        # Get decrypted credentials
        decrypted_credentials = await service.get_decrypted_credentials(
            external_system.id, tenant.id
        )
        if not decrypted_credentials:
            logger.error(
                f"❌ 无法获取解密后的凭据: external_system_id={external_system.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get decrypted credentials",
            )
        logger.info(f"✅ 凭据解密成功: external_system_id={external_system.id}")

        access_token = decrypted_credentials.get("access_token")
        if not access_token:
            logger.error(
                f"❌ 缺少 access_token: external_system_id={external_system.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access Token not configured for this store",
            )

        # Initialize Shopify service and sync orders
        from app.services.shopify_service import ShopifyService

        shopify_service = ShopifyService(db)

        # Extract shop domain from base_url
        base_url = external_system.base_url
        if base_url.startswith("https://"):
            shop_domain = base_url.replace("https://", "").replace(".myshopify.com", "")
        else:
            shop_domain = base_url.replace(".myshopify.com", "")

        logger.info(f"🔍 开始同步 Shopify 订单到 Shopify 表: shop_domain={shop_domain}")
        result = await shopify_service.sync_orders_to_shopify_table(
            shop_id=shop_domain,
            access_token=access_token,
            tenant_id=tenant.id,
            external_system_id=external_system.id,
            api_version=external_system.settings.get("api_version", "2024-10"),
        )

        if not result["success"]:
            logger.error(
                f"❌ Shopify 订单同步失败: {result.get('message', 'Unknown error')}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "Failed to sync orders"),
            )

        logger.info(
            f"✅ Shopify 订单同步成功: 新增 {result.get('orders_synced', 0)} 个订单，更新 {result.get('orders_updated', 0)} 个订单"
        )

        return {
            "success": True,
            "message": result.get("message", "Orders synced successfully"),
            "orders_synced": result.get("orders_synced", 0),
            "orders_updated": result.get("orders_updated", 0),
            "total_processed": result.get("total_processed", 0),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Shopify 订单同步请求处理失败: {str(e)}")
        import traceback

        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync orders: {str(e)}",
        )


@router.post("/by-external-id/{external_id}/test-connection", response_model=dict)
async def test_connection_by_external_id(
    external_id: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """Test connection for external system by external_id"""
    logger = get_logger(__name__)
    try:
        logger.info(f"🔍 开始处理外部系统测试连接请求: external_id={external_id}")
        tenant, user = auth
        logger.info(
            f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}"
        )

        # Get external system by external_id
        service = ExternalSystemService(db)
        external_system = await service.get_external_system_by_external_system_id(
            external_id, tenant.id
        )
        if not external_system:
            logger.error(
                f"❌ 未找到外部系统: external_id={external_id}, tenant_id={tenant.id}"
            )
            raise HTTPException(status_code=404, detail="External system not found")

        logger.info(
            f"✅ 找到外部系统: id={external_system.id}, name={external_system.name}, system_type={external_system.system_type}"
        )

        # Get decrypted credentials
        decrypted_credentials = await service.get_decrypted_credentials(
            external_system.id, tenant.id
        )
        if not decrypted_credentials:
            logger.error(
                f"❌ 无法获取解密后的凭据: external_system_id={external_system.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get decrypted credentials",
            )
        logger.info(f"✅ 凭据解密成功: external_system_id={external_system.id}")

        # Test connection based on system type
        if external_system.system_type == ExternalSystemType.SHOPIFY:
            from app.services.shopify_service import ShopifyService

            shopify_service = ShopifyService(db)

            access_token = decrypted_credentials.get("access_token")
            if not access_token:
                logger.error(
                    f"❌ 缺少 access_token: external_system_id={external_system.id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Access Token not configured for this store",
                )

            # Test Shopify connection
            logger.info(f"🔍 开始测试 Shopify 连接: external_id={external_id}")
            result = await shopify_service.test_connection(tenant.id)

            if result["success"]:
                logger.info(f"✅ Shopify 连接测试成功: external_id={external_id}")
                return {
                    "success": True,
                    "message": "Shopify connection test successful",
                    "shop_info": result.get("shop_info", {}),
                    "details": {
                        "shop_id": external_id,
                        "base_url": external_system.base_url,
                        "system_type": "SHOPIFY",
                    },
                }
            else:
                logger.error(
                    f"❌ Shopify 连接测试失败: {result.get('message', 'Unknown error')}"
                )
                return {
                    "success": False,
                    "message": result.get("message", "Shopify connection test failed"),
                    "error_code": result.get("error_code", 500),
                }

        elif external_system.system_type == ExternalSystemType.PRINTIFY:
            from app.services.printify_service import PrintifyService

            access_token = decrypted_credentials.get("access_token")
            shop_id = decrypted_credentials.get("shop_id")

            if not access_token:
                logger.error(
                    f"❌ 缺少 access_token: external_system_id={external_system.id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Access Token not configured for this store",
                )

            if not shop_id:
                logger.error(
                    f"❌ 缺少 shop_id: external_system_id={external_system.id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Shop ID not configured for this store",
                )

            # Test Printify connection
            logger.info(f"🔍 开始测试 Printify 连接: external_id={external_id}")
            printify_service = PrintifyService(printify_api_token=access_token)
            result = await printify_service.test_connection()

            if result["success"]:
                logger.info(f"✅ Printify 连接测试成功: external_id={external_id}")
                return {
                    "success": True,
                    "message": "Printify connection test successful",
                    "details": {
                        "shop_id": shop_id,
                        "base_url": external_system.base_url,
                        "system_type": "PRINTIFY",
                    },
                }
            else:
                logger.error(
                    f"❌ Printify 连接测试失败: {result.get('message', 'Unknown error')}"
                )
                return {
                    "success": False,
                    "message": result.get("message", "Printify connection test failed"),
                    "error_code": result.get("error_code", 500),
                }
        else:
            logger.error(f"❌ 不支持的系统类型: {external_system.system_type.value}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported system type: {external_system.system_type.value}",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 外部系统测试连接请求处理失败: {str(e)}")
        import traceback

        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test connection: {str(e)}",
        )


@router.get("/shopify/{external_system_hashid}/products", response_model=dict)
async def get_shopify_products_by_shop_id(
    external_system_hashid: str,
    limit: int = 50,
    page: int = 1,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """Get Shopify products for a specific shop"""
    logger = get_logger(__name__)
    try:
        logger.info(
            f"🔍 开始处理 Shopify 商品列表请求: external_system_hashid={external_system_hashid}, limit={limit}, page={page}"
        )
        tenant, user = auth
        logger.info(
            f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}"
        )

        # Decode hashids to get external system ID
        from app.core.hashids_utils import decode_id

        try:
            external_system_id = decode_id(external_system_hashid)
            logger.info(
                f"✅ Hashids 解码成功: {external_system_hashid} -> {external_system_id}"
            )
        except Exception as e:
            logger.error(f"❌ Hashids 解码失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid external system ID",
            )

        # Get external system by internal ID
        service = ExternalSystemService(db)
        external_system = await service.get_external_system(
            external_system_id, tenant.id
        )
        if not external_system:
            logger.error(
                f"❌ 未找到 Shopify 店铺: external_system_id={external_system_id}, tenant_id={tenant.id}"
            )
            raise HTTPException(status_code=404, detail="Shopify store not found")

        logger.info(
            f"✅ 找到 Shopify 店铺: id={external_system.id}, name={external_system.name}"
        )

        # Get decrypted credentials
        decrypted_credentials = await service.get_decrypted_credentials(
            external_system.id, tenant.id
        )
        if not decrypted_credentials:
            logger.error(
                f"❌ 无法获取解密后的凭据: external_system_id={external_system.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get decrypted credentials",
            )
        logger.info(f"✅ 凭据解密成功: external_system_id={external_system.id}")

        access_token = decrypted_credentials.get("access_token")
        if not access_token:
            logger.error(
                f"❌ 缺少 access_token: external_system_id={external_system.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access Token not configured for this store",
            )

        # Initialize Shopify service and get products
        from app.services.shopify_service import ShopifyService

        shopify_service = ShopifyService(db)

        logger.info(
            f"🔍 开始获取 Shopify 商品: external_system_id={external_system_id}"
        )
        products_response = await shopify_service.get_products(
            shop_id=external_system.external_system_id,  # Use the external system's shop_id
            access_token=access_token,
            api_version=external_system.settings.get("api_version", "2024-10"),
        )

        if not products_response.get("success", False):
            logger.error(
                f"❌ Shopify 商品获取失败: {products_response.get('error', 'Unknown error')}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=products_response.get("error", "Failed to get products"),
            )

        logger.info(
            f"✅ Shopify 商品获取成功: 数量={len(products_response.get('products', []))}"
        )

        return {
            "success": True,
            "products": products_response.get("products", []),
            "count": len(products_response.get("products", [])),
            "pagination": {
                "limit": limit,
                "page": page,
                "has_more": products_response.get("has_more", False),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Shopify 商品列表请求处理失败: {str(e)}")
        import traceback

        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get products: {str(e)}",
        )


@router.get("/shopify/{external_system_hashid}/orders", response_model=dict)
async def get_shopify_orders_by_shop_id(
    external_system_hashid: str,
    limit: int = 50,
    page: int = 1,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """Get Shopify orders for a specific shop"""
    logger = get_logger(__name__)
    try:
        logger.info(
            f"🔍 开始处理 Shopify 订单列表请求: external_system_hashid={external_system_hashid}, limit={limit}, page={page}"
        )
        tenant, user = auth
        logger.info(
            f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}"
        )

        # Decode hashids to get external system ID
        from app.core.hashids_utils import decode_id

        try:
            external_system_id = decode_id(external_system_hashid)
            logger.info(
                f"✅ Hashids 解码成功: {external_system_hashid} -> {external_system_id}"
            )
        except Exception as e:
            logger.error(f"❌ Hashids 解码失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid external system ID",
            )

        # Get external system by internal ID
        service = ExternalSystemService(db)
        external_system = await service.get_external_system(
            external_system_id, tenant.id
        )
        if not external_system:
            logger.error(
                f"❌ 未找到 Shopify 店铺: external_system_id={external_system_id}, tenant_id={tenant.id}"
            )
            raise HTTPException(status_code=404, detail="Shopify store not found")

        logger.info(
            f"✅ 找到 Shopify 店铺: id={external_system.id}, name={external_system.name}"
        )

        # Get decrypted credentials
        decrypted_credentials = await service.get_decrypted_credentials(
            external_system.id, tenant.id
        )
        if not decrypted_credentials:
            logger.error(
                f"❌ 无法获取解密后的凭据: external_system_id={external_system.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get decrypted credentials",
            )
        logger.info(f"✅ 凭据解密成功: external_system_id={external_system.id}")

        access_token = decrypted_credentials.get("access_token")
        if not access_token:
            logger.error(
                f"❌ 缺少 access_token: external_system_id={external_system.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access Token not configured for this store",
            )

        # Initialize Shopify service and get orders
        from app.services.shopify_service import ShopifyService

        shopify_service = ShopifyService(db)

        # Get the actual Shopify shop_id from external_system
        shop_id = external_system.external_system_id
        logger.info(f"🔍 开始获取 Shopify 订单: shop_id={shop_id}, external_system_id={external_system_id}")
        orders_response = await shopify_service.get_orders(
            shop_id=shop_id,
            access_token=access_token,
            api_version=external_system.settings.get("api_version", "2024-10"),
        )

        if not orders_response.get("success", False):
            logger.error(
                f"❌ Shopify 订单获取失败: {orders_response.get('error', 'Unknown error')}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=orders_response.get("error", "Failed to get orders"),
            )

        logger.info(
            f"✅ Shopify 订单获取成功: 数量={len(orders_response.get('orders', []))}"
        )

        return {
            "success": True,
            "orders": orders_response.get("orders", []),
            "count": len(orders_response.get("orders", [])),
            "pagination": {
                "limit": limit,
                "page": page,
                "has_more": orders_response.get("has_more", False),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Shopify 订单列表请求处理失败: {str(e)}")
        import traceback

        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get orders: {str(e)}",
        )


@router.get("/shopify/{shop_id}/orders/{order_id}", response_model=dict)
async def get_shopify_order_details(
    shop_id: str,
    order_id: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """Get detailed information for a specific Shopify order"""
    logger = get_logger(__name__)
    try:
        logger.info(
            f"🔍 开始处理 Shopify 订单详情请求: shop_id={shop_id}, order_id={order_id}"
        )
        tenant, user = auth
        logger.info(
            f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}"
        )

        # Get external system by shop_id (external_id)
        service = ExternalSystemService(db)
        external_system = await service.get_external_system_by_external_system_id(
            shop_id, tenant.id
        )
        if not external_system:
            logger.error(
                f"❌ 未找到 Shopify 店铺: shop_id={shop_id}, tenant_id={tenant.id}"
            )
            raise HTTPException(status_code=404, detail="Shopify store not found")

        logger.info(
            f"✅ 找到 Shopify 店铺: id={external_system.id}, name={external_system.name}"
        )

        # Get decrypted credentials
        decrypted_credentials = await service.get_decrypted_credentials(
            external_system.id, tenant.id
        )
        if not decrypted_credentials:
            logger.error(
                f"❌ 无法获取解密后的凭据: external_system_id={external_system.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get decrypted credentials",
            )
        logger.info(f"✅ 凭据解密成功: external_system_id={external_system.id}")

        access_token = decrypted_credentials.get("access_token")
        if not access_token:
            logger.error(
                f"❌ 缺少 access_token: external_system_id={external_system.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access Token not configured for this store",
            )

        # Initialize Shopify service and get order details
        from app.services.shopify_service import ShopifyService

        shopify_service = ShopifyService(db)

        logger.info(
            f"🔍 开始获取 Shopify 订单详情: shop_id={shop_id}, order_id={order_id}"
        )
        order_response = await shopify_service.get_order_details(
            shop_id=shop_id,
            order_id=order_id,
            access_token=access_token,
            api_version=external_system.settings.get("api_version", "2024-10"),
        )

        if not order_response.get("success", False):
            logger.error(
                f"❌ Shopify 订单详情获取失败: {order_response.get('error', 'Unknown error')}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=order_response.get("error", "Failed to get order details"),
            )

        logger.info(f"✅ Shopify 订单详情获取成功: order_id={order_id}")

        return {
            "success": True,
            "order": order_response.get("order", {}),
            "details": {
                "shop_id": shop_id,
                "order_id": order_id,
                "base_url": external_system.base_url,
                "system_type": "SHOPIFY",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Shopify 订单详情请求处理失败: {str(e)}")
        import traceback

        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get order details: {str(e)}",
        )


@router.get(
    "/shopify/{external_system_hashid}/products/{product_id}/json", response_model=dict
)
async def get_shopify_product_json(
    external_system_hashid: str,
    product_id: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """Get complete Shopify product JSON data"""
    logger = get_logger(__name__)
    try:
        logger.info(
            f"🔍 开始获取 Shopify 商品完整 JSON 数据: external_system_hashid={external_system_hashid}, product_id={product_id}"
        )
        tenant, user = auth
        logger.info(
            f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}"
        )

        # Decode hashids to get external system ID
        from app.core.hashids_utils import decode_id

        try:
            external_system_id = decode_id(external_system_hashid)
            logger.info(
                f"✅ Hashids 解码成功: {external_system_hashid} -> {external_system_id}"
            )
        except Exception as e:
            logger.error(f"❌ Hashids 解码失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid external system ID",
            )

        # Get external system by internal ID
        service = ExternalSystemService(db)
        external_system = await service.get_external_system(
            external_system_id, tenant.id
        )
        if not external_system:
            logger.error(
                f"❌ 未找到 Shopify 店铺: external_system_id={external_system_id}, tenant_id={tenant.id}"
            )
            raise HTTPException(status_code=404, detail="Shopify store not found")

        logger.info(
            f"✅ 找到 Shopify 店铺: id={external_system.id}, name={external_system.name}"
        )

        # Get decrypted credentials
        decrypted_credentials = await service.get_decrypted_credentials(
            external_system.id, tenant.id
        )
        if not decrypted_credentials:
            logger.error(
                f"❌ 无法获取解密后的凭据: external_system_id={external_system.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get decrypted credentials",
            )
        logger.info(f"✅ 凭据解密成功: external_system_id={external_system.id}")

        access_token = decrypted_credentials.get("access_token")
        if not access_token:
            logger.error(
                f"❌ 缺少 access_token: external_system_id={external_system.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access Token not configured for this store",
            )

        # Initialize Shopify service and get product JSON
        from app.services.shopify_service import ShopifyService

        shopify_service = ShopifyService(db)

        logger.info(
            f"🔍 开始获取 Shopify 商品完整 JSON: external_system_id={external_system_id}, product_id={product_id}"
        )
        product_response = await shopify_service.get_product_json(
            shop_id=external_system.external_system_id,  # Use the external system's shop_id
            product_id=product_id,
            access_token=access_token,
            api_version=external_system.settings.get("api_version", "2024-10"),
        )

        if not product_response.get("success", False):
            logger.error(
                f"❌ Shopify 商品 JSON 获取失败: {product_response.get('error', 'Unknown error')}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=product_response.get("error", "Failed to get product JSON"),
            )

        logger.info(f"✅ Shopify 商品 JSON 获取成功: product_id={product_id}")

        return {
            "success": True,
            "product": product_response.get("product", {}),
            "details": {
                "shop_id": external_system.external_system_id,  # Use the external system's shop_id
                "product_id": product_id,
                "base_url": external_system.base_url,
                "system_type": "SHOPIFY",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Shopify 商品 JSON 请求处理失败: {str(e)}")
        import traceback

        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get product JSON: {str(e)}",
        )


@router.get("/shopify/{external_system_hashid}/orders/{order_id}/json", response_model=dict)
async def get_shopify_order_json_by_hashid(
    external_system_hashid: str,
    order_id: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """获取 Shopify 订单的完整 JSON 数据（使用 hashid）"""
    logger = get_logger(__name__)
    tenant, user = auth
    logger.info(
        f"🔍 开始处理 Shopify 订单 JSON 请求: external_system_hashid={external_system_hashid}, order_id={order_id}"
    )

    try:
        logger.info(
            f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}"
        )

        # Decode hashids to get external system ID
        from app.core.hashids_utils import decode_id

        try:
            external_system_id = decode_id(external_system_hashid)
            logger.info(
                f"✅ Hashids 解码成功: {external_system_hashid} -> {external_system_id}"
            )
        except Exception as e:
            logger.error(
                f"❌ Hashids 解码失败: {external_system_hashid}, 错误: {str(e)}"
            )
            raise HTTPException(status_code=400, detail="Invalid external system ID")

        # Get external system by primary key
        service = ExternalSystemService(db)
        external_system = await service.get_external_system(
            external_system_id, tenant.id
        )
        if not external_system:
            logger.error(
                f"❌ 未找到 Shopify 店铺: external_system_id={external_system_id}, tenant_id={tenant.id}"
            )
            raise HTTPException(status_code=404, detail="Shopify store not found")

        logger.info(
            f"✅ 找到 Shopify 店铺: id={external_system.id}, name={external_system.name}, external_id={external_system.external_id}"
        )

        # Get decrypted credentials
        decrypted_credentials = await service.get_decrypted_credentials(
            external_system.id, tenant.id
        )
        if not decrypted_credentials:
            logger.error(
                f"❌ 无法获取解密后的凭据: external_system_id={external_system.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get decrypted credentials",
            )
        logger.info(f"✅ 凭据解密成功: external_system_id={external_system.id}")

        access_token = decrypted_credentials.get("access_token")
        if not access_token:
            logger.error(
                f"❌ 缺少 access_token: external_system_id={external_system.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access Token not configured for this store",
            )

        # Initialize Shopify service and get order JSON
        from app.services.shopify_service import ShopifyService

        shopify_service = ShopifyService(db)

        # Resolve shop_id: external_id 可能为空，从 base_url 或凭据 store_url 解析
        shop_id = external_system.external_id
        if not shop_id and external_system.base_url:
            base_url = (external_system.base_url or "").strip()
            if base_url.startswith("https://"):
                shop_id = base_url.replace("https://", "").split(".myshopify.com")[0].strip()
            else:
                shop_id = base_url.split(".myshopify.com")[0].strip() if ".myshopify.com" in base_url else None
        if not shop_id and decrypted_credentials:
            shop_id = (
                decrypted_credentials.get("store_url")
                or decrypted_credentials.get("shop_domain")
                or decrypted_credentials.get("shop_id")
            )
            if shop_id and ".myshopify.com" in str(shop_id):
                shop_id = str(shop_id).replace("https://", "").split(".myshopify.com")[0].strip()
        if not shop_id:
            logger.error(
                f"❌ 无法解析 Shopify 店铺域名: external_id={external_system.external_id}, base_url={external_system.base_url}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shop domain not configured. Set external_id or base_url (e.g. https://your-store.myshopify.com) for this Shopify store.",
            )
        logger.info(
            f"🔍 开始获取 Shopify 订单 JSON: shop_id={shop_id}, order_id={order_id}"
        )
        order_json_response = await shopify_service.get_order_json(
            shop_id=shop_id,
            order_id=order_id,
            access_token=access_token,
        )

        # Check if get_order_json returned an error
        if not order_json_response.get("success", False):
            error_msg = order_json_response.get("error", "Unknown error")
            logger.error(f"❌ Shopify 订单 JSON 获取失败: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get order JSON: {error_msg}",
            )

        # Extract the actual order data from the response
        order_json = order_json_response.get("order")
        if not order_json:
            logger.error(f"❌ Shopify 订单 JSON 数据为空: order_id={order_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Order data is empty",
            )

        logger.info(f"✅ Shopify 订单 JSON 获取成功: order_id={order_id}")

        return {
            "success": True,
            "order": order_json,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Shopify 订单 JSON 请求处理失败: {str(e)}")
        import traceback

        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get order JSON: {str(e)}",
        )


@router.get("/shopify/{shop_id}/orders/{order_id}/json", response_model=dict)
async def get_shopify_order_json(
    shop_id: str,
    order_id: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """获取 Shopify 订单的完整 JSON 数据（使用 shop_id/external_id）"""
    logger = get_logger(__name__)
    tenant, user = auth
    logger.info(
        f"🔍 开始处理 Shopify 订单 JSON 请求: shop_id={shop_id}, order_id={order_id}"
    )

    try:
        logger.info(
            f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}"
        )

        # Get external system by shop_id (external_id)
        service = ExternalSystemService(db)
        external_system = await service.get_external_system_by_external_system_id(
            shop_id, tenant.id
        )
        if not external_system:
            logger.error(
                f"❌ 未找到 Shopify 店铺: shop_id={shop_id}, tenant_id={tenant.id}"
            )
            raise HTTPException(status_code=404, detail="Shopify store not found")

        logger.info(
            f"✅ 找到 Shopify 店铺: id={external_system.id}, name={external_system.name}"
        )

        # Get decrypted credentials
        decrypted_credentials = await service.get_decrypted_credentials(
            external_system.id, tenant.id
        )
        if not decrypted_credentials:
            logger.error(
                f"❌ 无法获取解密后的凭据: external_system_id={external_system.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get decrypted credentials",
            )
        logger.info(f"✅ 凭据解密成功: external_system_id={external_system.id}")

        access_token = decrypted_credentials.get("access_token")
        if not access_token:
            logger.error(
                f"❌ 缺少 access_token: external_system_id={external_system.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access Token not configured for this store",
            )

        # Initialize Shopify service and get order JSON
        from app.services.shopify_service import ShopifyService

        shopify_service = ShopifyService(db)

        logger.info(
            f"🔍 开始获取 Shopify 订单 JSON: shop_id={shop_id}, order_id={order_id}"
        )
        order_json = await shopify_service.get_order_json(
            shop_id=shop_id,
            order_id=order_id,
            access_token=access_token,
        )

        logger.info(f"✅ Shopify 订单 JSON 获取成功: order_id={order_id}")

        return {
            "success": True,
            "order": order_json,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Shopify 订单 JSON 请求处理失败: {str(e)}")
        import traceback

        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get order JSON: {str(e)}",
        )


@router.get("/shopify/{external_system_hashid}/products/{product_id}/check-mapping", response_model=dict)
async def check_shopify_product_mapping(
    external_system_hashid: str,
    product_id: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """Check if a Shopify product variants have been mapped to core product variants"""
    logger = get_logger(__name__)
    
    try:
        logger.info(f"🔍 检查Shopify商品变体映射: external_system_hashid={external_system_hashid}, product_id={product_id}")
        tenant, user = auth
        logger.info(f"✅ 认证成功: tenant_id={tenant.id}, user_id={user.id}")
        
        # Decode hashids to get external system ID
        from app.core.hashids_utils import decode_id
        
        try:
            external_system_id = decode_id(external_system_hashid)
            logger.info(f"✅ Hashids 解码成功: {external_system_hashid} -> {external_system_id}")
        except Exception as e:
            logger.error(f"❌ Hashids 解码失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid external system ID",
            )
        
        # Get external system
        service = ExternalSystemService(db)
        external_system = await service.get_external_system(
            external_system_id, tenant.id
        )
        
        if not external_system:
            logger.error(f"❌ 未找到外部系统: external_system_id={external_system_id}")
            raise HTTPException(status_code=404, detail="Store not found")
        
        logger.info(f"✅ 找到外部系统: external_system_id={external_system.id}")
        
        # Import here to avoid circular imports
        from app.models.product import ProductMapping, Product, ProductVariant
        from app.core.hashids_utils import encode_id
        from sqlalchemy import select, or_
        from sqlalchemy.orm import selectinload
        
        # Query product mapping for this product (both product-level and variant-level mappings)
        stmt = select(ProductMapping).where(
            ProductMapping.tenant_id == tenant.id,
            ProductMapping.external_system_id == external_system.id,
            or_(
                ProductMapping.external_product_id == product_id,
                ProductMapping.external_product_id.like(f"{product_id}%")  # For variant mappings
            )
        ).options(
            selectinload(ProductMapping.core_product).selectinload(Product.variants),
            selectinload(ProductMapping.core_variant)
        )
        
        result = await db.execute(stmt)
        mappings = result.scalars().all()
        
        logger.info(f"✅ 查询映射结果: 找到{len(mappings)}个映射")
        
        if not mappings:
            return {
                "is_mapped": False,
                "message": "该Shopify商品及其变体尚未映射到核心商品",
                "mappings": [],
                "variant_mappings": []
            }
        
        # Separate product-level and variant-level mappings
        product_mappings = []
        variant_mappings = []
        
        for mapping in mappings:
            core_product = mapping.core_product
            core_variant = mapping.core_variant
            
            mapping_info = {
                "id_hashid": encode_id(mapping.id),
                "external_product_id": mapping.external_product_id,
                "external_variant_id": mapping.external_variant_id,
                "mapping_type": mapping.mapping_type,
                "sync_direction": mapping.sync_direction,
                "sync_status": mapping.sync_status,
                "last_synced_at": mapping.last_synced_at.isoformat() if mapping.last_synced_at else None,
                "created_at": mapping.created_at.isoformat() if mapping.created_at else None,
                "core_product": {
                    "id_hashid": encode_id(core_product.id) if core_product else None,
                    "title": core_product.title if core_product else None,
                    "handle": core_product.handle if core_product else None,
                    "product_type": core_product.product_type if core_product else None,
                    "vendor": core_product.vendor if core_product else None,
                    "status": core_product.status if core_product else None,
                    "variant_count": len(core_product.variants) if core_product and core_product.variants else 0
                } if core_product else None,
                "core_variant": {
                    "id_hashid": encode_id(core_variant.id) if core_variant else None,
                    "title": core_variant.title if core_variant else None,
                    "sku": core_variant.sku if core_variant else None,
                    "price": str(core_variant.price) if core_variant and core_variant.price else None,
                    "inventory_quantity": core_variant.inventory_quantity if core_variant else None,
                    "weight": str(core_variant.weight) if core_variant and core_variant.weight else None,
                    "weight_unit": core_variant.weight_unit if core_variant else None
                } if core_variant else None
            }
            
            # Categorize mappings
            if mapping.external_variant_id:
                variant_mappings.append(mapping_info)
            else:
                product_mappings.append(mapping_info)
        
        total_mappings = len(product_mappings) + len(variant_mappings)
        
        logger.info(f"✅ 成功检查商品映射: 商品映射={len(product_mappings)}, 变体映射={len(variant_mappings)}")
        
        return {
            "is_mapped": total_mappings > 0,
            "message": f"该Shopify商品已映射到{len(product_mappings)}个核心商品，{len(variant_mappings)}个变体已映射",
            "mapping_count": total_mappings,
            "product_mapping_count": len(product_mappings),
            "variant_mapping_count": len(variant_mappings),
            "mappings": product_mappings,
            "variant_mappings": variant_mappings
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 检查商品映射失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check product mapping: {str(e)}",
        )
