"""
统一错误处理系统

提供全局错误处理、错误分类、错误上报和用户友好的错误响应
"""

import traceback
import logging
from typing import Any, Dict, Optional, Union
from datetime import datetime
from enum import Enum

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import ValidationError

from app.core.logging import get_logger

logger = get_logger(__name__)


class ErrorType(Enum):
    """错误类型枚举"""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    NOT_FOUND_ERROR = "NOT_FOUND_ERROR"
    CONFLICT_ERROR = "CONFLICT_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class ErrorSeverity(Enum):
    """错误严重程度枚举"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ErrorInfo:
    """错误信息类"""
    
    def __init__(
        self,
        error_type: ErrorType,
        severity: ErrorSeverity,
        message: str,
        user_message: str,
        code: Optional[Union[str, int]] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        tenant_id: Optional[int] = None,
        user_id: Optional[int] = None
    ):
        self.error_type = error_type
        self.severity = severity
        self.message = message
        self.user_message = user_message
        self.code = code
        self.details = details or {}
        self.request_id = request_id
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.timestamp = datetime.utcnow()
        self.traceback = traceback.format_exc()


class ErrorHandler:
    """统一错误处理器"""
    
    def __init__(self):
        self.error_stats = {}
        self.error_queue = []
    
    def handle_error(
        self,
        error: Exception,
        request: Optional[Request] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ErrorInfo:
        """处理错误并返回错误信息"""
        
        # 确定错误类型和严重程度
        error_type, severity = self._classify_error(error)
        
        # 生成用户友好的错误消息
        user_message = self._get_user_friendly_message(error_type, error)
        
        # 提取请求信息
        request_id = getattr(request, 'id', None) if request else None
        tenant_id = getattr(request, 'tenant_id', None) if request else None
        user_id = getattr(request, 'user_id', None) if request else None
        
        # 创建错误信息
        error_info = ErrorInfo(
            error_type=error_type,
            severity=severity,
            message=str(error),
            user_message=user_message,
            code=getattr(error, 'status_code', None),
            details={
                'context': context,
                'request_url': str(request.url) if request else None,
                'request_method': request.method if request else None,
                'user_agent': request.headers.get('user-agent') if request else None,
            },
            request_id=request_id,
            tenant_id=tenant_id,
            user_id=user_id
        )
        
        # 记录错误
        self._log_error(error_info)
        
        # 更新统计
        self._update_stats(error_info)
        
        # 添加到错误队列
        self.error_queue.append(error_info)
        
        return error_info
    
    def _classify_error(self, error: Exception) -> tuple[ErrorType, ErrorSeverity]:
        """分类错误类型和严重程度"""
        
        if isinstance(error, RequestValidationError):
            return ErrorType.VALIDATION_ERROR, ErrorSeverity.LOW
        
        if isinstance(error, HTTPException):
            if error.status_code == 401:
                return ErrorType.AUTHENTICATION_ERROR, ErrorSeverity.HIGH
            elif error.status_code == 403:
                return ErrorType.AUTHORIZATION_ERROR, ErrorSeverity.HIGH
            elif error.status_code == 404:
                return ErrorType.NOT_FOUND_ERROR, ErrorSeverity.MEDIUM
            elif error.status_code == 409:
                return ErrorType.CONFLICT_ERROR, ErrorSeverity.MEDIUM
            elif error.status_code == 429:
                return ErrorType.RATE_LIMIT_ERROR, ErrorSeverity.MEDIUM
            elif error.status_code >= 500:
                return ErrorType.INTERNAL_SERVER_ERROR, ErrorSeverity.CRITICAL
            else:
                return ErrorType.UNKNOWN_ERROR, ErrorSeverity.MEDIUM
        
        if isinstance(error, IntegrityError):
            return ErrorType.DATABASE_ERROR, ErrorSeverity.HIGH
        
        if isinstance(error, SQLAlchemyError):
            return ErrorType.DATABASE_ERROR, ErrorSeverity.HIGH
        
        if isinstance(error, ValidationError):
            return ErrorType.VALIDATION_ERROR, ErrorSeverity.LOW
        
        # 检查是否是外部服务错误
        if hasattr(error, 'external_service'):
            return ErrorType.EXTERNAL_SERVICE_ERROR, ErrorSeverity.MEDIUM
        
        return ErrorType.UNKNOWN_ERROR, ErrorSeverity.MEDIUM
    
    def _get_user_friendly_message(self, error_type: ErrorType, error: Exception) -> str:
        """获取用户友好的错误消息"""
        
        messages = {
            ErrorType.VALIDATION_ERROR: "输入信息有误，请检查后重新提交",
            ErrorType.AUTHENTICATION_ERROR: "登录已过期，请重新登录",
            ErrorType.AUTHORIZATION_ERROR: "权限不足，请联系管理员",
            ErrorType.NOT_FOUND_ERROR: "请求的资源不存在",
            ErrorType.CONFLICT_ERROR: "数据冲突，请刷新后重试",
            ErrorType.DATABASE_ERROR: "数据操作失败，请稍后重试",
            ErrorType.EXTERNAL_SERVICE_ERROR: "外部服务暂时不可用，请稍后重试",
            ErrorType.INTERNAL_SERVER_ERROR: "服务器内部错误，请稍后重试",
            ErrorType.RATE_LIMIT_ERROR: "请求过于频繁，请稍后重试",
            ErrorType.UNKNOWN_ERROR: "系统出现异常，请稍后重试"
        }
        
        # 如果有自定义消息，使用自定义消息
        if hasattr(error, 'detail') and isinstance(error.detail, str):
            return error.detail
        
        return messages.get(error_type, "系统出现异常，请稍后重试")
    
    def _log_error(self, error_info: ErrorInfo):
        """记录错误日志"""
        
        log_data = {
            'error_type': error_info.error_type.value,
            'severity': error_info.severity.value,
            'message': error_info.message,
            'user_message': error_info.user_message,
            'code': error_info.code,
            'request_id': error_info.request_id,
            'tenant_id': error_info.tenant_id,
            'user_id': error_info.user_id,
            'timestamp': error_info.timestamp.isoformat(),
            'details': error_info.details
        }
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            logger.error("严重错误", **log_data, stack=error_info.traceback)
        elif error_info.severity == ErrorSeverity.HIGH:
            logger.error("高级错误", **log_data)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            logger.warning("中级错误", **log_data)
        else:
            logger.info("低级错误", **log_data)
    
    def _update_stats(self, error_info: ErrorInfo):
        """更新错误统计"""
        
        error_type = error_info.error_type.value
        severity = error_info.severity.value
        
        if error_type not in self.error_stats:
            self.error_stats[error_type] = {'count': 0, 'severities': {}}
        
        self.error_stats[error_type]['count'] += 1
        
        if severity not in self.error_stats[error_type]['severities']:
            self.error_stats[error_type]['severities'][severity] = 0
        
        self.error_stats[error_type]['severities'][severity] += 1
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        return {
            'total_errors': len(self.error_queue),
            'error_types': self.error_stats,
            'recent_errors': [
                {
                    'error_type': error.error_type.value,
                    'severity': error.severity.value,
                    'message': error.message,
                    'timestamp': error.timestamp.isoformat(),
                    'request_id': error.request_id
                }
                for error in self.error_queue[-10:]  # 最近10个错误
            ]
        }
    
    def clear_error_queue(self):
        """清理错误队列"""
        self.error_queue.clear()


# 全局错误处理器实例
error_handler = ErrorHandler()


# 错误处理装饰器
def handle_errors(func):
    """错误处理装饰器"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # 获取请求对象（如果存在）
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            # 处理错误
            error_info = error_handler.handle_error(e, request)
            
            # 返回适当的HTTP响应
            return create_error_response(error_info)
    
    return wrapper


