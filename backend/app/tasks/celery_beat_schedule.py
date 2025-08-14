"""
Celery Beat 定时任务配置
"""

from celery.schedules import crontab
from app.tasks.shopify_tasks import sync_shopify_orders_1min_task

# Celery Beat 定时任务配置
CELERY_BEAT_SCHEDULE = {
    # 每分钟同步 Shopify 订单
    'sync-shopify-orders-1min': {
        'task': 'app.tasks.shopify_tasks.sync_shopify_orders_1min_task',
        'schedule': 60.0,  # 每60秒执行一次
        'options': {
            'queue': 'shopify',
            'expires': 30,  # 任务过期时间（秒）
        }
    },
    
    # 每小时同步 Shopify 订单（全量同步）
    'sync-shopify-orders-hourly': {
        'task': 'app.tasks.shopify_tasks.sync_shopify_orders_task',
        'schedule': crontab(minute=0),  # 每小时整点执行
        'args': (1,),  # tenant_id
        'kwargs': {
            'sync_recent_only': False,
            'max_orders': 1000
        },
        'options': {
            'queue': 'shopify',
            'expires': 3600,  # 任务过期时间（秒）
        }
    },
    
    # 每天凌晨2点全量同步 Shopify 订单
    'sync-shopify-orders-daily': {
        'task': 'app.tasks.shopify_tasks.sync_shopify_orders_task',
        'schedule': crontab(hour=2, minute=0),  # 每天凌晨2点执行
        'args': (1,),  # tenant_id
        'kwargs': {
            'sync_recent_only': False,
            'max_orders': None  # 不限制数量，同步所有订单
        },
        'options': {
            'queue': 'shopify',
            'expires': 7200,  # 任务过期时间（秒）
        }
    },
}
