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
    key_id = request.headers.get("X-Key-ID")  # Required for production
    
    if not all([signature, timestamp, nonce]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required authentication headers: X-Signature, X-Timestamp, X-Nonce",
            headers={"WWW-Authenticate": "TimestampSignature"},
        )
    
    # Key ID is required in production
    if not key_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Key-ID header is required for signature verification",
            headers={"WWW-Authenticate": "TimestampSignature"},
        )
    
    try:
        timestamp_int = int(timestamp)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid timestamp format",
            headers={"WWW-Authenticate": "TimestampSignature"},
        )
    
    # Verify signature and get user/tenant
    auth_service = TimestampAuthService(db)
    user, tenant = await auth_service.verify_timestamp_signature(
        request=request,
        signature=signature,
        timestamp=timestamp_int,
        nonce=nonce,
        key_id=key_id
    )
    
    # User and tenant are already returned from signature verification
    return user, tenant


async def get_timestamp_auth(
    auth: Tuple[User, Tenant] = Depends(verify_timestamp_auth)
) -> Tuple[User, Tenant]:
    """Dependency for timestamp-based authentication"""
    return auth
