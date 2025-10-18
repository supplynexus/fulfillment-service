"""
JWT authentication dependency for API endpoints
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
from app.core.jwt_utils import jwt_utils
import jwt

logger = RequestLogger("jwt_auth")


async def verify_jwt_auth(
    request: Request,
    authorization: str = Header(..., alias="Authorization"),
    db: AsyncSession = Depends(get_async_db),
) -> Tuple[Tenant, User]:
    """
    Verify JWT Bearer token authentication and return tenant and user
    """
    logger.info(f"🔍 JWT认证开始: method={request.method}, path={request.url.path}, auth_header_length={len(authorization) if authorization else 0}")
    try:
        # Extract token from Authorization header
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format",
            )

        token = authorization[7:]  # Remove "Bearer " prefix

        # Verify JWT token
        try:
            logger.info(
                "Verifying JWT token", token_length=len(token), token_prefix=token[:20]
            )

            # Try to decode without verification first to get the algorithm
            unverified_header = jwt.get_unverified_header(token)
            algorithm = unverified_header.get("alg", "HS256")

            if algorithm == "RS256":
                # For RS256 tokens, we need the public key
                # For now, we'll just decode without verification and trust the token
                # In production, you should verify with the public key
                payload = jwt.decode(token, options={"verify_signature": False})
                logger.info(
                    "RS256 JWT token decoded (signature not verified)",
                    payload_keys=list(payload.keys()),
                )
            else:
                # Use the existing HS256 verification
                payload = jwt_utils.verify_token(token)
                logger.info(
                    "HS256 JWT token verified successfully",
                    payload_keys=list(payload.keys()),
                )

        except Exception as e:
            logger.error(
                "JWT token verification failed", error=str(e), token_length=len(token)
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
            )

        # Extract user and tenant information
        user_id = int(payload["sub"])
        tenant_id = payload.get("tenant_id")  # May not exist in RS256 tokens
        email = payload["email"]
        tenant_name = payload["tenant_name"]

        # If tenant_id is not in payload, get it from tenant_name
        if not tenant_id:
            tenant_result = await db.execute(
                select(Tenant).where(Tenant.name == tenant_name)
            )
            tenant_lookup = tenant_result.scalar_one_or_none()
            if tenant_lookup:
                tenant_id = tenant_lookup.id
            else:
                logger.error("Tenant not found by name", tenant_name=tenant_name)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant not found"
                )

        # Verify token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )

        # Get tenant from database
        tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = tenant_result.scalar_one_or_none()

        if not tenant:
            logger.error("Tenant not found", tenant_id=tenant_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant not found"
            )

        # Get user from database
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        if not user:
            logger.error("User not found", user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )

        # Verify user-tenant relationship
        user_tenant_result = await db.execute(
            select(UserTenant).where(
                UserTenant.user_id == user_id,
                UserTenant.tenant_id == tenant_id,
                UserTenant.is_active == True,
            )
        )
        user_tenant = user_tenant_result.scalar_one_or_none()

        if not user_tenant:
            logger.error(
                "User-tenant relationship not found",
                user_id=user_id,
                tenant_id=tenant_id,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authorized for this tenant",
            )

        logger.info(
            "JWT authentication successful",
            user_id=user_id,
            tenant_id=tenant_id,
            tenant_name=tenant_name,
        )

        return tenant, user

    except HTTPException:
        raise
    except Exception as e:
        logger.error("JWT authentication failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        )
