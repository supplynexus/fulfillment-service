"""
HTTP客户端重试工具
提供带有指数退避的智能重试机制，特别针对Shopify API的速率限制
"""

import asyncio
import aiohttp
import logging
from typing import Optional, Dict, Any, Callable, Union
from aiohttp import ClientTimeout, ClientResponse, ClientSession
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)


class RetryConfig:
    """重试配置"""
    
    def __init__(
        self,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_on_status_codes: list = None
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_on_status_codes = retry_on_status_codes or [429, 500, 502, 503, 504]
    
    def get_delay(self, attempt: int) -> float:
        """计算延迟时间（指数退避 + 抖动）"""
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        
        if self.jitter:
            # 添加随机抖动，避免多个请求同时重试
            jitter_factor = 0.1 * delay
            delay += random.uniform(-jitter_factor, jitter_factor)
            delay = max(0.1, delay)  # 确保最小延迟
        
        return delay


class RetryableHTTPClient:
    """可重试的HTTP客户端"""
    
    def __init__(self, retry_config: Optional[RetryConfig] = None):
        self.retry_config = retry_config or RetryConfig()
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, aiohttp.ClientTimeout]] = None,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """
        发送HTTP请求，支持自动重试
        
        Args:
            method: HTTP方法
            url: 请求URL
            headers: 请求头
            json_data: JSON数据
            data: 表单数据
            timeout: 超时时间
            **kwargs: 其他aiohttp参数
        
        Returns:
            aiohttp.ClientResponse
            
        Raises:
            Exception: 当重试次数用尽后仍然失败
        """
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        last_exception = None
        
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                # 准备请求参数
                request_kwargs = {
                    'method': method,
                    'url': url,
                    'timeout': timeout or aiohttp.ClientTimeout(total=30),
                    **kwargs
                }
                
                if headers:
                    request_kwargs['headers'] = headers
                if json_data:
                    request_kwargs['json'] = json_data
                if data:
                    request_kwargs['data'] = data
                
                # 发送请求
                response = await self.session.request(**request_kwargs)
                
                # 检查是否需要重试
                if response.status in self.retry_config.retry_on_status_codes:
                    if attempt < self.retry_config.max_retries:
                        delay = self.retry_config.get_delay(attempt)
                        
                        # 记录重试信息
                        if response.status == 429:
                            logger.warning(
                                f"Rate limit hit (429) on attempt {attempt + 1}/{self.retry_config.max_retries + 1}. "
                                f"Retrying in {delay:.2f}s. URL: {url}"
                            )
                        else:
                            logger.warning(
                                f"HTTP {response.status} on attempt {attempt + 1}/{self.retry_config.max_retries + 1}. "
                                f"Retrying in {delay:.2f}s. URL: {url}"
                            )
                        
                        # 关闭响应，避免资源泄漏
                        response.close()
                        
                        # 等待后重试
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # 重试次数用尽
                        error_text = await response.text()
                        response.close()
                        raise Exception(
                            f"Max retries ({self.retry_config.max_retries}) exceeded. "
                            f"Last status: {response.status}, Response: {error_text}"
                        )
                else:
                    # 请求成功或不需要重试的错误
                    return response
                    
            except asyncio.TimeoutError as e:
                last_exception = e
                if attempt < self.retry_config.max_retries:
                    delay = self.retry_config.get_delay(attempt)
                    logger.warning(
                        f"Timeout on attempt {attempt + 1}/{self.retry_config.max_retries + 1}. "
                        f"Retrying in {delay:.2f}s. URL: {url}"
                    )
                    await asyncio.sleep(delay)
                else:
                    raise Exception(f"Max retries exceeded due to timeout. URL: {url}") from e
                    
            except aiohttp.ClientError as e:
                last_exception = e
                if attempt < self.retry_config.max_retries:
                    delay = self.retry_config.get_delay(attempt)
                    logger.warning(
                        f"Client error on attempt {attempt + 1}/{self.retry_config.max_retries + 1}: {e}. "
                        f"Retrying in {delay:.2f}s. URL: {url}"
                    )
                    await asyncio.sleep(delay)
                else:
                    raise Exception(f"Max retries exceeded due to client error. URL: {url}") from e
        
        # 如果所有重试都失败了
        if last_exception:
            raise last_exception
        else:
            raise Exception(f"Unexpected error during request. URL: {url}")
    
    async def get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """GET请求"""
        return await self.request('GET', url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """POST请求"""
        return await self.request('POST', url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """PUT请求"""
        return await self.request('PUT', url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """DELETE请求"""
        return await self.request('DELETE', url, **kwargs)


def create_shopify_retry_config() -> RetryConfig:
    """创建针对Shopify API优化的重试配置"""
    return RetryConfig(
        max_retries=5,
        base_delay=2.0,  # 基础延迟2秒
        max_delay=60.0,  # 最大延迟60秒
        exponential_base=2.0,  # 指数退避基数
        jitter=True,  # 启用抖动
        retry_on_status_codes=[429, 500, 502, 503, 504]  # Shopify常见的需要重试的状态码
    )


async def retry_async_function(
    func: Callable,
    *args,
    retry_config: Optional[RetryConfig] = None,
    **kwargs
) -> Any:
    """
    通用的异步函数重试装饰器
    
    Args:
        func: 要重试的异步函数
        *args: 函数参数
        retry_config: 重试配置
        **kwargs: 函数关键字参数
    
    Returns:
        函数执行结果
    
    Raises:
        Exception: 当重试次数用尽后仍然失败
    """
    if retry_config is None:
        retry_config = RetryConfig()
    
    last_exception = None
    
    for attempt in range(retry_config.max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            
            # 检查是否需要重试
            should_retry = False
            
            # 检查是否是HTTP错误
            if hasattr(e, 'status'):
                should_retry = e.status in retry_config.retry_on_status_codes
            elif hasattr(e, 'code'):
                should_retry = e.code in retry_config.retry_on_status_codes
            else:
                # 对于其他异常，检查错误消息
                error_msg = str(e).lower()
                should_retry = any(
                    keyword in error_msg 
                    for keyword in ['timeout', 'connection', 'rate limit', '429', '500', '502', '503', '504']
                )
            
            if should_retry and attempt < retry_config.max_retries:
                delay = retry_config.get_delay(attempt)
                logger.warning(
                    f"Function {func.__name__} failed on attempt {attempt + 1}/{retry_config.max_retries + 1}: {e}. "
                    f"Retrying in {delay:.2f}s."
                )
                await asyncio.sleep(delay)
            else:
                # 不需要重试或重试次数用尽
                break
    
    # 如果所有重试都失败了
    if last_exception:
        raise last_exception
    else:
        raise Exception(f"Unexpected error in function {func.__name__}")


def retry_async(max_retries: int = 5, base_delay: float = 1.0, max_delay: float = 60.0):
    """
    异步函数重试装饰器
    
    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟时间
        max_delay: 最大延迟时间
    
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            retry_config = RetryConfig(
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay
            )
            return await retry_async_function(func, *args, retry_config=retry_config, **kwargs)
        return wrapper
    return decorator
