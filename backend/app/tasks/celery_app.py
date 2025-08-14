"""
Celery application configuration
"""

from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "fulfillment_service",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.product_tasks"]  # 暂时只包含 product_tasks 来测试
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
    
    # Beat schedule configuration
    beat_schedule=CELERY_BEAT_SCHEDULE,
    task_routes=CELERY_TASK_ROUTES,
)

# Auto-discover tasks
celery_app.autodiscover_tasks()
