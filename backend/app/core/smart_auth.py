"""
Smart authentication selector - automatically chooses authentication method
"""

from typing import Tuple, Optional
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.timestamp_auth_middleware import get_timestamp_auth
from app.core.dev_auth import get_dev_auth
from app.core.config import settings
from app.models.user import User
from app.models.tenant import Tenant


async def smart_auth_selector(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> Tuple[User, Tenant]:
    """
    Smart authentication selector that chooses the appropriate auth method
    based on environment and request headers
    """
    
    # Check if development headers are present
    dev_user_id = request.headers.get("X-Dev-User-ID")
    dev_tenant_id = request.headers.get("X-Dev-Tenant-ID")
    
    # Check if timestamp signature headers are present
    signature = request.headers.get("X-Signature")
    timestamp = request.headers.get("X-Timestamp")
    nonce = request.headers.get("X-Nonce")
    user_id = request.headers.get("X-User-ID")
    
    # Development mode with dev headers
    if settings.DEBUG and dev_user_id and dev_tenant_id:
        return await get_dev_auth(request, db)
    
    # Production mode with timestamp signature
    elif signature and timestamp and nonce and user_id:
        return await get_timestamp_auth(request, db)
    
    # Fallback: try development auth if in debug mode
    elif settings.DEBUG:
        return await get_dev_auth(request, db)
    
    else:
        # No valid authentication found
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No valid authentication method found. In development, use X-Dev-User-ID and X-Dev-Tenant-ID headers. In production, use timestamp signature authentication.",
            headers={"WWW-Authenticate": "SmartAuth"},
        )


async def get_smart_auth(
    auth: Tuple[User, Tenant] = Depends(smart_auth_selector)
) -> Tuple[User, Tenant]:
    """Dependency for smart authentication"""
    return auth
