"""
Shopify Stores API endpoints
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.jwt_auth_dependency import verify_jwt_auth

router = APIRouter()


@router.get("/stores", response_model=dict)
async def get_shopify_stores(
    db: AsyncSession = Depends(get_async_db), auth: tuple = Depends(verify_jwt_auth)
) -> Any:
    """
    Get Shopify stores list for the authenticated tenant
    """
    try:
        tenant, user = auth
        tenant_id = tenant.id

        # Import here to avoid circular imports
        from app.services.external_system_service import ExternalSystemService

        # Get Shopify stores for the tenant
        external_system_service = ExternalSystemService(db)
        stores = await external_system_service.get_shopify_stores(tenant_id=tenant_id)

        # Format the response
        stores_data = []
        for store in stores:
            stores_data.append(
                {
                    "id": store.id,
                    "name": store.name,
                    "display_name": store.name,  # Use name as display_name
                    "description": f"Shopify store: {store.external_system_id}",  # Generate description
                    "is_active": store.is_active,
                    "external_id": store.external_system_id,  # Use external_system_id as external_id for frontend compatibility
                    "external_system_id": store.external_system_id,
                    "base_url": store.base_url,
                    "created_at": (
                        store.created_at.isoformat() if store.created_at else None
                    ),
                    "updated_at": (
                        store.updated_at.isoformat() if store.updated_at else None
                    ),
                }
            )

        return {"success": True, "stores": stores_data, "count": len(stores_data)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Shopify stores: {str(e)}",
        )
