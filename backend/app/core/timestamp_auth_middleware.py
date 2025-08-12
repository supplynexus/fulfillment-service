"""
Timestamp signature authentication middleware
"""

from typing import Optional, Tuple
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.timestamp_auth import TimestampAuthService
from app.models.user import User
from app.models.tenant import Tenant


async def verify_timestamp_auth(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> Tuple[User, Tenant]:
    """Verify timestamp-based signature authentication"""
    
    # Get authentication headers
    signature = request.headers.get("X-Signature")
    tenant_hashid = request.headers.get("X-Tenant-ID")
    
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required authentication header: X-Signature",
            headers={"WWW-Authenticate": "TimestampSignature"},
        )
    
    if not tenant_hashid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required authentication header: X-Tenant-ID",
            headers={"WWW-Authenticate": "TimestampSignature"},
        )
    
    # Verify signature and extract information
    auth_service = TimestampAuthService(db)
    is_valid, tenant_id, user_id, nonce, timestamp = await auth_service.verify_timestamp_signature(
        request=request,
        signature=signature,
        tenant_hashid=tenant_hashid
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
            headers={"WWW-Authenticate": "TimestampSignature"},
        )
    
    # Get user and tenant information
    # Note: In a real implementation, you might want to get this from the signature verification
    # For now, we'll get it from the database
    from sqlalchemy import select
    from app.models.user_tenant import UserTenant
    
    # Verify user has access to this tenant (if user_id provided)
    if user_id:
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
                headers={"WWW-Authenticate": "TimestampSignature"},
            )
    
    # Get user and tenant
    user = None
    if user_id:
        user_result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "TimestampSignature"},
            )
    
    # If no user_id provided, create a system user for frontend authentication
    if not user:
        user = User(
            id=0,  # System user ID
            email="frontend@supplynexus.store",
            hashed_password="",  # System user doesn't need password
            is_active=True
        )
    
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant not found",
            headers={"WWW-Authenticate": "TimestampSignature"},
        )
    
    return user, tenant


async def get_timestamp_auth(
    auth: Tuple[User, Tenant] = Depends(verify_timestamp_auth)
) -> Tuple[User, Tenant]:
    """Dependency for timestamp-based authentication"""
    return auth
