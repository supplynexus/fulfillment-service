"""
External system management API endpoints
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.tenant_auth_dependency import verify_tenant_auth
from app.core.logging import get_logger
from app.models.tenant import Tenant
from app.models.user import User
from app.models.external_system import ExternalSystem, ExternalSystemType
from app.services.external_system_service import ExternalSystemService
from app.schemas.external_system import (
    ExternalSystemCreate,
    ExternalSystemUpdate,
    ExternalSystemResponse,
    ExternalSystemListResponse,
    ExternalSystemSecureResponse,
    ExternalSystemSecureListResponse
)

router = APIRouter()


@router.post("/", response_model=ExternalSystemResponse)
async def create_external_system(
    external_system_data: ExternalSystemCreate,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> Any:
    """
    Create a new external system integration
    """
    tenant, user = auth
    
    service = ExternalSystemService(db)
    
    try:
        system_type = ExternalSystemType(external_system_data.system_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid system type: {external_system_data.system_type}"
        )
    
    external_system = await service.create_external_system(
        tenant_id=tenant.id,
        system_type=system_type,
        name=external_system_data.name,
        external_system_id=external_system_data.external_system_id,
        credentials=external_system_data.credentials,
        base_url=external_system_data.base_url,
        webhook_url=external_system_data.webhook_url,
        settings=external_system_data.settings
    )
    
    return external_system


@router.get("/", response_model=ExternalSystemSecureListResponse)
async def get_external_systems(
    system_type: Optional[str] = Query(None, description="Filter by system type"),
    active_only: bool = Query(True, description="Show only active systems"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> Any:
    """
    Get external systems for the authenticated tenant
    """
    logger = get_logger(__name__)
    
    try:
        logger.info(f"🔍 开始处理外部系统列表请求: system_type={system_type}, active_only={active_only}, skip={skip}, limit={limit}")
        
        tenant, user = auth
        logger.info(f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}")
        
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
                    detail=f"Invalid system type: {system_type}"
                )
        
        logger.info(f"🔍 查询外部系统: tenant_id={tenant.id}, system_type={system_type_enum}, active_only={active_only}")
        try:
            external_systems = await service.get_external_systems_by_tenant(
                tenant_id=tenant.id,
                system_type=system_type_enum,
                active_only=active_only
            )
            logger.info(f"✅ 查询外部系统成功: 找到 {len(external_systems)} 个系统")
        except Exception as e:
            logger.error(f"❌ 查询外部系统失败: {str(e)}")
            import traceback
            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Failed to get external systems: {str(e)}")
        
        # Apply pagination
        total = len(external_systems)
        external_systems = external_systems[skip:skip + limit]
        logger.info(f"✅ 分页处理完成: total={total}, 返回={len(external_systems)}")
        
        # Decrypt credentials for each external system and add hashids
        from app.core.security import decrypt_data
        from app.core.hashids_utils import encode_id, decode_id
        decrypted_systems = []
        for system in external_systems:
            # Debug: Test encode_id function
            try:
                encoded_id = encode_id(system.id)
                logger.info(f"🔍 Hashids 编码测试: id={system.id} -> hashid={encoded_id}")
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
                    logger.warning(f"Failed to decrypt credential {key} for system {system.id}: {e}")
                    decrypted_credentials[key] = ""  # Use empty string if decryption fails
            
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
            external_systems=decrypted_systems,
            total=total,
            skip=skip,
            limit=limit
        )

        logger.info(f"✅ 外部系统列表请求处理成功: total={total}, skip={skip}, limit={limit}")
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
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> Any:
    """
    Get specific external system
    """
    tenant, user = auth
    
    service = ExternalSystemService(db)
    external_system = await service.get_external_system(external_system_id, tenant.id)
    
    if not external_system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="External system not found"
        )
    
    return external_system


@router.put("/{external_system_id}", response_model=ExternalSystemResponse)
async def update_external_system(
    external_system_id: int,
    external_system_data: ExternalSystemUpdate,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> Any:
    """
    Update external system
    """
    tenant, user = auth
    
    service = ExternalSystemService(db)
    
    # Convert system_type string to enum if provided
    system_type_enum = None
    if external_system_data.system_type:
        try:
            system_type_enum = ExternalSystemType(external_system_data.system_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid system type: {external_system_data.system_type}"
            )
    
    # Prepare update data
    update_data = external_system_data.dict(exclude_unset=True)
    if system_type_enum:
        update_data["system_type"] = system_type_enum
    
    external_system = await service.update_external_system(
        external_system_id=external_system_id,
        tenant_id=tenant.id,
        **update_data
    )
    
    if not external_system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="External system not found"
        )
    
    return external_system


@router.delete("/{external_system_id}")
async def delete_external_system(
    external_system_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> Any:
    """
    Delete external system (soft delete)
    """
    tenant, user = auth
    
    service = ExternalSystemService(db)
    success = await service.delete_external_system(external_system_id, tenant.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="External system not found"
        )
    
    return {"message": "External system deleted successfully"}


@router.post("/printify/test-connection", response_model=dict)
async def test_printify_connection(
    request_data: dict,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> Any:
    """
    Test Printify connection using provided credentials
    """
    logger = get_logger(__name__)
    
    try:
        logger.info(f"🔍 开始处理 Printify 测试连接请求")
        
        tenant, user = auth
        logger.info(f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}")
        
        # Extract credentials from request
        encrypted_access_token = request_data.get('access_token')
        encrypted_shop_id = request_data.get('shop_id')
        base_url = request_data.get('base_url', 'https://api.printify.com')
        
        logger.info(f"🔍 提取的加密凭据: shop_id={encrypted_shop_id}, base_url={base_url}, has_access_token={bool(encrypted_access_token)}")
        
        if not encrypted_access_token or not encrypted_shop_id:
            logger.error(f"❌ 缺少必要参数: access_token={bool(encrypted_access_token)}, shop_id={bool(encrypted_shop_id)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required parameters: access_token and shop_id"
            )
        
        # Handle credentials - try to decrypt first, if fails use as plain text (for test connection)
        from app.core.security import decrypt_data
        try:
            # Try to decrypt first (for saved stores)
            access_token = decrypt_data(encrypted_access_token)
            shop_id = decrypt_data(encrypted_shop_id)
            logger.info(f"✅ 凭据解密成功: shop_id={shop_id}, has_access_token={bool(access_token)}")
        except Exception as e:
            # If decryption fails, use as plain text (for test connection from dialog)
            logger.info(f"ℹ️ 凭据解密失败，使用明文凭据进行测试连接: {str(e)}")
            access_token = encrypted_access_token
            shop_id = encrypted_shop_id
            logger.info(f"✅ 使用明文凭据: shop_id={shop_id}, has_access_token={bool(access_token)}")
        
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
                detail=f"Printify connection test failed: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Printify 测试连接请求处理失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/printify/{external_system_hashid}/products", response_model=dict)
async def get_printify_products(
    external_system_hashid: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> Any:
    """
    Get products from Printify store by external system ID (hashid)
    """
    logger = get_logger(__name__)
    
    try:
        logger.info(f"🔍 开始处理 Printify 商品列表请求: external_system_hashid={external_system_hashid}")
        
        tenant, user = auth
        logger.info(f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}")
        
        # Decode hashid to get external system ID
        from app.core.hashids_utils import decode_id
        try:
            external_system_id = decode_id(external_system_hashid)
            if not external_system_id:
                logger.error(f"❌ 无效的 hashid: {external_system_hashid}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid external system ID"
                )
            logger.info(f"✅ hashid 解码成功: {external_system_hashid} -> {external_system_id}")
        except Exception as e:
            logger.error(f"❌ hashid 解码失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to decode external system ID"
            )
        
        # Get external system by ID
        service = ExternalSystemService(db)
        external_system = await service.get_external_system(external_system_id, tenant.id)
        
        if not external_system:
            logger.error(f"❌ 未找到外部系统: external_system_id={external_system_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="External system not found"
            )
        
        if external_system.system_type != ExternalSystemType.PRINTIFY:
            logger.error(f"❌ 外部系统类型错误: expected=PRINTIFY, actual={external_system.system_type}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="External system is not a Printify store"
            )
        
        # Get decrypted credentials
        decrypted_credentials = await service.get_decrypted_credentials(external_system.id, tenant.id)
        if not decrypted_credentials:
            logger.error(f"❌ 无法获取解密后的凭据: external_system_id={external_system.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get decrypted credentials"
            )
        
        access_token = decrypted_credentials.get("access_token")
        shop_id = decrypted_credentials.get("shop_id")
        
        if not access_token:
            logger.error(f"❌ 缺少 access_token: external_system_id={external_system.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access Token not configured for this store"
            )
        
        if not shop_id:
            logger.error(f"❌ 缺少 shop_id: external_system_id={external_system.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shop ID not configured for this store"
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
            "message": "Products retrieved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Printify 商品列表请求处理失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get products: {str(e)}"
        )


@router.get("/printify/{external_system_hashid}/orders", response_model=dict)
async def get_printify_orders(
    external_system_hashid: str,
    limit: int = 50,
    page: int = 1,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> Any:
    """Get Printify orders for a specific store"""
    logger = get_logger(__name__)
    try:
        logger.info(f"🔍 开始处理 Printify 订单列表请求: external_system_hashid={external_system_hashid}, limit={limit}, page={page}")
        tenant, user = auth
        logger.info(f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}")
        
        # Decode hashids to get external_system_id
        from app.core.hashids_utils import decode_id
        try:
            external_system_id = decode_id(external_system_hashid)
            logger.info(f"✅ Hashids 解码成功: {external_system_hashid} -> {external_system_id}")
        except Exception as e:
            logger.error(f"❌ Hashids 解码失败: {external_system_hashid}, 错误: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid external system ID")
        
        # Get external system by primary key
        service = ExternalSystemService(db)
        external_system = await service.get_external_system(external_system_id, tenant.id)
        if not external_system:
            logger.error(f"❌ 未找到外部系统: external_system_id={external_system_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="External system not found")
        
        logger.info(f"✅ 找到外部系统: id={external_system.id}, name={external_system.name}, system_type={external_system.system_type}")
        
        # Get decrypted credentials
        decrypted_credentials = await service.get_decrypted_credentials(external_system.id, tenant.id)
        if not decrypted_credentials:
            logger.error(f"❌ 无法获取解密后的凭据: external_system_id={external_system.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get decrypted credentials"
            )
        logger.info(f"✅ 凭据解密成功: external_system_id={external_system.id}")
        
        access_token = decrypted_credentials.get("access_token")
        shop_id = decrypted_credentials.get("shop_id")
        
        if not access_token:
            logger.error(f"❌ 缺少 access_token: external_system_id={external_system.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access Token not configured for this store"
            )
        
        if not shop_id:
            logger.error(f"❌ 缺少 shop_id: external_system_id={external_system.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shop ID not configured for this store"
            )
        
        # Get orders using PrintifyService
        from app.services.printify_service import PrintifyService
        printify_service = PrintifyService(printify_api_token=access_token)
        
        logger.info(f"🔍 开始调用 Printify API 获取订单列表: shop_id={shop_id}, limit={limit}, page={page}")
        orders_result = await printify_service.get_orders(shop_id, limit, page)
        
        if not orders_result.get("success"):
            logger.error(f"❌ Printify API 返回错误: {orders_result}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=orders_result.get("message", "Failed to get orders from Printify")
            )
        
        orders = orders_result.get("orders", [])
        logger.info(f"✅ Printify 订单列表获取成功: 数量={len(orders)}")
        
        return {
            "success": True,
            "external_system_id": external_system_hashid,
            "shop_id": shop_id,
            "orders": orders,
            "total_count": orders_result.get("total_count", 0),
            "current_page": orders_result.get("current_page", page),
            "per_page": orders_result.get("per_page", limit),
            "has_more": orders_result.get("has_more", False),
            "message": "Orders retrieved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Printify 订单列表请求处理失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get orders: {str(e)}"
        )


@router.post("/shopify/{shop_id}/sync-orders", response_model=dict)
async def sync_shopify_orders_by_shop_id(
    shop_id: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> Any:
    """Sync Shopify orders for a specific shop"""
    logger = get_logger(__name__)
    try:
        logger.info(f"🔍 开始处理 Shopify 订单同步请求: shop_id={shop_id}")
        tenant, user = auth
        logger.info(f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}")
        
        # Get external system by shop_id (external_id)
        service = ExternalSystemService(db)
        external_system = await service.get_external_system_by_external_id(shop_id, tenant.id)
        if not external_system:
            logger.error(f"❌ 未找到 Shopify 店铺: shop_id={shop_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="Shopify store not found")
        
        logger.info(f"✅ 找到 Shopify 店铺: id={external_system.id}, name={external_system.name}")
        
        # Get decrypted credentials
        decrypted_credentials = await service.get_decrypted_credentials(external_system.id, tenant.id)
        if not decrypted_credentials:
            logger.error(f"❌ 无法获取解密后的凭据: external_system_id={external_system.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get decrypted credentials"
            )
        logger.info(f"✅ 凭据解密成功: external_system_id={external_system.id}")
        
        access_token = decrypted_credentials.get("access_token")
        if not access_token:
            logger.error(f"❌ 缺少 access_token: external_system_id={external_system.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access Token not configured for this store"
            )
        
        # Initialize Shopify service and sync orders
        from app.services.shopify_service import ShopifyService
        shopify_service = ShopifyService(db)
        
        logger.info(f"🔍 开始同步 Shopify 订单: shop_id={shop_id}")
        result = await shopify_service.sync_orders_to_database(
            shop_id=shop_id,
            access_token=access_token,
            tenant_id=tenant.id,
            external_system_id=external_system.id,
            api_version=external_system.settings.get('api_version', '2024-10')
        )
        
        if not result["success"]:
            logger.error(f"❌ Shopify 订单同步失败: {result.get('message', 'Unknown error')}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "Failed to sync orders")
            )
        
        logger.info(f"✅ Shopify 订单同步成功: 新增 {result.get('orders_synced', 0)} 个订单，更新 {result.get('orders_updated', 0)} 个订单")
        
        return {
            "success": True,
            "message": result.get("message", "Orders synced successfully"),
            "orders_synced": result.get("orders_synced", 0),
            "orders_updated": result.get("orders_updated", 0),
            "total_processed": result.get("total_processed", 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Shopify 订单同步请求处理失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync orders: {str(e)}"
        )


@router.post("/by-external-id/{external_id}/test-connection", response_model=dict)
async def test_connection_by_external_id(
    external_id: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> Any:
    """Test connection for external system by external_id"""
    logger = get_logger(__name__)
    try:
        logger.info(f"🔍 开始处理外部系统测试连接请求: external_id={external_id}")
        tenant, user = auth
        logger.info(f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}")
        
        # Get external system by external_id
        service = ExternalSystemService(db)
        external_system = await service.get_external_system_by_external_id(external_id, tenant.id)
        if not external_system:
            logger.error(f"❌ 未找到外部系统: external_id={external_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="External system not found")
        
        logger.info(f"✅ 找到外部系统: id={external_system.id}, name={external_system.name}, system_type={external_system.system_type}")
        
        # Get decrypted credentials
        decrypted_credentials = await service.get_decrypted_credentials(external_system.id, tenant.id)
        if not decrypted_credentials:
            logger.error(f"❌ 无法获取解密后的凭据: external_system_id={external_system.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get decrypted credentials"
            )
        logger.info(f"✅ 凭据解密成功: external_system_id={external_system.id}")
        
        # Test connection based on system type
        if external_system.system_type.value == "shopify":
            from app.services.shopify_service import ShopifyService
            shopify_service = ShopifyService(db)
            
            access_token = decrypted_credentials.get("access_token")
            if not access_token:
                logger.error(f"❌ 缺少 access_token: external_system_id={external_system.id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Access Token not configured for this store"
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
                        "system_type": "SHOPIFY"
                    }
                }
            else:
                logger.error(f"❌ Shopify 连接测试失败: {result.get('message', 'Unknown error')}")
                return {
                    "success": False,
                    "message": result.get("message", "Shopify connection test failed"),
                    "error_code": result.get("error_code", 500)
                }
                
        elif external_system.system_type.value == "printify":
            from app.services.printify_service import PrintifyService
            
            access_token = decrypted_credentials.get("access_token")
            shop_id = decrypted_credentials.get("shop_id")
            
            if not access_token:
                logger.error(f"❌ 缺少 access_token: external_system_id={external_system.id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Access Token not configured for this store"
                )
            
            if not shop_id:
                logger.error(f"❌ 缺少 shop_id: external_system_id={external_system.id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Shop ID not configured for this store"
                )
            
            # Test Printify connection
            logger.info(f"🔍 开始测试 Printify 连接: external_id={external_id}")
            printify_service = PrintifyService(access_token=access_token, shop_id=shop_id)
            result = await printify_service.test_connection()
            
            if result["success"]:
                logger.info(f"✅ Printify 连接测试成功: external_id={external_id}")
                return {
                    "success": True,
                    "message": "Printify connection test successful",
                    "details": {
                        "shop_id": shop_id,
                        "base_url": external_system.base_url,
                        "system_type": "PRINTIFY"
                    }
                }
            else:
                logger.error(f"❌ Printify 连接测试失败: {result.get('message', 'Unknown error')}")
                return {
                    "success": False,
                    "message": result.get("message", "Printify connection test failed"),
                    "error_code": result.get("error_code", 500)
                }
        else:
            logger.error(f"❌ 不支持的系统类型: {external_system.system_type.value}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported system type: {external_system.system_type.value}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 外部系统测试连接请求处理失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test connection: {str(e)}"
        )


@router.get("/shopify/{shop_id}/products", response_model=dict)
async def get_shopify_products_by_shop_id(
    shop_id: str,
    limit: int = 50,
    page: int = 1,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> Any:
    """Get Shopify products for a specific shop"""
    logger = get_logger(__name__)
    try:
        logger.info(f"🔍 开始处理 Shopify 商品列表请求: shop_id={shop_id}, limit={limit}, page={page}")
        tenant, user = auth
        logger.info(f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}")
        
        # Get external system by shop_id (external_id)
        service = ExternalSystemService(db)
        external_system = await service.get_external_system_by_external_id(shop_id, tenant.id)
        if not external_system:
            logger.error(f"❌ 未找到 Shopify 店铺: shop_id={shop_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="Shopify store not found")
        
        logger.info(f"✅ 找到 Shopify 店铺: id={external_system.id}, name={external_system.name}")
        
        # Get decrypted credentials
        decrypted_credentials = await service.get_decrypted_credentials(external_system.id, tenant.id)
        if not decrypted_credentials:
            logger.error(f"❌ 无法获取解密后的凭据: external_system_id={external_system.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get decrypted credentials"
            )
        logger.info(f"✅ 凭据解密成功: external_system_id={external_system.id}")
        
        access_token = decrypted_credentials.get("access_token")
        if not access_token:
            logger.error(f"❌ 缺少 access_token: external_system_id={external_system.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access Token not configured for this store"
            )
        
        # Initialize Shopify service and get products
        from app.services.shopify_service import ShopifyService
        shopify_service = ShopifyService(db)
        
        logger.info(f"🔍 开始获取 Shopify 商品: shop_id={shop_id}")
        products_response = await shopify_service.get_products(
            shop_id=shop_id,
            access_token=access_token,
            api_version=external_system.settings.get('api_version', '2024-10')
        )
        
        if not products_response.get("success", False):
            logger.error(f"❌ Shopify 商品获取失败: {products_response.get('error', 'Unknown error')}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=products_response.get("error", "Failed to get products")
            )
        
        logger.info(f"✅ Shopify 商品获取成功: 数量={len(products_response.get('products', []))}")
        
        return {
            "success": True,
            "products": products_response.get("products", []),
            "count": len(products_response.get("products", [])),
            "pagination": {
                "limit": limit,
                "page": page,
                "has_more": products_response.get("has_more", False)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Shopify 商品列表请求处理失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get products: {str(e)}"
        )


@router.get("/shopify/{shop_id}/orders", response_model=dict)
async def get_shopify_orders_by_shop_id(
    shop_id: str,
    limit: int = 50,
    page: int = 1,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> Any:
    """Get Shopify orders for a specific shop"""
    logger = get_logger(__name__)
    try:
        logger.info(f"🔍 开始处理 Shopify 订单列表请求: shop_id={shop_id}, limit={limit}, page={page}")
        tenant, user = auth
        logger.info(f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}")
        
        # Get external system by shop_id (external_id)
        service = ExternalSystemService(db)
        external_system = await service.get_external_system_by_external_id(shop_id, tenant.id)
        if not external_system:
            logger.error(f"❌ 未找到 Shopify 店铺: shop_id={shop_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="Shopify store not found")
        
        logger.info(f"✅ 找到 Shopify 店铺: id={external_system.id}, name={external_system.name}")
        
        # Get decrypted credentials
        decrypted_credentials = await service.get_decrypted_credentials(external_system.id, tenant.id)
        if not decrypted_credentials:
            logger.error(f"❌ 无法获取解密后的凭据: external_system_id={external_system.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get decrypted credentials"
            )
        logger.info(f"✅ 凭据解密成功: external_system_id={external_system.id}")
        
        access_token = decrypted_credentials.get("access_token")
        if not access_token:
            logger.error(f"❌ 缺少 access_token: external_system_id={external_system.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access Token not configured for this store"
            )
        
        # Initialize Shopify service and get orders
        from app.services.shopify_service import ShopifyService
        shopify_service = ShopifyService(db)
        
        logger.info(f"🔍 开始获取 Shopify 订单: shop_id={shop_id}")
        orders_response = await shopify_service.get_orders(
            shop_id=shop_id,
            access_token=access_token,
            api_version=external_system.settings.get('api_version', '2024-10')
        )
        
        if not orders_response.get("success", False):
            logger.error(f"❌ Shopify 订单获取失败: {orders_response.get('error', 'Unknown error')}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=orders_response.get("error", "Failed to get orders")
            )
        
        logger.info(f"✅ Shopify 订单获取成功: 数量={len(orders_response.get('orders', []))}")
        
        return {
            "success": True,
            "orders": orders_response.get("orders", []),
            "count": len(orders_response.get("orders", [])),
            "pagination": {
                "limit": limit,
                "page": page,
                "has_more": orders_response.get("has_more", False)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Shopify 订单列表请求处理失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get orders: {str(e)}"
        )


