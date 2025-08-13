"""
Shopify orders API endpoints
"""

from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.timestamp_auth_middleware import verify_timestamp_auth
from app.services.shopify_service import ShopifyService
from app.schemas.order import OrderResponse, OrderListResponse

router = APIRouter()


@router.post("/shopify/sync-orders", response_model=dict)
async def sync_shopify_orders(
    tenant_id: int = Query(..., description="Tenant ID"),
    limit: int = Query(10, ge=1, le=100, description="Number of orders to sync"),
    db: AsyncSession = Depends(get_async_db),
    auth: dict = Depends(verify_timestamp_auth)
) -> Any:
    """
    Sync orders from Shopify
    """
    try:
        # Verify tenant access
        if auth.get("tenant_id") != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
        
        # Initialize Shopify service
        shopify_service = ShopifyService(db)
        
        # Sync orders
        result = await shopify_service.sync_orders(tenant_id, limit)
        
        # Close service
        await shopify_service.close()
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"]
            )
        
        return {
            "success": True,
            "message": result["message"],
            "orders_processed": result["orders_processed"],
            "total_fetched": result["total_fetched"],
            "errors": result.get("errors", [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error syncing Shopify orders: {str(e)}"
        )


@router.get("/shopify/orders", response_model=dict)
async def fetch_shopify_orders(
    tenant_id: int = Query(..., description="Tenant ID"),
    limit: int = Query(10, ge=1, le=100, description="Number of orders to fetch"),
    db: AsyncSession = Depends(get_async_db),
    auth: dict = Depends(verify_timestamp_auth)
) -> Any:
    """
    Fetch orders from Shopify (without saving to database)
    """
    try:
        # Verify tenant access
        if auth.get("tenant_id") != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
        
        # Initialize Shopify service
        shopify_service = ShopifyService(db)
        
        # Fetch orders
        orders = await shopify_service.fetch_orders(tenant_id, limit)
        
        # Close service
        await shopify_service.close()
        
        return {
            "success": True,
            "orders": orders,
            "count": len(orders)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching Shopify orders: {str(e)}"
        )


@router.get("/shopify/test-connection", response_model=dict)
async def test_shopify_connection(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_db),
    auth: dict = Depends(verify_timestamp_auth)
) -> Any:
    """
    Test Shopify connection and configuration
    """
    try:
        # Verify tenant access
        if auth.get("tenant_id") != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
        
        # Initialize Shopify service
        shopify_service = ShopifyService(db)
        
        # Get Shopify system configuration
        shopify_system = await shopify_service.get_shopify_system(tenant_id)
        
        if not shopify_system:
            return {
                "success": False,
                "message": "No active Shopify system found for this tenant",
                "configuration": None
            }
        
        # Test connection by fetching a single order
        orders = await shopify_service.fetch_orders(tenant_id, limit=1)
        
        # Close service
        await shopify_service.close()
        
        return {
            "success": True,
            "message": "Shopify connection successful",
            "configuration": {
                "system_id": shopify_system.id,
                "name": shopify_system.name,
                "base_url": shopify_system.base_url,
                "external_id": shopify_system.external_id,
                "is_active": shopify_system.is_active,
                "sync_enabled": shopify_system.sync_enabled,
                "webhook_enabled": shopify_system.webhook_enabled
            },
            "test_result": {
                "orders_fetched": len(orders),
                "connection_working": len(orders) >= 0  # True if no error occurred
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Shopify connection failed: {str(e)}",
            "configuration": None
        }
