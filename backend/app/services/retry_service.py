"""
重试服务
提供通用的失败操作重试机制，支持指数退避、重试策略和错误恢复
"""

from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
import asyncio
import random
import math

from app.core.logging import get_logger

logger = get_logger(__name__)


class RetryStrategy(Enum):
    """重试策略"""
    FIXED = "fixed"           # 固定间隔
    EXPONENTIAL = "exponential"  # 指数退避
    LINEAR = "linear"         # 线性增长
    RANDOM = "random"         # 随机间隔


class RetryStatus(Enum):
    """重试状态"""
    PENDING = "pending"       # 待重试
    IN_PROGRESS = "in_progress"  # 重试中
    SUCCESS = "success"       # 成功
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"   # 已取消


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    jitter: bool = True
    backoff_multiplier: float = 2.0
    retry_on_exceptions: List[type] = None
    stop_on_exceptions: List[type] = None


@dataclass
class RetryTask:
    """重试任务"""
    task_id: str
    operation_name: str
    operation: Callable
    args: tuple
    kwargs: dict
    config: RetryConfig
    status: RetryStatus
    current_attempt: int = 0
    total_attempts: int = 0
    last_error: Optional[Exception] = None
    created_at: datetime = None
    updated_at: datetime = None
    next_retry_at: Optional[datetime] = None
    result: Optional[Any] = None


