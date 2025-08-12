"""
Tenant-based authentication dependencies
"""

from typing import Optional, Tuple
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.timestamp_auth import TimestampAuthService
from app.models.tenant import Tenant
from app.models.user import User


async def verify_tenant_auth(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> Tenant:
    """Verify tenant-based authentication (no user required)"""
    
    # Get authentication header - only signature is required
    signature = request.headers.get("X-Signature")
    
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required authentication header: X-Signature",
            headers={"WWW-Authenticate": "TenantSignature"},
        )
    
    # Verify signature and extract information
    auth_service = TimestampAuthService(db)
    is_valid, tenant_id, user_id, nonce, timestamp = await auth_service.verify_timestamp_signature(
        request=request,
        signature=signature
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
            headers={"WWW-Authenticate": "TenantSignature"},
        )
    
    # Get tenant information
    from sqlalchemy import select
    
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant not found",
            headers={"WWW-Authenticate": "TenantSignature"},
        )
    
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant is inactive",
            headers={"WWW-Authenticate": "TenantSignature"},
        )
    
    return tenant


async def get_tenant_auth(
    tenant: Tenant = Depends(verify_tenant_auth)
) -> Tenant:
    """Dependency for tenant-based authentication"""
    return tenant


async def verify_tenant_user_auth(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> Tuple[User, Tenant]:
    """Verify tenant-based authentication with user (user required)"""
    
    # Get authentication header - only signature is required
    signature = request.headers.get("X-Signature")
    
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required authentication header: X-Signature",
            headers={"WWW-Authenticate": "TenantUserSignature"},
        )
    
    # Verify signature and extract information
    auth_service = TimestampAuthService(db)
    is_valid, tenant_id, user_id, nonce, timestamp = await auth_service.verify_timestamp_signature(
        request=request,
        signature=signature
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
            headers={"WWW-Authenticate": "TenantUserSignature"},
        )
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID required for this operation",
            headers={"WWW-Authenticate": "TenantUserSignature"},
        )
    
    # Get user and tenant information
    from sqlalchemy import select
    from app.models.user_tenant import UserTenant
    
    # Verify user has access to this tenant
    user_tenant_result = await db.execute(
        select(UserTenant).where(
            UserTenant.user_id == user_id,
            UserTenant.tenant_id == tenant_id,
            UserTenant.is_active == True
        ).limit(1)
    )
    user_tenant = user_tenant_result.scalar_one_or_none()
    
    if not user_tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User does not have access to this tenant",
            headers={"WWW-Authenticate": "TenantUserSignature"},
        )
    
    # Get user and tenant
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "TenantUserSignature"},
        )
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant not found",
            headers={"WWW-Authenticate": "TenantUserSignature"},
        )
    
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant is inactive",
            headers={"WWW-Authenticate": "TenantUserSignature"},
        )
    
    return user, tenant


async def get_tenant_user_auth(
    auth: Tuple[User, Tenant] = Depends(verify_tenant_user_auth)
) -> Tuple[User, Tenant]:
    """Dependency for tenant-user-based authentication"""
    return auth
