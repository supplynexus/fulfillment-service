"""
Timestamp signature authentication demo endpoints
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.timestamp_auth_middleware import get_timestamp_auth
from app.core.timestamp_auth import TimestampAuthService
from app.models.user import User
from app.models.tenant import Tenant

router = APIRouter()


@router.get("/timestamp-auth-demo/secure-endpoint")
async def secure_endpoint(
    auth: tuple[User, Tenant] = Depends(get_timestamp_auth)
) -> Any:
    """
    Secure endpoint that requires timestamp-based signature authentication
    """
    user, tenant = auth
    
    return {
        "message": "Access granted with timestamp signature authentication",
        "user_id": user.id,
        "user_email": user.email,
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
        "authentication_method": "timestamp_signature"
    }


@router.post("/timestamp-auth-demo/create-signature")
async def create_signature_demo(
    method: str = "GET",
    path: str = "/api/v1/timestamp-auth-demo/secure-endpoint",
    body: str = "",
    db: AsyncSession = Depends(get_async_db)
) -> Any:
    """
    Demo endpoint to show how to create a system signature
    This would be used by our system when making requests to external systems
    """
    
    auth_service = TimestampAuthService(db)
    
    try:
        signature_data = await auth_service.create_system_signature(
            method=method,
            path=path,
            body=body
        )
        
        return {
            "message": "System signature created successfully",
            "signature_data": signature_data,
            "headers_to_include": {
                "X-Signature": signature_data["signature"],
                "X-Timestamp": signature_data["timestamp"],
                "X-Nonce": signature_data["nonce"],
                "X-Key-ID": signature_data["key_id"]
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create signature: {str(e)}"
        )


@router.get("/timestamp-auth-demo/public-key")
async def get_system_public_key(
    db: AsyncSession = Depends(get_async_db)
) -> Any:
    """
    Get system's public key for signature verification
    External systems would use this to verify our signatures
    """
    
    from sqlalchemy import select
    from app.models.system_key import SystemKey, SystemKeyType
    
    # Get current API signing key
    result = await db.execute(
        select(SystemKey).where(
            SystemKey.key_type == SystemKeyType.API_SIGNING,
            SystemKey.is_current == True,
            SystemKey.is_active == True
        )
    )
    system_key = result.scalar_one_or_none()
    
    if not system_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active API signing key found"
        )
    
    return {
        "key_id": system_key.key_id,
        "public_key": system_key.public_key,
        "key_type": system_key.key_type_algorithm,
        "key_size": system_key.key_size,
        "created_at": system_key.created_at
    }
