"""
System-level API endpoints for monitoring and administration
"""

from fastapi import APIRouter, Depends, Request
from typing import Dict, Any
import structlog

from app.core.simple_api_key_auth import require_system_api_key
from app.core.config import settings

logger = structlog.get_logger()

router = APIRouter()


@router.get("/env")
async def get_environment_info(
    request: Request,
    _: None = Depends(require_system_api_key)
) -> Dict[str, Any]:
    """
    Get environment configuration information
    Note: This endpoint only shows non-sensitive configuration
    """
    
    # 获取环境文件路径
    env_file_path = settings.get_env_file_path()
    
    # 获取重要环境变量（排除敏感信息）
    env_vars = settings.get_important_env_vars()
    
    # 过滤敏感信息
    safe_env_vars = {}
    
    def mask_password_in_url(url: str) -> str:
        """在 URL 中隐藏密码，保留其他连接信息"""
        if not url or '@' not in url:
            return url
        
        # 处理 postgresql://username:password@host:port/database 格式
        if '://' in url:
            protocol, rest = url.split('://', 1)
            if '@' in rest:
                auth_part, host_part = rest.split('@', 1)
                if ':' in auth_part:
                    username, password = auth_part.split(':', 1)
                    return f"{protocol}://{username}:***@{host_part}"
                else:
                    # 处理 redis://password@host:port/db 格式
                    return f"{protocol}://***@{host_part}"
        
        return url
    
    for key, value in env_vars.items():
        if key in ['DATABASE_URL', 'REDIS_URL']:
            # 只隐藏密码，保留连接信息
            safe_env_vars[key] = mask_password_in_url(value)
        elif key in ['HEALTH_CHECK_API_KEY', 'SYSTEM_API_KEY']:
            # API 密钥完全隐藏
            if isinstance(value, str) and len(value) > 8:
                safe_env_vars[key] = value[:4] + "..." + value[-4:]
            else:
                safe_env_vars[key] = "***"
        else:
            safe_env_vars[key] = value
    
    return {
        "environment_file": env_file_path,
        "environment_variables": safe_env_vars,
        "service_info": {
            "name": "SupplyNexus Fulfillment Service",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "debug": settings.ENVIRONMENT == "dev"
        }
    }


@router.get("/config")
async def get_system_config(
    request: Request,
    _: None = Depends(require_system_api_key)
) -> Dict[str, Any]:
    """
    Get system configuration (non-sensitive)
    """
    
    return {
        "database": {
            "url": settings.DATABASE_URL,
            "pool_size": getattr(settings, 'DATABASE_POOL_SIZE', 'Not configured'),
            "max_overflow": getattr(settings, 'DATABASE_MAX_OVERFLOW', 'Not configured')
        },
        "redis": {
            "url": settings.REDIS_URL,
            "broker_url": settings.CELERY_BROKER_URL,
            "result_backend": getattr(settings, 'CELERY_RESULT_BACKEND', 'Not configured')
        },
        "security": {
            "webhook_secret": "configured"
        },
        "logging": {
            "level": getattr(settings, 'LOG_LEVEL', 'Not configured'),
            "format": getattr(settings, 'LOG_FORMAT', 'Not configured')
        },
        "api": {
            "v1_str": settings.API_V1_STR,
            "environment": settings.ENVIRONMENT
        }
    }


@router.get("/status")
async def get_system_status(
    request: Request,
    _: None = Depends(require_system_api_key)
) -> Dict[str, Any]:
    """
    Get system status information
    """
    
    import os
    import time
    
    # 获取进程信息
    pid = os.getpid()
    
    return {
        "service": {
            "name": "SupplyNexus Fulfillment Service",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "pid": pid,
            "startup_time": time.time()
        },
        "system": {
            "platform": os.name,
            "current_working_directory": os.getcwd(),
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"
        },
        "timestamp": time.time()
    }
