"""
Celery application configuration
"""

import os
from celery import Celery
from app.core.config import settings
from app.core.logging import get_logger
from app.tasks.celery_beat_schedule import CELERY_BEAT_SCHEDULE

# Create Celery app
celery_app = Celery(
    "fulfillment_service",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.shopify_tasks",
        "app.tasks.order_tasks",
        "app.tasks.order_automation_tasks",
    ],
)

# Import beat schedule
from app.tasks.celery_beat_schedule import CELERY_BEAT_SCHEDULE

# 合并静态和动态调度配置
def get_combined_beat_schedule():
    """
    合并静态和动态Celery Beat调度配置
    动态配置从数据库读取，静态配置来自celery_beat_schedule.py
    """
    from app.core.database import get_sync_db
    from app.services.automation_scheduler_service import get_dynamic_beat_schedule
    
    logger = get_logger(__name__)
    
    # 获取静态配置
    combined_schedule = CELERY_BEAT_SCHEDULE.copy()
    
    # 尝试获取动态配置（如果数据库可用）
    try:
        db = next(get_sync_db())
        dynamic_schedule = get_dynamic_beat_schedule(db)
        db.close()
        
        # 合并动态配置（动态配置优先级更高，会覆盖同名的静态配置）
        combined_schedule.update(dynamic_schedule)
        
        logger.info(
            f"✅ Celery Beat调度配置合并完成: 静态={len(CELERY_BEAT_SCHEDULE)}, "
            f"动态={len(dynamic_schedule)}, 总计={len(combined_schedule)}"
        )
    except Exception as e:
        # 如果数据库不可用（如迁移期间），只使用静态配置
        logger.warning(f"⚠️ 无法加载动态调度配置，仅使用静态配置: {str(e)}")
    
    return combined_schedule

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    # 定时任务配置（合并静态和动态）
    beat_schedule=get_combined_beat_schedule(),
    # 队列配置
    task_default_queue="default",
    task_routes={
        "app.tasks.shopify_tasks.*": {"queue": "shopify"},
        "app.tasks.order_tasks.*": {"queue": "orders"},
    },
    # 结果后端配置
    result_expires=3600,  # 结果保存1小时
    # 任务重试配置
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # 监控配置
    worker_send_task_events=True,
    task_send_sent_event=True,
    # 异常序列化配置 - 确保异常信息包含所有必要字段
    task_ignore_result=False,  # 不忽略结果，确保异常信息被正确存储
    # Windows 兼容性配置
    # 1. 强制使用 dbm.dumb 格式（Beat 调度文件）
    beat_schedule_filename="celerybeat-schedule",
    # 2. Windows 上使用 solo 池（单进程模式），避免 prefork 权限问题
    # 注意：在 Linux/Mac 上会自动使用 prefork，Windows 上使用 solo
    # 可以通过环境变量 CELERY_WORKER_POOL 覆盖（solo/threads/prefork）
    worker_pool=os.getenv("CELERY_WORKER_POOL", "solo" if os.name == "nt" else "prefork"),
)

# Auto-discover tasks
celery_app.autodiscover_tasks()

# 修复异常序列化问题：在结果后端初始化后 patch exception_to_python 方法
def _patch_backend_exception_handler():
    """Patch 结果后端的异常处理方法，确保异常信息格式正确"""
    try:
        # 等待后端初始化
        backend = celery_app.backend
        
        if backend and hasattr(backend, 'exception_to_python'):
            # 保存原始方法
            if not hasattr(backend, '_original_exception_to_python'):
                backend._original_exception_to_python = backend.exception_to_python
            
            # 创建修复后的方法（需要接收 self 作为第一个参数）
            def _patched_exception_to_python(self, exc):
                """修复的异常转换方法"""
                # #region agent log
                import json, time
                try:
                    with open(r'd:\work\cursor\impeach\supplynexus\fulfillment-service\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"celery_app.py:114","message":"exception_to_python called","data":{"exc_type":type(exc).__name__,"is_dict":isinstance(exc,dict),"keys":list(exc.keys()) if isinstance(exc,dict) else None},"timestamp":int(time.time()*1000)})+'\n')
                except: pass
                # #endregion
                
                if exc is None:
                    return None
                
                # 如果 exc 是字典，检查是否包含必要字段
                if isinstance(exc, dict):
                    # 确保包含 exc_type 字段
                    if 'exc_type' not in exc:
                        # #region agent log
                        try:
                            with open(r'd:\work\cursor\impeach\supplynexus\fulfillment-service\.cursor\debug.log', 'a', encoding='utf-8') as f:
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"celery_app.py:122","message":"Missing exc_type, fixing","data":{"has_error_type":'error_type' in exc,"has_error":'error' in exc},"timestamp":int(time.time()*1000)})+'\n')
                        except: pass
                        # #endregion
                        
                        if 'error_type' in exc:
                            exc['exc_type'] = exc['error_type']
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
                    
                    # 确保包含 exc_module 字段
                    if 'exc_module' not in exc:
                        exc['exc_module'] = 'builtins'
                
                # 调用原始方法
                try:
                    # #region agent log
                    try:
                        with open(r'd:\work\cursor\impeach\supplynexus\fulfillment-service\.cursor\debug.log', 'a', encoding='utf-8') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"G","location":"celery_app.py:145","message":"Calling original method","data":{"exc_keys":list(exc.keys()) if isinstance(exc,dict) else None},"timestamp":int(time.time()*1000)})+'\n')
                    except: pass
                    # #endregion
                    
                    return backend._original_exception_to_python(exc)
                except (KeyError, ValueError) as e:
                    # #region agent log
                    try:
                        with open(r'd:\work\cursor\impeach\supplynexus\fulfillment-service\.cursor\debug.log', 'a', encoding='utf-8') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"H","location":"celery_app.py:147","message":"Original method failed, using fallback","data":{"error":str(e),"exc_keys":list(exc.keys()) if isinstance(exc,dict) else None},"timestamp":int(time.time()*1000)})+'\n')
                    except: pass
                    # #endregion
                    
                    # 如果原始方法失败，返回一个包装的异常
                    if isinstance(exc, dict):
                        error_type = exc.get('exc_type', 'Exception')
                        error_message = exc.get('exc_message', str(exc))
                    else:
                        error_type = 'Exception'
                        error_message = str(exc)
                    return RuntimeError(f"{error_type}: {error_message}")
            
            # 替换方法
            import types
            backend.exception_to_python = types.MethodType(_patched_exception_to_python, backend)
    except (AttributeError, Exception):
        # 如果后端还未初始化，稍后会在任务执行时自动 patch
        pass

# 立即尝试 patch
_patch_backend_exception_handler()

# 使用 Celery 信号在 worker 启动时 patch
from celery.signals import worker_ready

@worker_ready.connect
def patch_backend_on_worker_ready(sender, **kwargs):
    """在 worker 就绪时 patch 结果后端"""
    _patch_backend_exception_handler()
