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
    Smart authentication selector - always uses timestamp signature authentication
    """
    
    # Always use timestamp signature authentication
    signature = request.headers.get("X-Signature")
    
    if not signature:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required authentication header: X-Signature",
            headers={"WWW-Authenticate": "TimestampSignature"},
        )
    
    return await get_timestamp_auth(request, db)


async def get_smart_auth(
    auth: Tuple[User, Tenant] = Depends(smart_auth_selector)
) -> Tuple[User, Tenant]:
    """Dependency for smart authentication"""
    return auth
