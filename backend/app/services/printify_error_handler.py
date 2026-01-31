"""
Printify API 错误处理服务
提供统一的错误处理、重试机制和错误恢复功能
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class PrintifyErrorHandler:
    """Printify API 错误处理器"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.rate_limit_delay = 60.0  # API限流等待时间（秒）
    
    async def execute_with_retry(
        self, 
        operation: Callable, 
        operation_name: str = "Printify API操作",
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行Printify API操作，带重试机制
        
        Args:
            operation: 要执行的操作函数
            operation_name: 操作名称，用于日志
            **kwargs: 传递给操作的参数
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"🔍 开始执行{operation_name} (尝试 {attempt + 1}/{self.max_retries + 1})")
                
                result = await operation(**kwargs)
                
                if attempt > 0:
                    logger.info(f"✅ {operation_name}成功 (重试后)")
                else:
                    logger.info(f"✅ {operation_name}成功")
                
                return result
                
            except httpx.HTTPStatusError as e:
                last_exception = e
                error_info = self._analyze_http_error(e)
                
                logger.warning(f"⚠️ {operation_name} HTTP错误 (尝试 {attempt + 1}): {error_info['message']}")
                
                # 检查是否应该重试
                if not self._should_retry(e, attempt):
                    logger.error(f"❌ {operation_name}失败，不满足重试条件: {error_info['message']}")
                    raise HTTPException(
                        status_code=error_info['status_code'],
                        detail=error_info['message']
                    )
                
                # 特殊处理API限流
                if e.response.status_code == 429:
                    retry_after = self._get_retry_after(e.response)
                    wait_time = min(retry_after, self.rate_limit_delay)
                    logger.warning(f"⏳ API限流，等待 {wait_time} 秒后重试")
                    await asyncio.sleep(wait_time)
                    continue
                
                # 计算重试延迟
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.info(f"⏳ {delay} 秒后重试")
                    await asyncio.sleep(delay)
                
            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(f"⚠️ {operation_name}超时 (尝试 {attempt + 1})")
                
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.info(f"⏳ 超时后 {delay} 秒重试")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"❌ {operation_name}超时，已达到最大重试次数")
                    raise HTTPException(
                        status_code=408,
                        detail="Printify API调用超时，请稍后重试"
                    )
                    
            except httpx.RequestError as e:
                last_exception = e
                logger.warning(f"⚠️ {operation_name}请求错误 (尝试 {attempt + 1}): {str(e)}")
                
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.info(f"⏳ 请求错误后 {delay} 秒重试")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"❌ {operation_name}请求错误，已达到最大重试次数: {str(e)}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Printify API请求失败: {str(e)}"
                    )
                    
            except Exception as e:
                last_exception = e
                logger.error(f"❌ {operation_name}发生未知错误: {str(e)}")
                import traceback
                logger.error(f"   异常堆栈: {traceback.format_exc()}")
                raise HTTPException(
                    status_code=500,
                    detail=f"{operation_name}失败: {str(e)}"
                )
        
        # 所有重试都失败了
        logger.error(f"❌ {operation_name}失败，已达到最大重试次数")
        if isinstance(last_exception, httpx.HTTPStatusError):
            error_info = self._analyze_http_error(last_exception)
            raise HTTPException(
                status_code=error_info['status_code'],
                detail=f"{operation_name}失败: {error_info['message']}"
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"{operation_name}失败: {str(last_exception)}"
            )
    
    def _analyze_http_error(self, error: httpx.HTTPStatusError) -> Dict[str, Any]:
        """分析HTTP错误并返回错误信息"""
        status_code = error.response.status_code
        response_text = error.response.text
        
        logger.info(f"🔍 分析HTTP错误: status_code={status_code}, response={response_text}")
        
        error_messages = {
            400: "请求参数错误，请检查请求数据",
            401: "Printify访问令牌无效或已过期，请重新配置",
            403: "没有权限访问此Printify商店，请检查商店权限",
            404: "Printify商店不存在或资源未找到，请检查配置",
            429: "API调用频率超限，请稍后重试",
            500: "Printify服务器内部错误，请稍后重试",
            502: "Printify服务暂时不可用，请稍后重试",
            503: "Printify服务维护中，请稍后重试",
        }
        
        message = error_messages.get(status_code, f"Printify API错误: {status_code}")
        
        # 尝试从响应中提取更详细的错误信息
        try:
            if response_text:
                import json
                error_data = json.loads(response_text)
                if isinstance(error_data, dict) and 'message' in error_data:
                    message = f"{message}: {error_data['message']}"
        except:
            pass
        
        return {
            'status_code': status_code,
            'message': message,
            'response_text': response_text
        }
    
    def _should_retry(self, error: httpx.HTTPStatusError, attempt: int) -> bool:
        """判断是否应该重试"""
        status_code = error.response.status_code
        
        # 不应该重试的状态码
        no_retry_codes = {400, 401, 403, 404}
        
        if status_code in no_retry_codes:
            return False
        
        # 应该重试的状态码
        retry_codes = {408, 429, 500, 502, 503, 504}
        
        if status_code in retry_codes:
            return True
        
        # 其他情况，根据重试次数决定
        return attempt < self.max_retries
    
    def _calculate_delay(self, attempt: int) -> float:
        """计算重试延迟时间（指数退避）"""
        delay = self.base_delay * (2 ** attempt)
        return min(delay, self.max_delay)
    
    def _get_retry_after(self, response: httpx.Response) -> float:
        """从响应头获取重试等待时间"""
        retry_after = response.headers.get('Retry-After')
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                pass
        return self.rate_limit_delay


# 全局错误处理器实例
printify_error_handler = PrintifyErrorHandler(
    max_retries=3,
    base_delay=1.0,
    max_delay=60.0
)


async def execute_printify_operation(
    operation: Callable,
    operation_name: str = "Printify API操作",
    **kwargs
) -> Dict[str, Any]:
    """
    执行Printify操作的便捷函数
    
    Args:
        operation: 要执行的操作函数
        operation_name: 操作名称
        **kwargs: 传递给操作的参数
        
    Returns:
        Dict[str, Any]: 操作结果
    """
    return await printify_error_handler.execute_with_retry(
        operation, operation_name, **kwargs
    )
