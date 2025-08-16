"""
请求中间件 - 自动生成和设置请求ID
"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import generate_request_id, set_request_id, get_request_id, RequestLogger


class RequestIDMiddleware(BaseHTTPMiddleware):
    """请求ID中间件"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = RequestLogger(__name__)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 生成请求ID
        request_id = generate_request_id()
        set_request_id(request_id)
        
        # 记录请求开始
        start_time = time.time()
        self.logger.info(
            "Request started",
            method=request.method,
            url=str(request.url),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            request_id=request_id
        )
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 记录请求完成
            duration = time.time() - start_time
            self.logger.info(
                "Request completed",
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                duration=f"{duration:.3f}s",
                request_id=request_id
            )
            
            # 在响应头中添加请求ID（可选）
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # 记录请求错误
            duration = time.time() - start_time
            self.logger.error(
                "Request failed",
                method=request.method,
                url=str(request.url),
                error=str(e),
                duration=f"{duration:.3f}s",
                request_id=request_id,
                exc_info=True
            )
            raise