class RetryService:
    """重试服务"""
    
    def __init__(self):
        self.retry_tasks = {}  # 重试任务队列
        self.retry_history = {}  # 重试历史记录
        self.default_config = RetryConfig()
    
    async def execute_with_retry(
        self,
        operation: Callable,
        operation_name: str = "操作",
        args: tuple = (),
        kwargs: dict = None,
        config: Optional[RetryConfig] = None
    ) -> Dict[str, Any]:
        """
        执行带重试的操作
        
        Args:
            operation: 要执行的操作
            operation_name: 操作名称
            args: 位置参数
            kwargs: 关键字参数
            config: 重试配置
            
        Returns:
            执行结果
        """
        if kwargs is None:
            kwargs = {}
        
        if config is None:
            config = self.default_config
        
        task_id = f"{operation_name}_{datetime.now().timestamp()}_{random.randint(1000, 9999)}"
        
        # 创建重试任务
        task = RetryTask(
            task_id=task_id,
            operation_name=operation_name,
            operation=operation,
            args=args,
            kwargs=kwargs,
            config=config,
            status=RetryStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.retry_tasks[task_id] = task
        
        try:
            logger.info(
                f"🔍 开始执行带重试的操作: {operation_name}",
                task_id=task_id
            )
            
            # 执行操作
            result = await self._execute_operation_with_retry(task)
            
            if result.get("success"):
                task.status = RetryStatus.SUCCESS
                task.result = result.get("data")
                logger.info(
                    f"✅ 操作执行成功: {operation_name}",
                    task_id=task_id,
                    attempts=task.total_attempts
                )
            else:
                task.status = RetryStatus.FAILED
                logger.error(
                    f"❌ 操作执行失败: {operation_name}",
                    task_id=task_id,
                    attempts=task.total_attempts,
                    error=result.get("error")
                )
            
            task.updated_at = datetime.utcnow()
            
            # 记录重试历史
            self._record_retry_history(task)
            
            return result
            
        except Exception as e:
            task.status = RetryStatus.FAILED
            task.last_error = e
            task.updated_at = datetime.utcnow()
            
            logger.error(
                f"❌ 操作执行异常: {operation_name}",
                task_id=task_id,
                error=str(e)
            )
            import traceback
            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            
            # 记录重试历史
            self._record_retry_history(task)
            
            return {
                "success": False,
                "message": f"操作执行异常: {str(e)}",
                "error": str(e),
                "task_id": task_id
            }
    
    async def _execute_operation_with_retry(self, task: RetryTask) -> Dict[str, Any]:
        """执行带重试的操作"""
        last_error = None
        
        for attempt in range(task.config.max_retries + 1):
            try:
                task.current_attempt = attempt + 1
                task.total_attempts += 1
                task.updated_at = datetime.utcnow()
                
                logger.info(
                    f"🔍 执行操作尝试 {task.current_attempt}/{task.config.max_retries + 1}",
                    operation_name=task.operation_name,
                    task_id=task.task_id
                )
                
                # 执行操作
                if asyncio.iscoroutinefunction(task.operation):
                    result = await task.operation(*task.args, **task.kwargs)
                else:
                    result = task.operation(*task.args, **task.kwargs)
                
                # 操作成功
                logger.info(
                    f"✅ 操作执行成功",
                    operation_name=task.operation_name,
                    task_id=task.task_id,
                    attempt=task.current_attempt
                )
                
                return {
                    "success": True,
                    "message": f"操作执行成功 (尝试 {task.current_attempt})",
                    "data": result,
                    "attempts": task.current_attempt
                }
                
            except Exception as e:
                last_error = e
                task.last_error = e
                
                logger.warning(
                    f"⚠️ 操作执行失败 (尝试 {task.current_attempt})",
                    operation_name=task.operation_name,
                    task_id=task.task_id,
                    error=str(e)
                )
                
                # 检查是否应该停止重试
                if self._should_stop_retry(e, task.config):
                    logger.error(
                        f"❌ 遇到不可重试的异常，停止重试",
                        operation_name=task.operation_name,
                        task_id=task.task_id,
                        error=str(e)
                    )
                    break
                
                # 检查是否还有重试机会
                if attempt >= task.config.max_retries:
                    logger.error(
                        f"❌ 已达到最大重试次数，停止重试",
                        operation_name=task.operation_name,
                        task_id=task.task_id,
                        max_retries=task.config.max_retries
                    )
                    break
                
                # 计算重试延迟
                delay = self._calculate_retry_delay(attempt, task.config)
                
                logger.info(
                    f"⏳ {delay} 秒后重试",
                    operation_name=task.operation_name,
                    task_id=task.task_id,
                    next_attempt=attempt + 2
                )
                
                # 等待重试
                await asyncio.sleep(delay)
        
        # 所有重试都失败了
        return {
            "success": False,
            "message": f"操作执行失败，已重试 {task.total_attempts} 次",
            "error": str(last_error) if last_error else "未知错误",
            "attempts": task.total_attempts,
            "last_error": str(last_error) if last_error else None
        }
    
    def _should_stop_retry(self, exception: Exception, config: RetryConfig) -> bool:
        """检查是否应该停止重试"""
        if config.stop_on_exceptions:
            for stop_exception in config.stop_on_exceptions:
                if isinstance(exception, stop_exception):
                    return True
        
        return False
    
    def _calculate_retry_delay(self, attempt: int, config: RetryConfig) -> float:
        """计算重试延迟"""
        if config.strategy == RetryStrategy.FIXED:
            delay = config.base_delay
        elif config.strategy == RetryStrategy.EXPONENTIAL:
            delay = config.base_delay * (config.backoff_multiplier ** attempt)
        elif config.strategy == RetryStrategy.LINEAR:
            delay = config.base_delay * (attempt + 1)
        elif config.strategy == RetryStrategy.RANDOM:
            delay = random.uniform(config.base_delay, config.base_delay * 2)
        else:
            delay = config.base_delay
        
        # 限制最大延迟
        delay = min(delay, config.max_delay)
        
        # 添加抖动
        if config.jitter:
            jitter = random.uniform(0, delay * 0.1)
            delay += jitter
        
        return delay
    
    def _record_retry_history(self, task: RetryTask):
        """记录重试历史"""
        self.retry_history[task.task_id] = {
            "task_id": task.task_id,
            "operation_name": task.operation_name,
            "status": task.status.value,
            "total_attempts": task.total_attempts,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "last_error": str(task.last_error) if task.last_error else None,
            "result": task.result
        }
    
    async def retry_failed_tasks(self, max_tasks: int = 10) -> Dict[str, Any]:
        """重试失败的任务"""
        try:
            logger.info(f"🔍 开始重试失败的任务，最大处理数量: {max_tasks}")
            
            # 获取失败的任务
            failed_tasks = [
                task for task in self.retry_tasks.values()
                if task.status == RetryStatus.FAILED
            ][:max_tasks]
            
            if not failed_tasks:
                return {
                    "success": True,
                    "message": "没有失败的任务需要重试",
                    "retried_count": 0
                }
            
            # 重试失败的任务
            retry_results = []
            for task in failed_tasks:
                try:
                    # 重置任务状态
                    task.status = RetryStatus.PENDING
                    task.current_attempt = 0
                    task.last_error = None
                    task.updated_at = datetime.utcnow()
                    
                    # 重新执行任务
                    result = await self._execute_operation_with_retry(task)
                    retry_results.append(result)
                    
                except Exception as e:
                    logger.error(
                        f"❌ 重试任务失败: {task.operation_name}",
                        task_id=task.task_id,
                        error=str(e)
                    )
                    retry_results.append({
                        "success": False,
                        "message": f"重试失败: {str(e)}",
                        "error": str(e)
                    })
            
            # 统计结果
            success_count = sum(1 for r in retry_results if r.get("success"))
            error_count = len(retry_results) - success_count
            
            return {
                "success": True,
                "message": f"重试完成: {success_count}成功, {error_count}失败",
                "retried_count": len(failed_tasks),
                "success_count": success_count,
                "error_count": error_count,
                "results": retry_results
            }
            
        except Exception as e:
            logger.error(f"❌ 重试失败任务异常: {str(e)}")
            return {
                "success": False,
                "message": f"重试失败任务异常: {str(e)}",
                "error": str(e)
            }
    
    def get_retry_statistics(self) -> Dict[str, Any]:
        """获取重试统计信息"""
        total_tasks = len(self.retry_tasks)
        success_tasks = len([t for t in self.retry_tasks.values() if t.status == RetryStatus.SUCCESS])
        failed_tasks = len([t for t in self.retry_tasks.values() if t.status == RetryStatus.FAILED])
        pending_tasks = len([t for t in self.retry_tasks.values() if t.status == RetryStatus.PENDING])
        
        return {
            "total_tasks": total_tasks,
            "success_tasks": success_tasks,
            "failed_tasks": failed_tasks,
            "pending_tasks": pending_tasks,
            "success_rate": (success_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            "failure_rate": (failed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        }
    
    def get_retry_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取重试历史"""
        history_items = list(self.retry_history.values())
        history_items.sort(key=lambda x: x["updated_at"], reverse=True)
        return history_items[:limit]
    
    def clear_retry_history(self, older_than_days: int = 7):
        """清理重试历史"""
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        
        # 清理任务
        tasks_to_remove = []
        for task_id, task in self.retry_tasks.items():
            if task.updated_at < cutoff_date:
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.retry_tasks[task_id]
        
        # 清理历史记录
        history_to_remove = []
        for task_id, history in self.retry_history.items():
            if history["updated_at"] < cutoff_date:
                history_to_remove.append(task_id)
        
        for task_id in history_to_remove:
            del self.retry_history[task_id]
        
        logger.info(
            f"🧹 清理重试历史完成",
            removed_tasks=len(tasks_to_remove),
            removed_history=len(history_to_remove)
        )


# 全局重试服务实例
retry_service = RetryService()


async def execute_with_retry(
    operation: Callable,
    operation_name: str = "操作",
    args: tuple = (),
    kwargs: dict = None,
    config: Optional[RetryConfig] = None
) -> Dict[str, Any]:
    """
    执行带重试的操作的便捷函数
    
    Args:
        operation: 要执行的操作
        operation_name: 操作名称
        args: 位置参数
        kwargs: 关键字参数
        config: 重试配置
        
    Returns:
        执行结果
    """
    return await retry_service.execute_with_retry(
        operation, operation_name, args, kwargs, config
    )