def create_error_response(error_info: ErrorInfo) -> JSONResponse:
    """创建错误响应"""
    
    # 确定HTTP状态码
    status_code = get_http_status_code(error_info.error_type)
    
    # 构建响应数据
    response_data = {
        'error': {
            'type': error_info.error_type.value,
            'message': error_info.user_message,
            'code': error_info.code,
            'timestamp': error_info.timestamp.isoformat(),
            'request_id': error_info.request_id
        }
    }
    
    # 在开发环境中包含详细信息
    if logger.level <= logging.DEBUG:
        response_data['error']['details'] = error_info.details
        response_data['error']['traceback'] = error_info.traceback
    
    return JSONResponse(
        status_code=status_code,
        content=response_data
    )


def get_http_status_code(error_type: ErrorType) -> int:
    """根据错误类型获取HTTP状态码"""
    
    status_mapping = {
        ErrorType.VALIDATION_ERROR: status.HTTP_422_UNPROCESSABLE_ENTITY,
        ErrorType.AUTHENTICATION_ERROR: status.HTTP_401_UNAUTHORIZED,
        ErrorType.AUTHORIZATION_ERROR: status.HTTP_403_FORBIDDEN,
        ErrorType.NOT_FOUND_ERROR: status.HTTP_404_NOT_FOUND,
        ErrorType.CONFLICT_ERROR: status.HTTP_409_CONFLICT,
        ErrorType.DATABASE_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
        ErrorType.EXTERNAL_SERVICE_ERROR: status.HTTP_502_BAD_GATEWAY,
        ErrorType.INTERNAL_SERVER_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
        ErrorType.RATE_LIMIT_ERROR: status.HTTP_429_TOO_MANY_REQUESTS,
        ErrorType.UNKNOWN_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR
    }
    
    return status_mapping.get(error_type, status.HTTP_500_INTERNAL_SERVER_ERROR)


# 全局异常处理器
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """全局异常处理器"""
    error_info = error_handler.handle_error(exc, request)
    return create_error_response(error_info)


# 验证错误处理器
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """验证错误处理器"""
    error_info = error_handler.handle_error(exc, request)
    
    # 为验证错误添加字段级别的错误信息
    if exc.errors():
        error_info.details['validation_errors'] = exc.errors()
    
    return create_error_response(error_info)


# HTTP异常处理器
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTP异常处理器"""
    error_info = error_handler.handle_error(exc, request)
    return create_error_response(error_info)
