"""
自动化服务
处理自动化步骤和配置的业务逻辑
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.core.logging import get_logger
from app.models.automation_step import AutomationStep
from app.models.tenant_automation_config import TenantAutomationConfig
from app.models.automation_manual_button import AutomationManualButton
from app.models.tenant import Tenant

logger = get_logger(__name__)


class AutomationService:
    """自动化服务类"""

    def __init__(self, db: Session):
        self.db = db

    def get_all_steps(
        self,
        category: Optional[str] = None
    ) -> List[AutomationStep]:
        """获取所有自动化步骤"""
        query = select(AutomationStep)
        if category:
            query = query.where(AutomationStep.category == category)
        query = query.order_by(AutomationStep.category, AutomationStep.step_key)
        
        result = self.db.execute(query)
        return result.scalars().all()

    def get_step_by_key(self, step_key: str) -> Optional[AutomationStep]:
        """根据step_key获取步骤"""
        result = self.db.execute(
            select(AutomationStep).where(AutomationStep.step_key == step_key)
        )
        return result.scalar_one_or_none()

    def get_tenant_configs(
        self,
        tenant_id: int
    ) -> List[TenantAutomationConfig]:
        """获取租户的所有自动化配置"""
        result = self.db.execute(
            select(TenantAutomationConfig).where(
                TenantAutomationConfig.tenant_id == tenant_id
            ).order_by(TenantAutomationConfig.step_key)
        )
        return result.scalars().all()

    def get_tenant_config(
        self,
        tenant_id: int,
        step_key: str
    ) -> Optional[TenantAutomationConfig]:
        """获取租户的单个步骤配置"""
        result = self.db.execute(
            select(TenantAutomationConfig).where(
                and_(
                    TenantAutomationConfig.tenant_id == tenant_id,
                    TenantAutomationConfig.step_key == step_key
                )
            )
        )
        return result.scalar_one_or_none()

    def create_or_update_tenant_config(
        self,
        tenant_id: int,
        step_key: str,
        is_enabled: Optional[bool] = None,
        schedule: Optional[str] = None,
        schedule_seconds: Optional[int] = None,
        task_params: Optional[Dict[str, Any]] = None,
        external_system_types: Optional[List[str]] = None,
        external_system_ids: Optional[List[str]] = None,
        is_active: Optional[bool] = None
    ) -> TenantAutomationConfig:
        """创建或更新租户自动化配置"""
        # 检查步骤是否存在
        step = self.get_step_by_key(step_key)
        if not step:
            raise ValueError(f"自动化步骤不存在: {step_key}")

        # 查找现有配置
        existing_config = self.get_tenant_config(tenant_id, step_key)

        if existing_config:
            # 更新现有配置
            if is_enabled is not None:
                existing_config.is_enabled = is_enabled
            if schedule is not None:
                existing_config.schedule = schedule
            if schedule_seconds is not None:
                existing_config.schedule_seconds = schedule_seconds
            if task_params is not None:
                existing_config.task_params = task_params
            if external_system_types is not None:
                existing_config.external_system_types = external_system_types
            if external_system_ids is not None:
                existing_config.external_system_ids = external_system_ids
            if is_active is not None:
                existing_config.is_active = is_active

            self.db.commit()
            self.db.refresh(existing_config)
            logger.info(f"✅ 更新租户自动化配置: tenant_id={tenant_id}, step_key={step_key}")
            return existing_config
        else:
            # 创建新配置
            new_config = TenantAutomationConfig(
                tenant_id=tenant_id,
                step_key=step_key,
                is_enabled=is_enabled if is_enabled is not None else step.default_enabled,
                schedule=schedule if schedule is not None else step.default_schedule,
                schedule_seconds=schedule_seconds,
                task_params=task_params or {},
                external_system_types=external_system_types,
                external_system_ids=external_system_ids,
                is_active=is_active if is_active is not None else True
            )
            self.db.add(new_config)
            self.db.commit()
            self.db.refresh(new_config)
            logger.info(f"✅ 创建租户自动化配置: tenant_id={tenant_id}, step_key={step_key}")
            return new_config

    def get_step_manual_buttons(
        self,
        step_key: str
    ) -> List[AutomationManualButton]:
        """获取步骤的手动按钮列表"""
        result = self.db.execute(
            select(AutomationManualButton).where(
                AutomationManualButton.step_key == step_key
            ).order_by(AutomationManualButton.order, AutomationManualButton.button_key)
        )
        return result.scalars().all()

    def get_enabled_tenant_configs(
        self,
        tenant_id: Optional[int] = None
    ) -> List[TenantAutomationConfig]:
        """获取所有启用的租户配置（用于Celery调度）"""
        query = select(TenantAutomationConfig).where(
            and_(
                TenantAutomationConfig.is_enabled == True,
                TenantAutomationConfig.is_active == True
            )
        )
        if tenant_id:
            query = query.where(TenantAutomationConfig.tenant_id == tenant_id)
        
        result = self.db.execute(query)
        return result.scalars().all()















