"""
自动化调度服务
从数据库读取租户配置，动态生成Celery Beat调度
"""

from typing import Dict, Any
from sqlalchemy.orm import Session
from celery.schedules import crontab

from app.core.logging import get_logger
from app.services.automation_service import AutomationService
from app.models.tenant_automation_config import TenantAutomationConfig

logger = get_logger(__name__)


def parse_schedule(schedule: str, schedule_seconds: int = None) -> Any:
    """
    解析计划配置，支持cron表达式或秒数
    
    Args:
        schedule: Cron表达式，如 "*/30 * * * *"
        schedule_seconds: 秒数，如 1800（30分钟）
        
    Returns:
        Celery schedule对象（crontab或秒数）
    """
    if schedule_seconds:
        # 优先使用秒数
        return float(schedule_seconds)
    
    if schedule:
        # 解析cron表达式
        # 格式: "*/30 * * * *" -> minute, hour, day_of_month, month, day_of_week
        try:
            parts = schedule.strip().split()
            if len(parts) == 5:
                minute, hour, day_of_month, month, day_of_week = parts
                
                # 处理特殊格式
                # "*/30 * * * *" -> 每30分钟
                if minute.startswith("*/"):
                    minute_value = int(minute[2:])
                    return crontab(minute=f"*/{minute_value}")
                elif minute.isdigit():
                    return crontab(minute=int(minute))
                elif minute == "*":
                    # 每小时
                    if hour.startswith("*/"):
                        hour_value = int(hour[2:])
                        return crontab(hour=f"*/{hour_value}")
                    elif hour.isdigit():
                        return crontab(hour=int(hour))
                    elif hour == "*":
                        # 每天
                        if day_of_month.startswith("*/"):
                            day_value = int(day_of_month[2:])
                            return crontab(day_of_month=f"*/{day_value}")
                        elif day_of_month.isdigit():
                            return crontab(day_of_month=int(day_of_month))
                
                # 默认：尝试解析完整cron
                return crontab(
                    minute=minute if minute != "*" else None,
                    hour=hour if hour != "*" else None,
                    day_of_month=day_of_month if day_of_month != "*" else None,
                    month_of_year=month if month != "*" else None,
                    day_of_week=day_of_week if day_of_week != "*" else None,
                )
        except Exception as e:
            logger.warning(f"⚠️ 解析cron表达式失败: {schedule}, 错误: {str(e)}")
            # 降级为默认值：30分钟
            return 1800.0
    
    # 默认：30分钟
    return 1800.0


