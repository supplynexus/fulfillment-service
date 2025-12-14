"""
自定义 Celery 结果后端
确保异常信息格式正确，包含所有必要字段
"""
from celery.backends.redis import RedisBackend
from kombu.utils.encoding import bytes_to_str
import json
import traceback


class CustomRedisBackend(RedisBackend):
    """自定义 Redis 后端，确保异常信息格式正确"""
    
    def exception_to_python(self, exc):
        """
        将异常信息转换为 Python 异常对象
        确保异常信息包含所有必要字段
        """
        if exc is None:
            return None
        
        # 如果 exc 是字符串，尝试解析
        if isinstance(exc, str):
            try:
                exc = json.loads(exc)
            except (json.JSONDecodeError, TypeError):
                # 如果无法解析，返回一个默认的异常
                return RuntimeError(exc)
        
        # 如果 exc 是字典，检查是否包含必要字段
        if isinstance(exc, dict):
            # 确保包含 exc_type 字段
            if 'exc_type' not in exc:
                # 如果没有 exc_type，尝试从其他字段推断
                if 'error_type' in exc:
                    exc['exc_type'] = exc['error_type']
                elif 'error' in exc:
                    exc['exc_type'] = type(exc['error']).__name__ if hasattr(exc['error'], '__class__') else 'Exception'
                else:
                    exc['exc_type'] = 'RuntimeError'
            
            # 确保包含 exc_message 字段
            if 'exc_message' not in exc:
                if 'error_message' in exc:
                    exc['exc_message'] = exc['error_message']
                elif 'error' in exc:
                    exc['exc_message'] = str(exc['error'])
                elif 'message' in exc:
                    exc['exc_message'] = exc['message']
                else:
                    exc['exc_message'] = 'Unknown error'
            
            # 确保包含 exc_module 字段（可选，但有助于调试）
            if 'exc_module' not in exc:
                exc['exc_module'] = 'builtins'
        
        # 调用父类方法
        try:
            return super().exception_to_python(exc)
        except (KeyError, ValueError) as e:
            # 如果父类方法失败，返回一个包装的异常
            if isinstance(exc, dict):
                error_type = exc.get('exc_type', 'Exception')
                error_message = exc.get('exc_message', str(exc))
            else:
                error_type = 'Exception'
                error_message = str(exc)
            return RuntimeError(f"{error_type}: {error_message}")

