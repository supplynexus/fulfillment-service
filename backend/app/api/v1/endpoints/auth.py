"""
Authentication endpoints - Simplified version without JWT
"""

from typing import Any
import base64
from cryptography.hazmat.primitives import (
    hashes,
    serialization,
)
from cryptography.hazmat.primitives.asymmetric import (
    padding,
)
from cryptography.hazmat.backends import (
    default_backend,
)

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request,
    Form,
    Header,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.logging import RequestLogger
from app.models.tenant import Tenant
from app.schemas.auth import UserCreate, UserResponse
from app.services.user_service import UserService
from app.core.jwt_utils import jwt_utils

router = APIRouter()


async def verify_tenant_signature(
    signature: str, message: str, tenant_name: str, db: AsyncSession
) -> bool:
    """
    验证租户签名
    """
    try:
        from sqlalchemy import select  # pyright: ignore[reportMissingImports]

        # 使用标准日志记录替换 print，便于后续排查和生产环境调试
        from app.core.logging import get_logger

        logger = get_logger(__name__)
        logger.info(
            "🔍 签名验证调试信息",
            tenant_name=tenant_name,
            signature_preview=(
                signature[:50] + "..." if len(signature) > 50 else signature
            ),
            message_preview=(message[:100] + "..." if len(message) > 100 else message),
            message_length=len(message),
        )

        # 获取租户信息和公钥
        logger.info("🔍 查询数据库获取租户信息...", tenant_name=tenant_name)
        try:
            tenant_result = await db.execute(
                select(Tenant).where(Tenant.name == tenant_name)
            )
            tenant = tenant_result.scalar_one_or_none()
            if tenant:
                logger.info(
                    "✅ 租户信息查询成功", tenant_id=tenant.id, tenant_name=tenant.name
                )
            else:
                logger.error("❌ 未找到租户信息", tenant_name=tenant_name)
        except Exception as e:
            logger.error(
                "❌ 查询租户信息时发生异常", error=str(e), tenant_name=tenant_name
            )
            import traceback

            logger.error("   异常堆栈", stack=traceback.format_exc())
            return False

        if not tenant:
            print(f"❌ 租户不存在: {tenant_name}")
            return False
        # 日志记录：租户存在
        from app.core.logging import get_logger

        logger = get_logger(__name__)
        logger.info(
            "✅ 租户存在",
            tenant_id=tenant.id,
            tenant_name=tenant.name,
            is_active=tenant.is_active,
        )

        if not tenant.public_key:
            logger.error(
                "❌ 租户公钥不存在", tenant_id=tenant.id, tenant_name=tenant.name
            )
            logger.error(
                "❌ 租户公钥不存在", tenant_id=tenant.id, tenant_name=tenant.name
            )
            return False

        logger.info(
            "✅ 从租户表获取公钥成功",
            key_id=tenant.key_id,
            key_type=tenant.key_type,
            public_key_length=len(tenant.public_key),
            public_key_preview=(
                tenant.public_key[:100] + "..."
                if len(tenant.public_key) > 100
                else tenant.public_key
            ),
        )

        # 加载公钥
        try:
            public_key = serialization.load_pem_public_key(
                tenant.public_key.encode("utf-8"), backend=default_backend()
            )
            logger.info("✅ 公钥加载成功", tenant_id=tenant.id, tenant_name=tenant.name)
        except Exception as e:
            logger.error(
                "❌ 公钥加载失败",
                error=str(e),
                tenant_id=tenant.id,
                tenant_name=tenant.name,
            )
            import traceback

            logger.error("   异常堆栈", stack=traceback.format_exc())
            return False

        # 解码签名
        try:
            signature_bytes = base64.b64decode(signature.encode("utf-8"))
            print(f"   signature_bytes_length: {len(signature_bytes)}")
        except Exception as e:
            print(f"❌ 签名解码失败: {e}")
            return False

        # 验证签名 - 使用 PKCS1v15 填充，与前端 RSA-SHA256 匹配
        try:
            public_key.verify(
                signature_bytes,
                message.encode("utf-8"),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            logger.info("✅ 签名验证成功", tenant_id=tenant.id, tenant_name=tenant.name)
        except Exception as e:
            logger.error(
                "❌ 签名验证失败",
                error=str(e),
                tenant_id=tenant.id,
                tenant_name=tenant.name,
            )
            import traceback

            logger.error("   异常堆栈", stack=traceback.format_exc())
            logger.error("   异常类型", error_type=type(e).__name__)
            return False

        # 更新租户密钥使用统计（如果需要的话）
        # 这里可以添加租户密钥使用统计的逻辑
        await db.commit()

        return True

    except Exception as e:
        print(f"❌ 签名验证失败: {e}")
        print(f"   Exception type: {type(e).__name__}")
        import traceback

        print(f"   Traceback: {traceback.format_exc()}")
        # 重新抛出异常，让调用者能够看到具体的错误信息
        raise e


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    tenant_name: str = Form(...),
    x_signature: str = Header(..., alias="X-Signature"),
    x_tenant_name: str = Header(..., alias="X-Tenant-Name"),
    x_timestamp: str = Header(..., alias="X-Timestamp"),
    x_nonce: str = Header(..., alias="X-Nonce"),
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    """
    主登录端点
    此端点由前端 API 路由在签名验证后调用
    """
    from app.core.logging import get_logger

    logger = get_logger(__name__)

    try:
        logger.info(
            "🔍 开始处理登录请求",
            params={
                "username": username,
                "tenant_name": tenant_name,
                "timestamp": x_timestamp,
                "nonce": x_nonce,
            },
        )
        logger.info(
            f"Login attempt - username: {username}, "
            f"tenant_name: {tenant_name}, timestamp: {x_timestamp}, "
            f"nonce: {x_nonce}"
        )

        # 验证签名
        # 构建 body 字符串，避免超过最大行长度
        # 按照PEP8规范，每行不超过79字符
        body = (
            f"username={username}" f"&password={password}" f"&tenant_name={tenant_name}"
        )
        backend_path = "/api/v1/auth/login"
        signature_string = (
            f"POST{backend_path}{x_timestamp}{x_nonce}{tenant_name}{body}"
        )

        logger.info(
            f"🔍 Backend 签名验证调试信息: username={username}, "
            f"tenant_name={tenant_name}, timestamp={x_timestamp}, "
            f"nonce={x_nonce}, body={body}, backend_path={backend_path}, "
            f"signature_string_length={len(signature_string)}, "
            f"x_signature_length={len(x_signature)}"
        )

        if not await verify_tenant_signature(
            x_signature, signature_string, tenant_name, db
        ):
            raise HTTPException(status_code=401, detail="Invalid signature")

        logger.info("Signature verified successfully")

        # Get tenant by name
        from sqlalchemy import select  # pyright: ignore[reportMissingImports]

        result = await db.execute(select(Tenant).where(Tenant.name == tenant_name))
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        tenant_id = tenant.id

        # Get user by email and tenant
        user_service = UserService(db)
        user = await user_service.get_by_email_and_tenant(
            email=username, tenant_id=tenant_id
        )

        if not user:
            logger.error(f"❌ 用户不存在: username={username}, tenant_id={tenant_id}")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # 添加密码验证调试日志
        logger.info(f"🔍 开始密码验证: username={username}, password_length={len(password)}, hash_length={len(user.hashed_password) if user.hashed_password else 0}")
        
        # Verify password (assuming password is stored as hash)
        password_valid = await user_service.verify_password(password, user.hashed_password)
        logger.info(f"🔍 密码验证结果: {password_valid}")
        
        if not password_valid:
            logger.error(f"❌ 密码验证失败: username={username}")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        logger.info(
            f"User authenticated successfully - user_id: {user.id}, "
            f"tenant_id: {tenant_id}, tenant_name: {tenant_name}"
        )

        # Generate JWT tokens
        try:
            access_token = jwt_utils.generate_access_token(
                user_id=user.id,
                tenant_id=tenant_id,
                email=user.email,
                tenant_name=tenant_name,
                expires_in=3600,  # 1 hour
            )

            refresh_token = jwt_utils.generate_refresh_token(
                user_id=user.id,
                tenant_id=tenant_id,
                email=user.email,
                tenant_name=tenant_name,
                expires_in=86400 * 7,  # 7 days
            )

            logger.info("JWT tokens generated successfully")

        except Exception as e:
            logger.error(f"Failed to generate JWT tokens: {str(e)}")
            raise HTTPException(
                status_code=500, detail="Failed to generate authentication tokens"
            )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user.id,
                "email": user.email,
                "is_active": user.is_active,
                "created_at": (
                    user.created_at.isoformat() if user.created_at else None
                ),
            },
            "tenant_name": tenant.name,
            "tenant_id": tenant_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


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
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    """
    Tenant-based login endpoint
    This endpoint is called by the frontend API route after signature verification
    """
    logger = RequestLogger("auth.login_tenant")

    try:
        logger.info(
            f"Tenant login attempt - username: {username}, "
            f"tenant_name: {tenant_name}, timestamp: {x_timestamp}, "
            f"nonce: {x_nonce}"
        )

        # 验证签名
        body = f"username={username}&password={password}&" f"tenant_name={tenant_name}"
        backend_path = "/api/v1/auth/login/tenant"
        signature_string = (
            f"POST{backend_path}{x_timestamp}{x_nonce}{tenant_name}{body}"
        )

        logger.info(
            f"🔍 Backend 签名验证调试信息: username={username}, "
            f"tenant_name={tenant_name}, timestamp={x_timestamp}, "
            f"nonce={x_nonce}, body={body}, backend_path={backend_path}, "
            f"signature_string_length={len(signature_string)}, "
            f"x_signature_length={len(x_signature)}"
        )

        if not await verify_tenant_signature(
            x_signature, signature_string, tenant_name, db
        ):
            raise HTTPException(status_code=401, detail="Invalid signature")

        logger.info("Signature verified successfully")

        # Get tenant by name
        from sqlalchemy import select  # pyright: ignore[reportMissingImports]

        result = await db.execute(select(Tenant).where(Tenant.name == tenant_name))
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        tenant_id = tenant.id

        # Get user by email and tenant
        user_service = UserService(db)
        user = await user_service.get_by_email_and_tenant(
            email=username, tenant_id=tenant_id
        )

        if not user:
            logger.error(f"❌ 用户不存在: username={username}, tenant_id={tenant_id}")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # 添加密码验证调试日志
        logger.info(f"🔍 开始密码验证: username={username}, password_length={len(password)}, hash_length={len(user.hashed_password) if user.hashed_password else 0}")
        
        # Verify password (assuming password is stored as hash)
        password_valid = await user_service.verify_password(password, user.hashed_password)
        logger.info(f"🔍 密码验证结果: {password_valid}")
        
        if not password_valid:
            logger.error(f"❌ 密码验证失败: username={username}")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        logger.info(
            f"User authenticated successfully - user_id: {user.id}, "
            f"tenant_id: {tenant_id}, tenant_name: {tenant_name}"
        )

        # Return user data (without sensitive information)
        return {
            "user": {
                "id": user.id,
                "email": user.email,
                "is_active": user.is_active,
                "created_at": (
                    user.created_at.isoformat() if user.created_at else None
                ),
            },
            "tenant_name": tenant.name,
            "tenant_id": tenant_id,
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
    request: Request, db: AsyncSession = Depends(get_async_db)
) -> Any:
    """
    Get current user information
    Note: This endpoint now requires API Key authentication or RSA JWT
    """
    # This endpoint should be protected by the unified authentication middleware
    # For now, we'll return a placeholder response
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="This endpoint requires authentication. "
        "Use API Key or RSA JWT authentication.",
    )


@router.post("/test-auth")
async def test_authentication(request: Request) -> Any:
    """
    Test authentication endpoint
    """
    return {
        "message": "Authentication test endpoint",
        "note": "Use API Key or RSA JWT authentication for protected endpoints",
    }
