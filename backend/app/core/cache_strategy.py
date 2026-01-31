"""
缓存策略实现

提供Redis缓存、内存缓存和查询缓存策略
"""

import json
import pickle
import hashlib
from typing import Any, Optional, Dict, List, Union, Callable
from datetime import datetime, timedelta
import asyncio
import logging

from app.core.redis_client import redis_client
from app.core.logging import get_logger

logger = get_logger(__name__)


class CacheStrategy:
    """缓存策略基类"""
    
    def __init__(self, ttl: int = 300, prefix: str = ""):
        self.ttl = ttl
        self.prefix = prefix
    
    def _generate_key(self, key: str) -> str:
        """生成缓存键"""
        return f"{self.prefix}:{key}" if self.prefix else key
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        raise NotImplementedError
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        raise NotImplementedError
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        raise NotImplementedError
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        raise NotImplementedError


class RedisCacheStrategy(CacheStrategy):
    """Redis缓存策略"""
    
    def __init__(self, ttl: int = 300, prefix: str = "app"):
        super().__init__(ttl, prefix)
        self.redis = redis_client
    
    async def get(self, key: str) -> Optional[Any]:
        """从Redis获取缓存"""
        try:
            cache_key = self._generate_key(key)
            data = await self.redis.get(cache_key)
            
            if data is None:
                return None
            
            # 尝试JSON反序列化
            try:
                return json.loads(data)
            except (json.JSONDecodeError, TypeError):
                # 如果JSON失败，尝试pickle反序列化
                try:
                    return pickle.loads(data)
                except (pickle.PickleError, TypeError):
                    logger.warning(f"无法反序列化缓存数据: {cache_key}")
                    return None
                    
        except Exception as e:
            logger.error(f"Redis缓存获取失败: {key}, 错误: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置Redis缓存"""
        try:
            cache_key = self._generate_key(key)
            ttl = ttl or self.ttl
            
            # 尝试JSON序列化
            try:
                data = json.dumps(value, default=str)
            except (TypeError, ValueError):
                # 如果JSON失败，使用pickle序列化
                data = pickle.dumps(value)
            
            await self.redis.setex(cache_key, ttl, data)
            return True
            
        except Exception as e:
            logger.error(f"Redis缓存设置失败: {key}, 错误: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除Redis缓存"""
        try:
            cache_key = self._generate_key(key)
            result = await self.redis.delete(cache_key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis缓存删除失败: {key}, 错误: {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查Redis缓存是否存在"""
        try:
            cache_key = self._generate_key(key)
            result = await self.redis.exists(cache_key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis缓存检查失败: {key}, 错误: {str(e)}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """删除匹配模式的缓存"""
        try:
            cache_pattern = self._generate_key(pattern)
            keys = await self.redis.keys(cache_pattern)
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis批量删除失败: {pattern}, 错误: {str(e)}")
            return 0


class MemoryCacheStrategy(CacheStrategy):
    """内存缓存策略"""
    
    def __init__(self, ttl: int = 300, max_size: int = 1000):
        super().__init__(ttl)
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
    
    async def get(self, key: str) -> Optional[Any]:
        """从内存获取缓存"""
        cache_key = self._generate_key(key)
        
        if cache_key not in self.cache:
            return None
        
        cache_item = self.cache[cache_key]
        
        # 检查是否过期
        if datetime.now() > cache_item['expires_at']:
            del self.cache[cache_key]
            return None
        
        # 更新访问时间
        cache_item['accessed_at'] = datetime.now()
        return cache_item['value']
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置内存缓存"""
        try:
            cache_key = self._generate_key(key)
            ttl = ttl or self.ttl
            
            # 如果缓存已满，删除最旧的项
            if len(self.cache) >= self.max_size:
                await self._evict_oldest()
            
            expires_at = datetime.now() + timedelta(seconds=ttl)
            self.cache[cache_key] = {
                'value': value,
                'created_at': datetime.now(),
                'accessed_at': datetime.now(),
                'expires_at': expires_at
            }
            
            return True
        except Exception as e:
            logger.error(f"内存缓存设置失败: {key}, 错误: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除内存缓存"""
        cache_key = self._generate_key(key)
        if cache_key in self.cache:
            del self.cache[cache_key]
            return True
        return False
    
    async def exists(self, key: str) -> bool:
        """检查内存缓存是否存在"""
        cache_key = self._generate_key(key)
        return cache_key in self.cache and datetime.now() <= self.cache[cache_key]['expires_at']
    
    async def _evict_oldest(self):
        """删除最旧的缓存项"""
        if not self.cache:
            return
        
        oldest_key = min(
            self.cache.keys(),
            key=lambda k: self.cache[k]['accessed_at']
        )
        del self.cache[oldest_key]


class QueryCache:
    """查询缓存管理器"""
    
    def __init__(self, strategy: CacheStrategy):
        self.strategy = strategy
    
    def _generate_query_key(self, query_func: str, params: Dict[str, Any]) -> str:
        """生成查询缓存键"""
        # 创建参数的哈希值
        params_str = json.dumps(params, sort_keys=True, default=str)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()
        return f"query:{query_func}:{params_hash}"
    
    async def get_or_set(
        self,
        query_func: str,
        params: Dict[str, Any],
        fetch_func: Callable,
        ttl: Optional[int] = None
    ) -> Any:
        """获取或设置查询缓存"""
        cache_key = self._generate_query_key(query_func, params)
        
        # 尝试从缓存获取
        cached_result = await self.strategy.get(cache_key)
        if cached_result is not None:
            logger.debug(f"查询缓存命中: {query_func}")
            return cached_result
        
        # 缓存未命中，执行查询
        logger.debug(f"查询缓存未命中: {query_func}")
        result = await fetch_func()
        
        # 设置缓存
        await self.strategy.set(cache_key, result, ttl)
        
        return result
    
    async def invalidate_query(self, query_func: str, params: Optional[Dict[str, Any]] = None):
        """使查询缓存失效"""
        if params:
            cache_key = self._generate_query_key(query_func, params)
            await self.strategy.delete(cache_key)
        else:
            # 删除所有匹配的查询缓存
            pattern = f"query:{query_func}:*"
            await self.strategy.delete_pattern(pattern)


class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        # 创建不同层级的缓存策略
        self.redis_cache = RedisCacheStrategy(ttl=300, prefix="app")
        self.memory_cache = MemoryCacheStrategy(ttl=60, max_size=500)
        
        # 创建查询缓存
        self.query_cache = QueryCache(self.redis_cache)
    
    async def get(self, key: str, use_memory: bool = True) -> Optional[Any]:
        """获取缓存（优先内存，其次Redis）"""
        if use_memory:
            # 先尝试内存缓存
            result = await self.memory_cache.get(key)
            if result is not None:
                return result
        
        # 尝试Redis缓存
        result = await self.redis_cache.get(key)
        if result is not None:
            # 将Redis结果写入内存缓存
            if use_memory:
                await self.memory_cache.set(key, result, ttl=60)
            return result
        
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, use_memory: bool = True) -> bool:
        """设置缓存（同时写入内存和Redis）"""
        success = True
        
        # 设置Redis缓存
        if not await self.redis_cache.set(key, value, ttl):
            success = False
        
        # 设置内存缓存
        if use_memory:
            if not await self.memory_cache.set(key, value, ttl=60):
                success = False
        
        return success
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        redis_success = await self.redis_cache.delete(key)
        memory_success = await self.memory_cache.delete(key)
        return redis_success or memory_success
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """使匹配模式的缓存失效"""
        return await self.redis_cache.delete_pattern(pattern)
    
    # 业务特定的缓存方法
    async def get_product_categories(self, tenant_id: int) -> Optional[List[Dict]]:
        """获取产品分类缓存"""
        key = f"product_categories:tenant:{tenant_id}"
        return await self.get(key)
    
    async def set_product_categories(self, tenant_id: int, categories: List[Dict], ttl: int = 300) -> bool:
        """设置产品分类缓存"""
        key = f"product_categories:tenant:{tenant_id}"
        return await self.set(key, categories, ttl)
    
    async def invalidate_product_categories(self, tenant_id: int) -> bool:
        """使产品分类缓存失效"""
        key = f"product_categories:tenant:{tenant_id}"
        return await self.delete(key)
    
    async def get_product_variants(self, tenant_id: int, filters: Dict = None) -> Optional[List[Dict]]:
        """获取产品变体缓存"""
        filters_str = json.dumps(filters or {}, sort_keys=True)
        key = f"product_variants:tenant:{tenant_id}:filters:{hashlib.md5(filters_str.encode()).hexdigest()}"
        return await self.get(key)
    
    async def set_product_variants(self, tenant_id: int, variants: List[Dict], filters: Dict = None, ttl: int = 120) -> bool:
        """设置产品变体缓存"""
        filters_str = json.dumps(filters or {}, sort_keys=True)
        key = f"product_variants:tenant:{tenant_id}:filters:{hashlib.md5(filters_str.encode()).hexdigest()}"
        return await self.set(key, variants, ttl)
    
    async def invalidate_product_variants(self, tenant_id: int) -> bool:
        """使产品变体缓存失效"""
        pattern = f"product_variants:tenant:{tenant_id}:*"
        return await self.invalidate_pattern(pattern) > 0


# 全局缓存管理器实例
cache_manager = CacheManager()
