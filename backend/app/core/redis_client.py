"""
Redis client for JWT blacklist and caching
"""

import json
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis import Redis
from app.core.config import settings


class RedisClient:
    """Redis client for JWT and API key management"""
    
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Connect to Redis"""
        if not self.client:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.client:
            await self.client.close()
            self.client = None
    
    async def add_to_blacklist(self, token: str, expires_at: datetime, user_id: int, customer_id: Optional[int] = None):
        """Add JWT token to blacklist"""
        await self.connect()
        
        # Hash the token for storage
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Calculate TTL (time to live)
        ttl = int((expires_at - datetime.utcnow()).total_seconds())
        if ttl <= 0:
            return  # Token already expired
        
        # Store in Redis with TTL
        key = f"jwt_blacklist:{token_hash}"
        value = json.dumps({
            "user_id": user_id,
            "customer_id": customer_id,
            "expires_at": expires_at.isoformat()
        })
        
        await self.client.setex(key, ttl, value)
    
    async def is_blacklisted(self, token: str) -> bool:
        """Check if JWT token is blacklisted"""
        await self.connect()
        
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        key = f"jwt_blacklist:{token_hash}"
        
        return await self.client.exists(key) > 0
    
    async def cache_api_key(self, key_id: str, api_key_data: Dict[str, Any], ttl: int = 3600):
        """Cache API key data"""
        await self.connect()
        
        key = f"api_key:{key_id}"
        await self.client.setex(key, ttl, json.dumps(api_key_data))
    
    async def get_cached_api_key(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Get cached API key data"""
        await self.connect()
        
        key = f"api_key:{key_id}"
        data = await self.client.get(key)
        
        if data:
            return json.loads(data)
        return None
    
    async def invalidate_api_key_cache(self, key_id: str):
        """Invalidate API key cache"""
        await self.connect()
        
        key = f"api_key:{key_id}"
        await self.client.delete(key)
    
    async def cache_user_session(self, user_id: int, session_data: Dict[str, Any], ttl: int = 1800):
        """Cache user session data"""
        await self.connect()
        
        key = f"user_session:{user_id}"
        await self.client.setex(key, ttl, json.dumps(session_data))
    
    async def get_user_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get cached user session data"""
        await self.connect()
        
        key = f"user_session:{user_id}"
        data = await self.client.get(key)
        
        if data:
            return json.loads(data)
        return None
    
    async def clear_user_session(self, user_id: int):
        """Clear user session cache"""
        await self.connect()
        
        key = f"user_session:{user_id}"
        await self.client.delete(key)


# Global Redis client instance
redis_client = RedisClient()
