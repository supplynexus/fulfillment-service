"""
Celery Beat 定时任务配置
用于配置定期执行的任务
"""

from celery.schedules import crontab

# 定时任务配置
CELERY_BEAT_SCHEDULE = {
    # 每小时增量同步所有租户的 Shopify 产品
    'sync-shopify-products-hourly': {
        'task': 'schedule_shopify_products_sync',
        'schedule': crontab(minute=0, hour='*'),  # 每小时整点执行
        'args': (),
        'options': {
            'queue': 'default',
            'expires': 3600,  # 1小时后过期
        }
    },
    
    # 每天凌晨2点全量同步所有租户的 Shopify 产品
    'sync-shopify-products-daily': {
        'task': 'schedule_shopify_products_full_sync',
        'schedule': crontab(minute=0, hour=2),  # 每天凌晨2点执行
        'args': (),
        'options': {
            'queue': 'default',
            'expires': 86400,  # 24小时后过期
        }
    },
    
    # 每30分钟同步一次订单（如果需要）
    'sync-shopify-orders': {
        'task': 'fetch_recent_orders',
        'schedule': crontab(minute='*/30'),  # 每30分钟执行
        'args': (),
        'options': {
            'queue': 'default',
            'expires': 1800,  # 30分钟后过期
        }
    },
    
    # 每30分钟同步所有租户的 Shopify 产品（基于数据库配置）
    'sync-shopify-products-30min': {
        'task': 'sync_all_tenants_products_custom',
        'schedule': crontab(minute='*/30'),  # 每30分钟执行
        'args': (),
        'options': {
            'queue': 'shopify',
            'expires': 1800,  # 30分钟后过期
        }
    },
}

# 任务路由配置
CELERY_TASK_ROUTES = {
    'sync_shopify_products': {'queue': 'shopify'},
    'sync_shopify_products_incremental': {'queue': 'shopify'},
    'sync_shopify_products_full': {'queue': 'shopify'},
    'sync_all_tenants_products': {'queue': 'shopify'},
    'schedule_shopify_products_sync': {'queue': 'shopify'},
    'schedule_shopify_products_full_sync': {'queue': 'shopify'},
    'sync_all_tenants_products_custom': {'queue': 'shopify'},
    
    'fetch_shopify_orders': {'queue': 'orders'},
    'fetch_recent_orders': {'queue': 'orders'},
    'fetch_unfulfilled_orders': {'queue': 'orders'},
    'sync_all_orders': {'queue': 'orders'},
}

# 队列配置
CELERY_TASK_DEFAULT_QUEUE = 'default'
CELERY_TASK_CREATE_MISSING_QUEUES = True

# 任务优先级
CELERY_TASK_QUEUE_MAX_PRIORITY = 10
CELERY_TASK_DEFAULT_PRIORITY = 5
