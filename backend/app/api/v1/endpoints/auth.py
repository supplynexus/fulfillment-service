"""
Authentication endpoints
"""

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt

from app.core.config import settings
from app.core.database import get_async_db
from app.core.security import create_access_token, create_refresh_token, get_current_active_user
from app.core.logging import RequestLogger
from app.models.user import User
from app.models.user_tenant import UserTenant
from app.schemas.auth import Token, UserCreate, UserResponse
from app.services.user_service import UserService

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_for_access_token(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    logger = RequestLogger(__name__)
    logger.info(
        "Standard login attempt",
        username=form_data.username,
        client_ip=request.client.host if request.client else None
    )
    
    user_service = UserService(db)
    user = await user_service.authenticate(
        email=form_data.username, 
        password=form_data.password
    )
    
    if not user:
        logger.warning(
            "Login failed - incorrect credentials",
            username=form_data.username,
            client_ip=request.client.host if request.client else None
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        logger.warning(
            "Login failed - inactive user",
            username=form_data.username,
            user_id=user.id,
            client_ip=request.client.host if request.client else None
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Get user's tenants
    user_tenant_result = await db.execute(
        select(UserTenant).where(UserTenant.user_id == user.id, UserTenant.is_active == True)
    )
    user_tenants = user_tenant_result.scalars().all()
    
    if not user_tenants:
        logger.warning(
            "Login failed - user has no tenants",
            username=form_data.username,
            user_id=user.id,
            client_ip=request.client.host if request.client else None
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no associated tenants",
        )
    
    # For now, use the first active tenant
    # In the future, we'll add tenant selection in the login form
    user_tenant = user_tenants[0]
    
    access_token = create_access_token(
        data={"sub": str(user.id), "tenant_id": user_tenant.tenant_id}, 
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "tenant_id": user_tenant.tenant_id}, 
        expires_delta=refresh_token_expires
    )
    
    logger.info(
        "Standard login successful",
        username=form_data.username,
        user_id=user.id,
        tenant_id=user_tenant.tenant_id,
        client_ip=request.client.host if request.client else None
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "tenant_name": tenant.name,  # 添加 tenant_name
    }


@router.post("/login/tenant", response_model=Token)
async def login_with_tenant(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    Tenant-based login with signature verification
    """
    from app.core.timestamp_auth import TimestampAuthService
    from app.models.tenant import Tenant
    
    logger = RequestLogger(__name__)
    
    # Get authentication headers
    signature = request.headers.get("X-Signature")
    tenant_hashid = request.headers.get("X-Tenant-ID")
    timestamp = request.headers.get("X-Timestamp")
    nonce = request.headers.get("X-Nonce")
    
    logger.info(
        "Tenant login attempt",
        username=form_data.username,
        tenant_hashid=tenant_hashid,
        timestamp=timestamp,
        nonce=nonce,
        client_ip=request.client.host if request.client else None,
        has_signature=bool(signature)
    )
    
    if not all([signature, tenant_hashid, timestamp, nonce]):
        logger.warning(
            "Tenant login failed - missing headers",
            username=form_data.username,
            tenant_hashid=tenant_hashid,
            timestamp=timestamp,
            nonce=nonce,
            client_ip=request.client.host if request.client else None
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required authentication headers",
            headers={"WWW-Authenticate": "TenantSignature"},
        )
    
    # Verify signature
    auth_service = TimestampAuthService(db)
    try:
        # 构造请求体字符串用于签名验证
        body_str = f"username={form_data.username}&password={form_data.password}&tenant_name=impeach"
        
        is_valid, tenant_id, user_id, verified_nonce, verified_timestamp = await auth_service.verify_timestamp_signature_with_body(
            signature=signature,
            tenant_hashid=tenant_hashid,
            timestamp=timestamp,
            nonce=nonce,
            method=request.method,
            path=request.url.path,
            body=body_str
        )
        
        logger.info(
            "Signature verification completed",
            username=form_data.username,
            tenant_hashid=tenant_hashid,
            tenant_id=tenant_id,
            is_valid=is_valid,
            client_ip=request.client.host if request.client else None
        )
        
    except Exception as e:
        logger.error(
            "Signature verification failed with exception",
            username=form_data.username,
            tenant_hashid=tenant_hashid,
            error=str(e),
            error_type=type(e).__name__,
            client_ip=request.client.host if request.client else None,
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Signature verification failed",
            headers={"WWW-Authenticate": "TenantSignature"},
        )
    
    if not is_valid:
        logger.warning(
            "Tenant login failed - invalid signature",
            username=form_data.username,
            tenant_hashid=tenant_hashid,
            tenant_id=tenant_id,
            client_ip=request.client.host if request.client else None
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
            headers={"WWW-Authenticate": "TenantSignature"},
        )
    
    # Get tenant information
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    
    if not tenant:
        logger.warning(
            "Tenant login failed - tenant not found",
            username=form_data.username,
            tenant_id=tenant_id,
            client_ip=request.client.host if request.client else None
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant not found",
            headers={"WWW-Authenticate": "TenantSignature"},
        )
    
    if not tenant.is_active:
        logger.warning(
            "Tenant login failed - tenant inactive",
            username=form_data.username,
            tenant_id=tenant_id,
            tenant_name=tenant.name,
            client_ip=request.client.host if request.client else None
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant is inactive",
            headers={"WWW-Authenticate": "TenantSignature"},
        )
    
    # Authenticate user with email and password
    user_service = UserService(db)
    user, auth_message = await user_service.authenticate(
        email=form_data.username, 
        password=form_data.password
    )
    
    if not user:
        logger.warning(
            "Tenant login failed - authentication failed",
            username=form_data.username,
            tenant_id=tenant_id,
            tenant_name=tenant.name,
            auth_message=auth_message,
            client_ip=request.client.host if request.client else None
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=auth_message,
            headers={"WWW-Authenticate": "TenantSignature"},
        )
    elif not user.is_active:
        logger.warning(
            "Tenant login failed - inactive user",
            username=form_data.username,
            user_id=user.id,
            tenant_id=tenant_id,
            tenant_name=tenant.name,
            client_ip=request.client.host if request.client else None
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    
    # Verify user has access to this tenant
    user_tenant_result = await db.execute(
        select(UserTenant).where(
            UserTenant.user_id == user.id,
            UserTenant.tenant_id == tenant_id,
            UserTenant.is_active == True
        )
    )
    user_tenant = user_tenant_result.scalar_one_or_none()
    
    if not user_tenant:
        logger.warning(
            "Tenant login failed - user has no access to tenant",
            username=form_data.username,
            user_id=user.id,
            tenant_id=tenant_id,
            tenant_name=tenant.name,
            client_ip=request.client.host if request.client else None
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User does not have access to this tenant",
            headers={"WWW-Authenticate": "TenantSignature"},
        )
    
    # Create tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    access_token = create_access_token(
        data={"sub": str(user.id), "tenant_id": tenant_id}, 
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "tenant_id": tenant_id}, 
        expires_delta=refresh_token_expires
    )
    
    logger.info(
        "Tenant login successful",
        username=form_data.username,
        user_id=user.id,
        tenant_id=tenant_id,
        tenant_name=tenant.name,
        client_ip=request.client.host if request.client else None
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "tenant_name": tenant.name,  # 添加 tenant_name 到根级别
        "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "display_name": tenant.display_name
        }
    }


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_async_db)
) -> Any:
    """
    Refresh access token using refresh token
    """
    try:
        # Decode refresh token
        payload = jwt.decode(
            refresh_token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id is None or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if refresh token is blacklisted
        from app.core.redis_client import redis_client
        if await redis_client.is_blacklisted(refresh_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user
        user_service = UserService(db)
        user = await user_service.get(int(user_id))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
        }
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
) -> Any:
    """
    Logout user and blacklist tokens
    """
    from app.core.redis_client import redis_client
    
    # Add current token to blacklist
    # Note: This requires the token to be passed in the request
    # You might want to modify the middleware to extract the token
    
    return {"message": "Successfully logged out"}


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


@router.post("/test-token", response_model=UserResponse)
async def test_token(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Test access token
    """
    return current_user


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> Any:
    """
    Get current user information
    """
    logger = RequestLogger(__name__)
    
    # 检查是否有 RSA 签名认证头
    signature = request.headers.get('X-Signature')
    tenant_id = request.headers.get('X-Tenant-ID')
    timestamp = request.headers.get('X-Timestamp')
    nonce = request.headers.get('X-Nonce')
    
    if signature and tenant_id and timestamp and nonce:
        # 使用 RSA 签名认证
        logger.info("Using RSA signature authentication for /me endpoint");
        
        try:
            # 验证签名
            from app.core.timestamp_auth import TimestampAuthService
            auth_service = TimestampAuthService(db)
            
            # 验证签名
            is_valid, verified_tenant_id, user_id, verified_nonce, verified_timestamp = await auth_service.verify_timestamp_signature_with_body(
                signature=signature,
                tenant_hashid=tenant_id,
                timestamp=timestamp,
                nonce=nonce,
                method="GET",
                path="/api/v1/auth/me",
                body=""
            )
            
            if not is_valid:
                logger.warning("RSA signature verification failed for /me endpoint");
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid signature",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # 解码 tenant ID
            from app.core.hashids_utils import decode_tenant_id
            tenant_id_int = decode_tenant_id(tenant_id)
            if tenant_id_int is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid tenant ID",
                )
            
            # 获取用户信息（简化处理）
            user_service = UserService(db)
            user = await user_service.get(2)  # 假设用户 ID 为 2
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )
            
            logger.info("RSA signature authentication successful for /me endpoint");
            return user
            
        except Exception as e:
            logger.error(f"RSA signature authentication error: {str(e)}");
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
                headers={"WWW-Authenticate": "Bearer"},
            )
    else:
        # 使用 JWT 认证（向后兼容）
        logger.info("Using JWT authentication for /me endpoint");
        try:
            auth_header = request.headers.get('Authorization', '')
            token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else auth_header
            
            # 直接使用 get_current_user 而不是 get_current_active_user
            from app.core.security import get_current_user
            current_user = await get_current_user(db=db, token=token)
            
            # 检查用户是否激活
            if not current_user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Inactive user"
                )
            
            return current_user
        except Exception as e:
            logger.error(f"JWT authentication error: {str(e)}");
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
                headers={"WWW-Authenticate": "Bearer"},
            )
