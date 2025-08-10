"""
健康检查 API 认证和频率限制
"""

import time
import hashlib
from typing import Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
import redis.asyncio as redis
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class HealthCheckAuth:
    """健康检查认证和频率限制"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
    
    async def get_redis_client(self) -> redis.Redis:
        """获取 Redis 客户端"""
        if self.redis_client is None:
            # 解析 Redis URL
            redis_url = settings.REDIS_URL
            if redis_url.startswith("redis://"):
                redis_url = redis_url[8:]
            
            password = None
            if "@" in redis_url:
                auth_part, rest = redis_url.split("@", 1)
                if ":" in auth_part:
                    password = auth_part.split(":", 1)[1]
                redis_url = rest
            
            if ":" in redis_url:
                host_port, db_part = redis_url.split("/", 1)
                host, port = host_port.split(":")
                port = int(port)
            else:
                host = redis_url
                port = 6379
            
            self.redis_client = redis.Redis(
                host=host, 
                port=port, 
                password=password, 
                decode_responses=True
            )
        
        return self.redis_client
    
    def verify_api_key(self, api_key: str) -> bool:
        """验证 API Key"""
        if not api_key:
            return False
        
        # 检查配置的 API Key 是否为空
        expected_key = settings.HEALTH_CHECK_API_KEY
        if not expected_key:
            logger.error("HEALTH_CHECK_API_KEY is not configured")
            return False
        
        # 使用时间安全的字符串比较
        if len(api_key) != len(expected_key):
            return False
        
        result = 0
        for a, b in zip(api_key, expected_key):
            result |= ord(a) ^ ord(b)
        
        return result == 0
    
    async def check_rate_limit(self, identifier: str) -> bool:
        """检查频率限制"""
        try:
            redis_client = await self.get_redis_client()
            
            # 使用滑动窗口实现频率限制
            current_time = int(time.time())
            window_start = current_time - settings.HEALTH_CHECK_RATE_WINDOW
            
            # 清理过期的记录
            await redis_client.zremrangebyscore(
                f"health_check_rate_limit:{identifier}",
                0, window_start
            )
            
            # 获取当前窗口内的请求数
            current_count = await redis_client.zcard(
                f"health_check_rate_limit:{identifier}"
            )
            
            # 检查是否超过限制
            if current_count >= settings.HEALTH_CHECK_RATE_LIMIT:
                return False
            
            # 添加当前请求记录（使用微秒级时间戳避免重复）
            current_time_ms = int(time.time() * 1000)  # 毫秒级时间戳
            await redis_client.zadd(
                f"health_check_rate_limit:{identifier}",
                {str(current_time_ms): current_time_ms}
            )
            
            # 设置过期时间
            await redis_client.expire(
                f"health_check_rate_limit:{identifier}",
                settings.HEALTH_CHECK_RATE_WINDOW
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {str(e)}")
            # 如果 Redis 不可用，允许请求通过
            return True
    
    async def authenticate_health_check(self, request: Request) -> bool:
        """认证健康检查请求"""
        # 获取 API Key
        api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization")
        
        # 处理 Authorization header
        if api_key and api_key.startswith("Bearer "):
            api_key = api_key[7:]
        
        # 验证 API Key
        if not self.verify_api_key(api_key):
            logger.warning(
                "Invalid health check API key",
                ip=request.client.host,
                user_agent=request.headers.get("User-Agent", ""),
                api_key_hash=hashlib.sha256(api_key.encode()).hexdigest()[:8] if api_key else "none"
            )
            return False
        
        # 生成频率限制标识符（使用 IP + API Key 哈希）
        identifier = f"{request.client.host}:{hashlib.sha256(api_key.encode()).hexdigest()[:8]}"
        
        # 检查频率限制
        if not await self.check_rate_limit(identifier):
            logger.warning(
                "Health check rate limit exceeded",
                ip=request.client.host,
                identifier=identifier
            )
            return False
        
        # 记录成功的访问
        logger.info(
            "Health check accessed",
            ip=request.client.host,
            endpoint=request.url.path,
            identifier=identifier
        )
        
        return True


# 全局实例
health_check_auth = HealthCheckAuth()


async def require_health_check_auth(request: Request):
    """健康检查认证依赖"""
    if not await health_check_auth.authenticate_health_check(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key or rate limit exceeded",
            headers={"WWW-Authenticate": "ApiKey"},
        )
