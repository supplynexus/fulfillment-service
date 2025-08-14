"""
Celery application configuration
"""

from celery import Celery
from app.core.config import settings
from app.tasks.celery_beat_schedule import CELERY_BEAT_SCHEDULE

# Create Celery app
celery_app = Celery(
    "fulfillment_service",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.shopify_tasks",
        "app.tasks.order_tasks"
    ]
)

# Import beat schedule
from app.tasks.celery_beat_schedule import CELERY_BEAT_SCHEDULE, CELERY_TASK_ROUTES

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
    
    # 定时任务配置
    beat_schedule=CELERY_BEAT_SCHEDULE,
    
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
)

# Auto-discover tasks
celery_app.autodiscover_tasks()
