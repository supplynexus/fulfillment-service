"""
Celery Beat 定时任务配置
所有定时任务都已改为动态任务，从数据库读取配置
此文件保留为空配置，所有任务通过 tenant_automation_config 表控制
"""

# Celery Beat 定时任务配置
# 注意：所有任务都已改为动态任务，从数据库 tenant_automation_config 表读取
# 静态任务已全部移除，因为所有任务都可以在画面上控制开关
CELERY_BEAT_SCHEDULE = {}
