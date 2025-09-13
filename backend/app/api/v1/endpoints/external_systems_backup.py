"""
External system management API endpoints
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.tenant_auth_dependency import verify_tenant_auth
from app.models.tenant import Tenant
from app.models.user import User
from app.models.external_system import ExternalSystem, ExternalSystemType
from app.services.external_system_service import ExternalSystemService
from app.schemas.external_system import (
    ExternalSystemCreate,
    ExternalSystemUpdate,
    ExternalSystemResponse,
    ExternalSystemListResponse
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


@router.get("/", response_model=ExternalSystemListResponse)
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
    tenant, user = auth
    
    service = ExternalSystemService(db)
    
    # Convert system_type string to enum if provided
    system_type_enum = None
    if system_type:
        try:
            system_type_enum = ExternalSystemType(system_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid system type: {system_type}"
            )
    
    external_systems = await service.get_external_systems_by_tenant(
        tenant_id=tenant.id,
        system_type=system_type_enum,
        active_only=active_only
    )
    
    # Apply pagination
    total = len(external_systems)
    external_systems = external_systems[skip:skip + limit]
    
    return {
        "external_systems": external_systems,
        "total": total,
        "skip": skip,
        "limit": limit
    }


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


@router.post("/shopify/test-connection")
async def test_shopify_connection_with_params(
    request_data: dict,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> Any:
    """
    Test Shopify connection with direct parameters (shop_id, access_token, etc.)
    """
    tenant, user = auth
    
    # Extract parameters from request
    shop_id = request_data.get("shop_id")
    access_token = request_data.get("access_token")
    api_version = request_data.get("api_version", "2024-10")
    
    # Validate required parameters
    if not shop_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="shop_id is required"
        )
    
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="access_token is required"
        )
    
    # Auto-generate base_url from shop_id
    base_url = f"https://{shop_id}.myshopify.com"
    
    # Test connection using ShopifyService
    from app.services.shopify_service import ShopifyService
    shopify_service = ShopifyService(db)
    
    try:
        result = await shopify_service.test_connection_with_params(
            shop_id=shop_id,
            access_token=access_token,
            base_url=base_url,
            api_version=api_version
        )
        await shopify_service.close()
        
        if result["success"]:
            return {
                "success": True,
                "message": "Connection test successful",
                "system_type": "SHOPIFY",
                "shop_id": shop_id,
                "shop_info": result.get("shop_info", {})
            }
        else:
            return {
                "success": False,
                "message": result.get("error", "Connection test failed"),
                "system_type": "SHOPIFY",
                "shop_id": shop_id
            }
            
    except Exception as e:
        await shopify_service.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Connection test failed: {str(e)}"
        )


@router.post("/{external_system_id}/test-connection")
async def test_external_system_connection(
    external_system_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> Any:
    """
    Test connection to external system
    """
    tenant, user = auth
    
    service = ExternalSystemService(db)
    external_system = await service.get_external_system(external_system_id, tenant.id)
    
    if not external_system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="External system not found"
        )
    
    # Test connection based on system type
    if external_system.system_type == ExternalSystemType.SHOPIFY:
        from app.services.shopify_service import ShopifyService
        shopify_service = ShopifyService(db)
        
        try:
            # Test Shopify connection by fetching shop info
            result = await shopify_service.test_connection(tenant.id, external_system_id)
            await shopify_service.close()
            
            if result["success"]:
                return {
                    "success": True,
                    "message": "Connection test successful",
                    "system_type": "SHOPIFY",
                    "shop_info": result.get("shop_info", {})
                }
            else:
                return {
                    "success": False,
                    "message": result.get("error", "Connection test failed"),
                    "system_type": "SHOPIFY"
                }
                
        except Exception as e:
            await shopify_service.close()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Connection test failed: {str(e)}"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connection testing not supported for system type: {external_system.system_type}"
        )


@router.post("/by-external-id/{external_id}/test-connection")
async def test_external_system_connection_by_external_id(
    external_id: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> Any:
    """
    Test connection to external system by external_id (shop_name) with tenant isolation
    """
    tenant, user = auth
    
    service = ExternalSystemService(db)
    external_system = await service.get_external_system_by_external_id(external_id, tenant.id)
    
    if not external_system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="External system not found"
        )
    
    # Test connection based on system type
    if external_system.system_type == ExternalSystemType.SHOPIFY:
        from app.services.shopify_service import ShopifyService
        shopify_service = ShopifyService(db)
        
        try:
            # Test Shopify connection by fetching shop info
            result = await shopify_service.test_connection(tenant.id, external_system.id)
            await shopify_service.close()
            
            if result["success"]:
                return {
                    "success": True,
                    "message": "Connection test successful",
                    "system_type": "SHOPIFY",
                    "external_id": external_id,
                    "shop_info": result.get("shop_info", {})
                }
            else:
                return {
                    "success": False,
                    "message": result.get("error", "Connection test failed"),
                    "system_type": "SHOPIFY",
                    "external_id": external_id
                }
                
        except Exception as e:
            await shopify_service.close()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Connection test failed: {str(e)}"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connection testing not supported for system type: {external_system.system_type}"
        )

