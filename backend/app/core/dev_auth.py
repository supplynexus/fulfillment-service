"""
Development environment simplified authentication
"""

from typing import Optional, Tuple
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_async_db
from app.models.user import User
from app.models.tenant import Tenant
from app.models.user_tenant import UserTenant
from app.core.config import settings


async def dev_auth_bypass(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> Tuple[User, Tenant]:
    """
    Development environment authentication bypass
    Only works when DEBUG=True and specific headers are present
    """
    
    # Only allow in development
    if settings.ENVIRONMENT not in ["dev", "development", "local"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Development authentication not allowed in production"
        )
    
    # Check for development headers
    dev_user_id = request.headers.get("X-Dev-User-ID")
    dev_tenant_id = request.headers.get("X-Dev-Tenant-ID")
    
    if not dev_user_id or not dev_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Development headers required: X-Dev-User-ID, X-Dev-Tenant-ID"
        )
    
    try:
        user_id = int(dev_user_id)
        tenant_id = int(dev_tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID or tenant ID format"
        )
    
    # Get user
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get tenant
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Verify user has access to this tenant
    user_tenant_result = await db.execute(
        select(UserTenant).where(
            UserTenant.user_id == user.id,
            UserTenant.tenant_id == tenant.id,
            UserTenant.is_active == True
        )
    )
    user_tenant = user_tenant_result.scalar_one_or_none()
    
    if not user_tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to this tenant"
        )
    
    return user, tenant


async def get_dev_auth(
    auth: Tuple[User, Tenant] = Depends(dev_auth_bypass)
) -> Tuple[User, Tenant]:
    """Dependency for development authentication"""
    return auth
