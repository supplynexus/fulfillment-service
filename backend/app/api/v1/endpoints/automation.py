"""
Automation management API endpoints
自动化管理API端点
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.database import get_async_db, get_sync_db
from app.core.tenant_auth_dependency import verify_tenant_auth
from app.core.logging import get_logger
from app.models.tenant import Tenant
from app.models.user import User
from app.services.automation_service import AutomationService
from app.schemas.automation import (
    AutomationStepResponse,
    TenantAutomationConfigResponse,
    TenantAutomationConfigUpdate,
    AutomationManualButtonResponse,
    AutomationStepWithConfigResponse,
    AutomationTriggerRequest,
    AutomationTriggerResponse,
)

router = APIRouter()
logger = get_logger(__name__)


@router.get("/steps", response_model=List[AutomationStepResponse])
async def get_automation_steps(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """获取所有可用的自动化步骤（系统预定义）"""
    tenant, user = auth
    
    try:
        # 使用同步数据库会话（因为AutomationService使用同步会话）
        sync_db = next(get_sync_db())
        service = AutomationService(sync_db)
        
        steps = service.get_all_steps(category=category)
        
        logger.info(f"✅ 获取自动化步骤列表: count={len(steps)}, category={category}")
        return steps
    except Exception as e:
        logger.error(f"❌ 获取自动化步骤列表失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get automation steps: {str(e)}"
        )


@router.get("/steps/{step_key}", response_model=AutomationStepResponse)
async def get_automation_step(
    step_key: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """获取单个自动化步骤详情"""
    tenant, user = auth
    
    try:
        sync_db = next(get_sync_db())
        service = AutomationService(sync_db)
        
        step = service.get_step_by_key(step_key)
        if not step:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Automation step not found: {step_key}"
            )
        
        logger.info(f"✅ 获取自动化步骤: step_key={step_key}")
        return step
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取自动化步骤失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get automation step: {str(e)}"
        )


@router.get("/configs", response_model=List[TenantAutomationConfigResponse])
async def get_tenant_automation_configs(
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """获取当前租户的所有自动化配置"""
    tenant, user = auth
    
    try:
        sync_db = next(get_sync_db())
        service = AutomationService(sync_db)
        
        configs = service.get_tenant_configs(tenant.id)
        
        logger.info(f"✅ 获取租户自动化配置: tenant_id={tenant.id}, count={len(configs)}")
        return configs
    except Exception as e:
        logger.error(f"❌ 获取租户自动化配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tenant automation configs: {str(e)}"
        )


@router.get("/configs/{step_key}", response_model=TenantAutomationConfigResponse)
async def get_tenant_automation_config(
    step_key: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """获取当前租户的单个步骤配置"""
    tenant, user = auth
    
    try:
        sync_db = next(get_sync_db())
        service = AutomationService(sync_db)
        
        config = service.get_tenant_config(tenant.id, step_key)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant automation config not found: {step_key}"
            )
        
        logger.info(f"✅ 获取租户自动化配置: tenant_id={tenant.id}, step_key={step_key}")
        return config
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取租户自动化配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tenant automation config: {str(e)}"
        )


@router.put("/configs/{step_key}", response_model=TenantAutomationConfigResponse)
async def update_tenant_automation_config(
    step_key: str,
    config_update: TenantAutomationConfigUpdate,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """更新租户的自动化配置（启用/禁用、修改计划等）"""
    tenant, user = auth
    
    try:
        sync_db = next(get_sync_db())
        service = AutomationService(sync_db)
        
        config = service.create_or_update_tenant_config(
            tenant_id=tenant.id,
            step_key=step_key,
            is_enabled=config_update.is_enabled,
            schedule=config_update.schedule,
            schedule_seconds=config_update.schedule_seconds,
            task_params=config_update.task_params,
            external_system_types=config_update.external_system_types,
            external_system_ids=config_update.external_system_ids,
            is_active=config_update.is_active
        )
        
        logger.info(
            f"✅ 更新租户自动化配置: tenant_id={tenant.id}, step_key={step_key}, "
            f"is_enabled={config.is_enabled}"
        )
        return config
    except ValueError as e:
        logger.error(f"❌ 更新租户自动化配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"❌ 更新租户自动化配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tenant automation config: {str(e)}"
        )


@router.get("/configs/{step_key}/buttons", response_model=List[AutomationManualButtonResponse])
async def get_step_manual_buttons(
    step_key: str,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """获取步骤的手动按钮列表"""
    tenant, user = auth
    
    try:
        sync_db = next(get_sync_db())
        service = AutomationService(sync_db)
        
        buttons = service.get_step_manual_buttons(step_key)
        
        logger.info(f"✅ 获取步骤手动按钮: step_key={step_key}, count={len(buttons)}")
        return buttons
    except Exception as e:
        logger.error(f"❌ 获取步骤手动按钮失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get step manual buttons: {str(e)}"
        )


@router.post("/configs/{step_key}/trigger", response_model=AutomationTriggerResponse)
async def trigger_automation_step(
    step_key: str,
    trigger_request: Optional[AutomationTriggerRequest] = None,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """手动触发自动化步骤"""
    tenant, user = auth
    
    try:
        sync_db = next(get_sync_db())
        service = AutomationService(sync_db)
        
        # 检查步骤是否存在
        step = service.get_step_by_key(step_key)
        if not step:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Automation step not found: {step_key}"
            )
        
        if step.is_manual_only:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Step {step_key} is manual only and cannot be triggered automatically"
            )
        
        # 根据step_key触发对应的Celery任务
        task_params = trigger_request.params if trigger_request else {}
        # 手动触发和自动触发都一样，默认不忽略标志（处理过就不再处理）
        ignore_flags = trigger_request.ignore_flags if trigger_request and trigger_request.ignore_flags is not None else False
        
        # 映射step_key到Celery任务（优先级高于数据库中的配置）
        task_mapping = {
            "sync_external_orders": "sync_shopify_orders_1min",
            "sync_to_core_orders": "app.tasks.order_automation_tasks.sync_shopify_orders_to_core",
            "create_scm_orders": "app.tasks.order_automation_tasks.process_new_orders_to_scm",
            "create_printify_orders_from_scm": "app.tasks.order_automation_tasks.create_printify_orders_from_scm",
            "sync_printify_orders_to_local": "app.tasks.order_automation_tasks.sync_printify_orders_to_local",
            "sync_printify_products_to_local": "app.tasks.order_automation_tasks.sync_printify_products_to_local",
            "auto_create_scm_from_unbound_printify_orders": "app.tasks.order_automation_tasks.auto_create_scm_from_unbound_printify_orders",
            "sync_fulfillment_status": "app.tasks.order_automation_tasks.sync_printify_orders_status",
            "sync_to_external_fulfillment": "app.tasks.order_automation_tasks.sync_scm_to_shopify_fulfillment",
            "sync_shopify_fulfillment_to_local": "app.tasks.order_automation_tasks.sync_shopify_fulfillment_to_local",
            "sync_shopify_local_fulfillment_to_core": "app.tasks.order_automation_tasks.sync_shopify_local_fulfillment_to_core",
        }
        
        # 优先使用代码中的映射，如果没有则使用数据库中的配置
        celery_task_name = task_mapping.get(step_key) or step.celery_task_name
        if not celery_task_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No Celery task configured for step: {step_key}"
            )
        
        # 导入并调用Celery任务
        from app.tasks.celery_app import celery_app
        
        # 构建任务参数
        task_kwargs = {
            "tenant_id": tenant.id,
            "ignore_flags": ignore_flags,  # 默认False，处理过就不再处理
            **{k: v for k, v in task_params.items() if k != "ignore_flags"}
        }
        
        # 发送任务到队列
        task = celery_app.send_task(
            celery_task_name,
            kwargs=task_kwargs
        )
        
        logger.info(
            f"✅ 手动触发自动化步骤: step_key={step_key}, tenant_id={tenant.id}, "
            f"task_id={task.id}"
        )
        
        return AutomationTriggerResponse(
            success=True,
            message=f"Task triggered successfully for step {step_key}",
            task_id=task.id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 手动触发自动化步骤失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger automation step: {str(e)}"
        )


@router.get("/steps-with-configs", response_model=List[AutomationStepWithConfigResponse])
async def get_steps_with_configs(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """获取所有步骤及其配置和按钮（用于管理页面）"""
    tenant, user = auth
    
    try:
        sync_db = next(get_sync_db())
        service = AutomationService(sync_db)
        
        # 获取所有步骤
        steps = service.get_all_steps(category=category)
        
        # 获取租户配置
        tenant_configs = {
            config.step_key: config
            for config in service.get_tenant_configs(tenant.id)
        }
        
        # 构建响应
        result = []
        for step in steps:
            # 获取按钮
            buttons = service.get_step_manual_buttons(step.step_key)
            
            result.append(AutomationStepWithConfigResponse(
                **step.__dict__,
                tenant_config=tenant_configs.get(step.step_key),
                manual_buttons=buttons
            ))
        
        logger.info(
            f"✅ 获取步骤及配置: tenant_id={tenant.id}, count={len(result)}, "
            f"category={category}"
        )
        return result
    except Exception as e:
        logger.error(f"❌ 获取步骤及配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get steps with configs: {str(e)}"
        )




