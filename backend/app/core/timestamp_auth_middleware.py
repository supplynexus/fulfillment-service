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
    timestamp = request.headers.get("X-Timestamp")
    nonce = request.headers.get("X-Nonce")
    user_id = request.headers.get("X-User-ID")
    key_id = request.headers.get("X-Key-ID")  # Optional
    
    if not all([signature, timestamp, nonce, user_id]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required authentication headers: X-Signature, X-Timestamp, X-Nonce, X-User-ID",
            headers={"WWW-Authenticate": "TimestampSignature"},
        )
    
    try:
        timestamp_int = int(timestamp)
        user_id_int = int(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid timestamp or user ID format",
            headers={"WWW-Authenticate": "TimestampSignature"},
        )
    
    # Verify signature
    auth_service = TimestampAuthService(db)
    is_valid = await auth_service.verify_timestamp_signature(
        request=request,
        signature=signature,
        timestamp=timestamp_int,
        nonce=nonce,
        user_id=user_id_int,
        key_id=key_id
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
    
    # Get user's active tenant (you might want to get this from the request or token)
    user_tenant_result = await db.execute(
        select(UserTenant).where(
            UserTenant.user_id == user_id_int,
            UserTenant.is_active == True
        ).limit(1)
    )
    user_tenant = user_tenant_result.scalar_one_or_none()
    
    if not user_tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User has no active tenant",
            headers={"WWW-Authenticate": "TimestampSignature"},
        )
    
    # Get user and tenant
    user_result = await db.execute(
        select(User).where(User.id == user_id_int)
    )
    user = user_result.scalar_one_or_none()
    
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == user_tenant.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    
    if not user or not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User or tenant not found",
            headers={"WWW-Authenticate": "TimestampSignature"},
        )
    
    return user, tenant


async def get_timestamp_auth(
    auth: Tuple[User, Tenant] = Depends(verify_timestamp_auth)
) -> Tuple[User, Tenant]:
    """Dependency for timestamp-based authentication"""
    return auth