def get_dynamic_beat_schedule(db: Session) -> Dict[str, Any]:
    """
    从数据库读取所有租户的自动化配置，生成Celery Beat调度
    
    Returns:
        Celery Beat调度字典，格式:
        {
            "tenant_{tenant_id}_step_{step_key}": {
                "task": "celery_task_name",
                "schedule": crontab(...) 或 秒数,
                "args": (tenant_id, ...),
                "kwargs": {...}
            }
        }
    """
    try:
        logger.info("🔍 开始生成动态Celery Beat调度配置")
        
        service = AutomationService(db)
        
        # 获取所有启用的租户配置
        enabled_configs = service.get_enabled_tenant_configs()
        
        if not enabled_configs:
            logger.info("ℹ️ 没有启用的自动化配置，返回空调度")
            return {}
        
        schedule = {}
        
        for config in enabled_configs:
            # 获取步骤信息
            step = service.get_step_by_key(config.step_key)
            if not step:
                logger.warning(f"⚠️ 步骤不存在，跳过: {config.step_key}")
                continue
            
            if step.is_manual_only:
                logger.info(f"ℹ️ 步骤仅支持手动触发，跳过: {config.step_key}")
                continue
            
            if not step.celery_task_name:
                logger.warning(f"⚠️ 步骤未配置Celery任务，跳过: {config.step_key}")
                continue
            
            # 任务名称映射（优先级高于数据库中的配置）
            # 用于修复旧的任务名称或统一任务名称
            task_mapping = {
                "app.tasks.order_automation_tasks.process_new_shopify_orders": "app.tasks.order_automation_tasks.process_new_orders_to_scm",
                "sync_external_orders": "sync_shopify_orders_1min",
            }
            
            # 按 step_key 的任务名称映射（优先级最高）
            step_key_task_mapping = {
                "create_scm_orders": "app.tasks.order_automation_tasks.process_new_orders_to_scm",
                "create_printify_orders_from_scm": "app.tasks.order_automation_tasks.create_printify_orders_from_scm",
                "sync_external_orders": "sync_shopify_orders_1min",
                "sync_printify_orders_to_local": "app.tasks.order_automation_tasks.sync_printify_orders_to_local",
                "sync_shopify_fulfillment_to_local": "app.tasks.order_automation_tasks.sync_shopify_fulfillment_to_local",
                "sync_shopify_local_fulfillment_to_core": "app.tasks.order_automation_tasks.sync_shopify_local_fulfillment_to_core",
            }
            
            # 优先使用 step_key 映射，然后使用通用映射，最后使用数据库中的配置
            celery_task_name = (
                step_key_task_mapping.get(config.step_key) or
                task_mapping.get(step.celery_task_name) or
                step.celery_task_name
            )
            
            # 生成调度键
            schedule_key = f"tenant_{config.tenant_id}_step_{config.step_key}"
            
            # 解析计划
            celery_schedule = parse_schedule(config.schedule, config.schedule_seconds)
            
            # 构建任务参数
            task_kwargs = config.task_params or {}
            task_kwargs["tenant_id"] = config.tenant_id
            
            # 添加到调度
            schedule[schedule_key] = {
                "task": celery_task_name,
                "schedule": celery_schedule,
                "kwargs": task_kwargs,
                "options": {
                    "queue": "order_automation",
                    "expires": 300,  # 任务过期时间（秒）
                },
            }
            
            logger.info(
                f"✅ 添加调度任务: {schedule_key}, task={celery_task_name}, "
                f"schedule={celery_schedule}"
            )
        
        logger.info(f"✅ 动态Celery Beat调度配置生成完成: count={len(schedule)}")
        return schedule
        
    except Exception as e:
        logger.error(f"❌ 生成动态Celery Beat调度配置失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        return {}


def get_dynamic_beat_schedule_for_tenant(
    db: Session,
    tenant_id: int
) -> Dict[str, Any]:
    """
    获取特定租户的动态调度配置
    
    Args:
        db: 数据库会话
        tenant_id: 租户ID
        
    Returns:
        Celery Beat调度字典
    """
    try:
        service = AutomationService(db)
        enabled_configs = service.get_enabled_tenant_configs(tenant_id=tenant_id)
        
        schedule = {}
        # 任务名称映射（与上面的映射保持一致）
        task_mapping = {
            "app.tasks.order_automation_tasks.process_new_shopify_orders": "app.tasks.order_automation_tasks.process_new_orders_to_scm",
            "sync_external_orders": "sync_shopify_orders_1min",
        }
        
        step_key_task_mapping = {
            "create_scm_orders": "app.tasks.order_automation_tasks.process_new_orders_to_scm",
            "create_printify_orders_from_scm": "app.tasks.order_automation_tasks.create_printify_orders_from_scm",
            "sync_external_orders": "sync_shopify_orders_1min",
            "sync_printify_orders_to_local": "app.tasks.order_automation_tasks.sync_printify_orders_to_local",
            "sync_shopify_fulfillment_to_local": "app.tasks.order_automation_tasks.sync_shopify_fulfillment_to_local",
            "sync_shopify_local_fulfillment_to_core": "app.tasks.order_automation_tasks.sync_shopify_local_fulfillment_to_core",
        }
        
        for config in enabled_configs:
            step = service.get_step_by_key(config.step_key)
            if not step or step.is_manual_only or not step.celery_task_name:
                continue
            
            # 使用相同的映射逻辑
            celery_task_name = (
                step_key_task_mapping.get(config.step_key) or
                task_mapping.get(step.celery_task_name) or
                step.celery_task_name
            )
            
            schedule_key = f"tenant_{config.tenant_id}_step_{config.step_key}"
            celery_schedule = parse_schedule(config.schedule, config.schedule_seconds)
            
            task_kwargs = config.task_params or {}
            task_kwargs["tenant_id"] = config.tenant_id
            
            schedule[schedule_key] = {
                "task": celery_task_name,
                "schedule": celery_schedule,
                "kwargs": task_kwargs,
                "options": {
                    "queue": "order_automation",
                    "expires": 300,
                },
            }
        
        return schedule
    except Exception as e:
        logger.error(f"❌ 获取租户动态调度配置失败: {str(e)}")
        return {}




