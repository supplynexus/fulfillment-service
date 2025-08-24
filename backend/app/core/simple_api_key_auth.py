"""
Simplified API Key authentication for system-level APIs only
"""

import hashlib
from typing import Optional
from fastapi import HTTPException, Request, status
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class SimpleApiKeyAuth:
    """Simplified API Key authentication for system-level APIs"""
    
    def __init__(self):
        self.system_api_key = settings.SYSTEM_API_KEY
    
    def verify_api_key(self, api_key: str) -> bool:
        """Verify system API key"""
        if not api_key or not self.system_api_key:
            return False
        
        # 使用时间安全的字符串比较
        if len(api_key) != len(self.system_api_key):
            return False
        
        result = 0
        for a, b in zip(api_key, self.system_api_key):
            result |= ord(a) ^ ord(b)
        
        return result == 0
    
    async def authenticate_request(self, request: Request) -> bool:
        """Authenticate system API request"""
        # 获取 API Key
        api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization")
        
        # 处理 Authorization header
        if api_key and api_key.startswith("Bearer "):
            api_key = api_key[7:]
        
        # 验证 API Key
        if not self.verify_api_key(api_key):
            logger.warning(
                "Invalid system API key",
                ip=request.client.host,
                endpoint=request.url.path,
                api_key_hash=hashlib.sha256(api_key.encode()).hexdigest()[:8] if api_key else "none"
            )
            return False
        
        # 记录成功的访问
        logger.info(
            "System API accessed",
            ip=request.client.host,
            endpoint=request.url.path
        )
        
        return True


# 全局实例
simple_api_key_auth = SimpleApiKeyAuth()


async def require_system_api_key(request: Request):
    """System API key authentication dependency"""
    if not await simple_api_key_auth.authenticate_request(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid system API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
