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
        # Include query parameters in the path to match frontend signature generation
        method = request.method.upper()
        path = request.url.path
        query_string = request.url.query
        # Build full path with query parameters if they exist
        full_path = f"{path}?{query_string}" if query_string else path
        signature_string = f"{method}{full_path}{x_timestamp}{x_nonce}{x_tenant_name}{body_str}"
        
        logger.info(f"🔍 后端签名验证调试信息: tenant_name={x_tenant_name}, method={method}, path={full_path}, query={query_string}, timestamp={x_timestamp}, nonce={x_nonce}, body_length={len(body_str)}, signature_string_length={len(signature_string)}, x_signature_length={len(x_signature)}")
        logger.info(f"🔍 后端构建的签名字符串: {signature_string}")
        logger.info(f"🔍 前端发送的签名: {x_signature[:50]}...")
        
        # Verify signature
        try:
            signature_valid = await verify_tenant_signature(x_signature, signature_string, x_tenant_name, db)
            logger.info(f"🔍 签名验证结果: {signature_valid}")
            
            if not signature_valid:
                logger.error(f"❌ 签名验证失败: tenant_name={x_tenant_name}, signature_string={signature_string}")
                raise HTTPException(status_code=401, detail="Invalid signature")
        except Exception as e:
            import traceback
            logger.error(f"❌ 签名验证过程中发生异常: {str(e)}")
            logger.error(f"   异常类型: {type(e).__name__}")
            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Signature verification error: {str(e)}")
        
        logger.info("Signature verified successfully")
        
        # Get tenant by name
        logger.info(f"🔍 查询租户信息: {x_tenant_name}")
        try:
            result = await db.execute(select(Tenant).where(Tenant.name == x_tenant_name))
            tenant = result.scalar_one_or_none()
            if not tenant:
                logger.error(f"❌ 租户不存在: {x_tenant_name}")
                raise HTTPException(status_code=404, detail="Tenant not found")
            
            logger.info(f"✅ 租户查询成功: id={tenant.id}, name={tenant.name}, is_active={tenant.is_active}")
            
            if not tenant.is_active:
                logger.error(f"❌ 租户未激活: {x_tenant_name}")
                raise HTTPException(status_code=401, detail="Tenant is inactive")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ 查询租户时发生异常: {str(e)}")
            import traceback
            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
        # For now, we'll return a system user or create a mock user
        # In a real implementation, you might want to get the actual user from the signature
        # For simplicity, we'll use a system user approach
        
        # Get or create system user for this tenant
        logger.info(f"🔍 查询系统用户: system@supplynexus.store")
        try:
            system_user_result = await db.execute(
                select(User).where(User.email == "system@supplynexus.store")
            )
            system_user = system_user_result.scalar_one_or_none()
            
            if not system_user:
                logger.info(f"🔍 系统用户不存在，正在创建...")
                # Create system user if it doesn't exist
                from app.services.user_service import UserService
                user_service = UserService(db)
                system_user = await user_service.create_system_user()
                logger.info(f"✅ 系统用户创建成功: id={system_user.id}")
            else:
                logger.info(f"✅ 系统用户查询成功: id={system_user.id}, email={system_user.email}")
        except Exception as e:
            logger.error(f"❌ 查询/创建系统用户时发生异常: {str(e)}")
            import traceback
            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"User service error: {str(e)}")
        
        logger.info(f"✅ 租户认证成功 - tenant_id: {tenant.id}, tenant_name: {tenant.name}, user_id: {system_user.id}")
        
        return tenant, system_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tenant auth error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


def require_tenant_auth():
    """Factory function that returns tenant authentication dependency"""
    return verify_tenant_auth
