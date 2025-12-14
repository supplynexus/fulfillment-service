"""
Celery Beat 定时任务配置
用于配置定期执行的任务
"""

from celery.schedules import crontab

# Celery Beat 定时任务配置
CELERY_BEAT_SCHEDULE = {
    # 每分钟同步 Shopify 订单
    "sync-shopify-orders-1min": {
        "task": "app.tasks.shopify_tasks.sync_shopify_orders_1min_task",
        "schedule": 1800.0,  # 每60秒执行一次
        "options": {
            "queue": "shopify",
            "expires": 30,  # 任务过期时间（秒）
        },
    },
    # 每分钟同步 Shopify 商品
    "sync-shopify-products-1min": {
        "task": "app.tasks.shopify_tasks.sync_shopify_products_1min_task",
        "schedule": 1800.0,  # 每60秒执行一次
        "options": {
            "queue": "shopify",
            "expires": 30,  # 任务过期时间（秒）
        },
    },
    # 每小时同步 Shopify 订单（全量同步）
    "sync-shopify-orders-hourly": {
        "task": "app.tasks.shopify_tasks.sync_shopify_orders_task",
        "schedule": crontab(minute=0),  # 每小时整点执行
        "args": (1,),  # tenant_id
        "kwargs": {"sync_recent_only": False, "max_orders": 1000},
        "options": {
            "queue": "shopify",
            "expires": 3600,  # 任务过期时间（秒）
        },
    },
    # 每小时同步 Shopify 商品（全量同步）
    "sync-shopify-products-hourly": {
        "task": "app.tasks.shopify_tasks.sync_shopify_products_task",
        "schedule": crontab(minute=0),  # 每小时整点执行
        "args": (1,),  # tenant_id
        "kwargs": {"sync_recent_only": False, "max_products": 1000},
        "options": {
            "queue": "shopify",
            "expires": 3600,  # 任务过期时间（秒）
        },
    },
    # 每天凌晨2点全量同步 Shopify 订单
    "sync-shopify-orders-daily": {
        "task": "app.tasks.shopify_tasks.sync_shopify_orders_task",
        "schedule": crontab(hour=2, minute=0),  # 每天凌晨2点执行
        "args": (1,),  # tenant_id
        "kwargs": {
            "sync_recent_only": False,
            "max_orders": None,  # 不限制数量，同步所有订单
        },
        "options": {
            "queue": "shopify",
            "expires": 7200,  # 任务过期时间（秒）
        },
    },
    # 每天凌晨3点全量同步 Shopify 商品
    "sync-shopify-products-daily": {
        "task": "app.tasks.shopify_tasks.sync_shopify_products_task",
        "schedule": crontab(hour=3, minute=0),  # 每天凌晨3点执行
        "args": (1,),  # tenant_id
        "kwargs": {
            "sync_recent_only": False,
            "max_products": None,  # 不限制数量，同步所有商品
        },
        "options": {
            "queue": "shopify",
            "expires": 7200,  # 任务过期时间（秒）
        },
    },
    # 订单自动化任务
    # 每30分钟处理新的核心订单，路由到SCM系统（通用任务，不限制订单来源）
    "process-new-orders-to-scm": {
        "task": "app.tasks.order_automation_tasks.scheduled_process_orders_to_scm",
        "schedule": 1800.0,  # 每1800秒（30分钟）执行一次
        "options": {
            "queue": "order_automation",
            "expires": 60,  # 任务过期时间（秒）
        },
    },
    # 每5分钟同步Printify订单状态
    "sync-printify-orders-status": {
        "task": "app.tasks.order_automation_tasks.scheduled_sync_printify_status",
        "schedule": 1800.0,  # 每1800秒执行一次
        "options": {
            "queue": "order_automation",
            "expires": 120,  # 任务过期时间（秒）
        },
    },
    # 每10分钟同步SCM订单到Shopify履约
    "sync-scm-to-shopify-fulfillment": {
        "task": "app.tasks.order_automation_tasks.scheduled_sync_shopify_fulfillment",
        "schedule": 1800.0,  # 每1800秒执行一次
        "options": {
            "queue": "order_automation",
            "expires": 300,  # 任务过期时间（秒）
        },
    },
}
