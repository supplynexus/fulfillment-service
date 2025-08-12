"""
Debug authentication endpoint
"""

from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.timestamp_auth import TimestampAuthService

router = APIRouter()


@router.get("/debug-auth/test")
async def debug_auth_test(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
):
    """Debug authentication test endpoint"""
    
    try:
        # Get headers
        signature = request.headers.get("X-Signature")
        tenant_id = request.headers.get("X-Tenant-ID")
        
        if not signature or not tenant_id:
            return {
                "error": "Missing headers",
                "signature": bool(signature),
                "tenant_id": bool(tenant_id)
            }
        
        # Create auth service
        auth_service = TimestampAuthService(db)
        
        # Try to verify signature
        try:
            is_valid, tenant_id_decoded, user_id, nonce, timestamp = await auth_service.verify_timestamp_signature(
                request=request,
                signature=signature,
                tenant_hashid=tenant_id
            )
            
            return {
                "success": True,
                "is_valid": is_valid,
                "tenant_id": tenant_id_decoded,
                "user_id": user_id,
                "nonce": nonce,
                "timestamp": timestamp
            }
            
        except HTTPException as e:
            return {
                "success": False,
                "error": e.detail,
                "error_type": "HTTPException",
                "status_code": e.status_code,
                "full_error": str(e),
                "traceback": str(e.__traceback__)
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
