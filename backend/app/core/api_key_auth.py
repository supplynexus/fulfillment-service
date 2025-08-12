"""
API Key authentication middleware
"""

import hashlib
import hmac
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_async_db
from app.core.redis_client import redis_client
from app.models.api_key import ApiKey, ApiKeyType
from app.models.tenant import Tenant


async def verify_api_key(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> tuple[ApiKey, Tenant]:
    """Verify API Key and return the key and tenant"""
    
    # Get API Key from header
    api_key = request.headers.get("X-API-Key")
    api_secret = request.headers.get("X-API-Secret")
    
    if not api_key or not api_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key and Secret are required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Try to get from cache first
    cached_key = await redis_client.get_cached_api_key(api_key)
    if cached_key:
        # Verify secret from cache
        if not hmac.compare_digest(
            hashlib.sha256(api_secret.encode()).hexdigest(),
            cached_key["secret_hash"]
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API Secret",
                headers={"WWW-Authenticate": "ApiKey"},
            )
        
        # Get tenant from cache or database
        tenant_result = await db.execute(
            select(Tenant).where(Tenant.id == cached_key["tenant_id"])
        )
        tenant = tenant_result.scalar_one_or_none()
        
        if not tenant or not tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tenant not found or inactive",
                headers={"WWW-Authenticate": "ApiKey"},
            )
        
        return cached_key, tenant
    
    # If not in cache, query database
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_id == api_key)
    )
    api_key_obj = result.scalar_one_or_none()
    
    if not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Verify secret
    if not hmac.compare_digest(
        hashlib.sha256(api_secret.encode()).hexdigest(),
        api_key_obj.secret_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Secret",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Check if key is active and not expired
    if not api_key_obj.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key is inactive",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Get tenant
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == api_key_obj.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    
    if not tenant or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant not found or inactive",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Cache the API key data
    key_data = {
        "id": api_key_obj.id,
        "tenant_id": api_key_obj.tenant_id,
        "key_type": api_key_obj.key_type.value,
        "permissions": api_key_obj.permissions,
        "secret_hash": api_key_obj.secret_hash,
        "rate_limit": api_key_obj.rate_limit,
        "allowed_ips": api_key_obj.allowed_ips
    }
    await redis_client.cache_api_key(api_key, key_data)
    
    return api_key_obj, tenant


async def get_api_key_auth(
    api_key_obj: ApiKey,
    tenant: Tenant = Depends(verify_api_key)
) -> tuple[ApiKey, Tenant]:
    """Dependency for API Key authentication"""
    return api_key_obj, tenant


async def require_permission(
    permission: str,
    api_key_obj: ApiKey,
    tenant: Tenant = Depends(verify_api_key)
) -> tuple[ApiKey, Tenant]:
    """Dependency that requires specific permission"""
    
    # Check if API key has the required permission
    if permission not in api_key_obj.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing permission: {permission}",
        )
    
    return api_key_obj, tenant


async def require_frontend_server_key(
    api_key_obj: ApiKey,
    tenant: Tenant = Depends(verify_api_key)
) -> tuple[ApiKey, Tenant]:
    """Dependency that requires frontend server API key"""
    
    if api_key_obj.key_type != ApiKeyType.FRONTEND_SERVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Frontend server API key required",
        )
    
    return api_key_obj, tenant
