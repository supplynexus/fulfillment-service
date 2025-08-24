"""
Authentication endpoints - Simplified version without JWT
"""

from typing import Any
import hashlib
import hmac
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_async_db
from app.core.logging import RequestLogger
from app.models.user import User
from app.models.tenant import Tenant
from app.schemas.auth import UserCreate, UserResponse
from app.services.user_service import UserService
from app.core.hashids_utils import hashids_encoder

router = APIRouter()


async def verify_tenant_signature(
    signature: str,
    message: str,
    tenant_name: str,
    db: AsyncSession
) -> bool:
    """
    验证租户签名
    """
    try:
        from sqlalchemy import select
        
        print(f"🔍 签名验证调试信息:")
        print(f"   tenant_name: {tenant_name}")
        print(f"   signature: {signature}")
        print(f"   message: {message}")
        print(f"   message_length: {len(message)}")
        
        # 获取租户信息和公钥
        tenant_result = await db.execute(
            select(Tenant).where(Tenant.name == tenant_name)
        )
        tenant = tenant_result.scalar_one_or_none()
        
        if not tenant:
            print(f"❌ 租户不存在: {tenant_name}")
            return False
        
        if not tenant.public_key:
            print(f"❌ 租户公钥不存在")
            return False
        
        print(f"✅ 从租户表获取公钥成功")
        print(f"   key_id: {tenant.key_id}")
        print(f"   key_type: {tenant.key_type}")
        
        # 加载公钥
        public_key = serialization.load_pem_public_key(
            tenant.public_key.encode('utf-8'),
            backend=default_backend()
        )
        
        print(f"✅ 公钥加载成功")
        
        # 解码签名
        signature_bytes = base64.b64decode(signature.encode('utf-8'))
        print(f"   signature_bytes_length: {len(signature_bytes)}")
        
        # 验证签名 - 使用 PKCS1v15 填充，与前端 RSA-SHA256 匹配
        public_key.verify(
            signature_bytes,
            message.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        print(f"✅ 签名验证成功")
        
        # 更新租户密钥使用统计（如果需要的话）
        # 这里可以添加租户密钥使用统计的逻辑
        await db.commit()
        
        return True
        
    except Exception as e:
        print(f"❌ 签名验证失败: {e}")
        print(f"   Exception type: {type(e).__name__}")
        return False


@router.post("/login/tenant")
async def login_tenant(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    tenant_name: str = Form(...),
    x_signature: str = Header(..., alias="X-Signature"),
    x_tenant_name: str = Header(..., alias="X-Tenant-Name"),
    x_timestamp: str = Header(..., alias="X-Timestamp"),
    x_nonce: str = Header(..., alias="X-Nonce"),
    db: AsyncSession = Depends(get_async_db)
) -> Any:
    """
    Tenant-based login endpoint
    This endpoint is called by the frontend API route after signature verification
    """
    logger = RequestLogger("auth.login_tenant")
    
    try:
        logger.info(f"Tenant login attempt - username: {username}, tenant_name: {tenant_name}, timestamp: {x_timestamp}, nonce: {x_nonce}")
        
        # 验证签名
        body = f"username={username}&password={password}&tenant_name={tenant_name}"
        backend_path = '/api/v1/auth/login/tenant'
        signature_string = f"POST{backend_path}{x_timestamp}{x_nonce}{tenant_name}{body}"
        
        logger.info(f"🔍 Backend 签名验证调试信息: username={username}, tenant_name={tenant_name}, timestamp={x_timestamp}, nonce={x_nonce}, body={body}, backend_path={backend_path}, signature_string_length={len(signature_string)}, x_signature_length={len(x_signature)}")
        
        if not await verify_tenant_signature(x_signature, signature_string, tenant_name, db):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        logger.info("Signature verified successfully")
        
        # Get tenant by name
        from sqlalchemy import select
        result = await db.execute(select(Tenant).where(Tenant.name == tenant_name))
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        tenant_id = tenant.id
        
        # Get user by email and tenant
        user_service = UserService(db)
        user = await user_service.get_by_email_and_tenant(email=username, tenant_id=tenant_id)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Verify password (assuming password is stored as hash)
        if not user_service.verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        logger.info(f"User authenticated successfully - user_id: {user.id}, tenant_id: {tenant_id}, tenant_name: {tenant_name}")
        
        # Return user data (without sensitive information)
        return {
            "user": {
                "id": user.id,
                "email": user.email,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None
            },
            "tenant_name": tenant.name,
            "tenant_id": tenant_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/register", response_model=UserResponse)
async def register(
    *,
    db: AsyncSession = Depends(get_async_db),
    user_in: UserCreate,
) -> Any:
    """
    Create new user account
    """
    user_service = UserService(db)
    
    # Check if user already exists
    user = await user_service.get_by_email(email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    
    user = await user_service.create(obj_in=user_in.dict())
    return user


@router.get("/me", response_model=UserResponse)
async def read_users_me(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> Any:
    """
    Get current user information
    Note: This endpoint now requires API Key authentication or RSA JWT
    """
    # This endpoint should be protected by the unified authentication middleware
    # For now, we'll return a placeholder response
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="This endpoint requires authentication. Use API Key or RSA JWT authentication.",
    )


@router.post("/test-auth")
async def test_authentication(
    request: Request
) -> Any:
    """
    Test authentication endpoint
    """
    return {
        "message": "Authentication test endpoint",
        "note": "Use API Key or RSA JWT authentication for protected endpoints"
    }
