"""
External system management API endpoints
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.api_key_auth import require_permission
from app.models.api_key import ApiKey
from app.models.tenant import Tenant
from app.models.external_system import ExternalSystem, ExternalSystemType
from app.services.external_system_service import ExternalSystemService
from app.schemas.external_system import (
    ExternalSystemCreate,
    ExternalSystemUpdate,
    ExternalSystemResponse,
    ExternalSystemListResponse
)

router = APIRouter()


@router.post("/external-systems", response_model=ExternalSystemResponse)
async def create_external_system(
    external_system_data: ExternalSystemCreate,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[ApiKey, Tenant] = Depends(require_permission("external_systems:write"))
) -> Any:
    """
    Create a new external system integration
    """
    api_key, tenant = auth
    
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
        credentials=external_system_data.credentials,
        base_url=external_system_data.base_url,
        webhook_url=external_system_data.webhook_url,
        settings=external_system_data.settings
    )
    
    return external_system


@router.get("/external-systems", response_model=ExternalSystemListResponse)
async def get_external_systems(
    system_type: Optional[str] = Query(None, description="Filter by system type"),
    active_only: bool = Query(True, description="Show only active systems"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[ApiKey, Tenant] = Depends(require_permission("external_systems:read"))
) -> Any:
    """
    Get external systems for the authenticated tenant
    """
    api_key, tenant = auth
    
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


@router.get("/external-systems/{external_system_id}", response_model=ExternalSystemResponse)
async def get_external_system(
    external_system_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[ApiKey, Tenant] = Depends(require_permission("external_systems:read"))
) -> Any:
    """
    Get specific external system
    """
    api_key, tenant = auth
    
    service = ExternalSystemService(db)
    external_system = await service.get_external_system(external_system_id, tenant.id)
    
    if not external_system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="External system not found"
        )
    
    return external_system


@router.put("/external-systems/{external_system_id}", response_model=ExternalSystemResponse)
async def update_external_system(
    external_system_id: int,
    external_system_data: ExternalSystemUpdate,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[ApiKey, Tenant] = Depends(require_permission("external_systems:write"))
) -> Any:
    """
    Update external system
    """
    api_key, tenant = auth
    
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


@router.delete("/external-systems/{external_system_id}")
async def delete_external_system(
    external_system_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[ApiKey, Tenant] = Depends(require_permission("external_systems:write"))
) -> Any:
    """
    Delete external system (soft delete)
    """
    api_key, tenant = auth
    
    service = ExternalSystemService(db)
    success = await service.delete_external_system(external_system_id, tenant.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="External system not found"
        )
    
    return {"message": "External system deleted successfully"}



