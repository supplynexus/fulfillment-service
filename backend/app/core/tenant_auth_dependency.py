"""
Tenant authentication dependency for business API endpoints
"""

from typing import Tuple
from fastapi import Depends, HTTPException, status, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_async_db
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_tenant import UserTenant
from app.core.logging import RequestLogger
from app.api.v1.endpoints.auth import verify_tenant_signature

logger = RequestLogger("tenant_auth")


async def verify_tenant_auth(
    request: Request,
    x_signature: str = Header(..., alias="X-Signature"),
    x_tenant_name: str = Header(..., alias="X-Tenant-Name"),
    x_timestamp: str = Header(..., alias="X-Timestamp"),
    x_nonce: str = Header(..., alias="X-Nonce"),
    db: AsyncSession = Depends(get_async_db)
) -> Tuple[Tenant, User]:
    """
    Verify tenant signature authentication and return tenant and user
    """
    try:
        logger.info(f"Tenant auth attempt - tenant_name: {x_tenant_name}, timestamp: {x_timestamp}, nonce: {x_nonce}")
        
        # Get request body for signature verification
        body = await request.body()
        body_str = body.decode('utf-8') if body else ""
        
        # Create signature string
        method = request.method.upper()
        path = request.url.path
        signature_string = f"{method}{path}{x_timestamp}{x_nonce}{x_tenant_name}{body_str}"
        
        logger.info(f"🔍 签名验证调试信息: tenant_name={x_tenant_name}, method={method}, path={path}, timestamp={x_timestamp}, nonce={x_nonce}, body_length={len(body_str)}, signature_string_length={len(signature_string)}, x_signature_length={len(x_signature)}")
        
        # Verify signature
        if not await verify_tenant_signature(x_signature, signature_string, x_tenant_name, db):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        logger.info("Signature verified successfully")
        
        # Get tenant by name
        result = await db.execute(select(Tenant).where(Tenant.name == x_tenant_name))
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        if not tenant.is_active:
            raise HTTPException(status_code=401, detail="Tenant is inactive")
        
        # For now, we'll return a system user or create a mock user
        # In a real implementation, you might want to get the actual user from the signature
        # For simplicity, we'll use a system user approach
        
        # Get or create system user for this tenant
        system_user_result = await db.execute(
            select(User).where(User.email == "system@supplynexus.store")
        )
        system_user = system_user_result.scalar_one_or_none()
        
        if not system_user:
            # Create system user if it doesn't exist
            from app.services.user_service import UserService
            user_service = UserService(db)
            system_user = await user_service.create_system_user()
        
        logger.info(f"Tenant authenticated successfully - tenant_id: {tenant.id}, tenant_name: {tenant.name}, user_id: {system_user.id}")
        
        return tenant, system_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tenant auth error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


def require_tenant_auth():
    """Factory function that returns tenant authentication dependency"""
    return verify_tenant_auth
