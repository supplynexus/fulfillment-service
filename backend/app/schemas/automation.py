"""
Automation schemas
自动化配置相关的Pydantic模型
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ==================== AutomationStep Schemas ====================

class AutomationStepBase(BaseModel):
    """自动化步骤基础模型"""
    step_key: str = Field(..., description="步骤唯一标识")
    name: str = Field(..., description="步骤名称")
    description: Optional[str] = Field(None, description="步骤描述")
    category: str = Field(..., description="步骤类别")
    required_external_systems: Optional[List[str]] = Field(None, description="所需外部系统列表")
    celery_task_name: Optional[str] = Field(None, description="Celery任务名")
    default_schedule: Optional[str] = Field(None, description="默认计划（cron表达式）")
    default_enabled: bool = Field(False, description="默认是否启用")
    is_manual_only: bool = Field(False, description="是否仅支持手动触发")


class AutomationStepResponse(AutomationStepBase):
    """自动化步骤响应模型"""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== TenantAutomationConfig Schemas ====================

class TenantAutomationConfigBase(BaseModel):
    """租户自动化配置基础模型"""
    step_key: str = Field(..., description="步骤标识")
    is_enabled: bool = Field(False, description="是否启用自动化")
    schedule: Optional[str] = Field(None, description="Cron表达式")
    schedule_seconds: Optional[int] = Field(None, description="计划秒数（兼容现有）")
    task_params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="任务参数")
    external_system_types: Optional[List[str]] = Field(None, description="外部系统类型过滤")
    external_system_ids: Optional[List[str]] = Field(None, description="外部系统ID过滤")
    is_active: bool = Field(True, description="是否激活")


class TenantAutomationConfigCreate(TenantAutomationConfigBase):
    """创建租户自动化配置"""
    pass


class TenantAutomationConfigUpdate(BaseModel):
    """更新租户自动化配置"""
    is_enabled: Optional[bool] = Field(None, description="是否启用自动化")
    schedule: Optional[str] = Field(None, description="Cron表达式")
    schedule_seconds: Optional[int] = Field(None, description="计划秒数")
    task_params: Optional[Dict[str, Any]] = Field(None, description="任务参数")
    external_system_types: Optional[List[str]] = Field(None, description="外部系统类型过滤")
    external_system_ids: Optional[List[str]] = Field(None, description="外部系统ID过滤")
    is_active: Optional[bool] = Field(None, description="是否激活")


class TenantAutomationConfigResponse(TenantAutomationConfigBase):
    """租户自动化配置响应模型"""
    id: int
    tenant_id: int
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    last_run_error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== AutomationManualButton Schemas ====================

class AutomationManualButtonBase(BaseModel):
    """手动按钮基础模型"""
    step_key: str = Field(..., description="步骤标识")
    button_key: str = Field(..., description="按钮标识")
    button_label: str = Field(..., description="按钮标签")
    button_action: str = Field(..., description="按钮动作（API路径）")
    http_method: str = Field("POST", description="HTTP方法")
    is_recommended: bool = Field(False, description="是否推荐使用")
    is_deprecated: bool = Field(False, description="是否已废弃")
    deprecated_reason: Optional[str] = Field(None, description="废弃原因")
    page_path: Optional[str] = Field(None, description="前端页面路径")
    order: int = Field(0, description="显示顺序")


class AutomationManualButtonResponse(AutomationManualButtonBase):
    """手动按钮响应模型"""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== Combined Response Schemas ====================

class AutomationStepWithConfigResponse(AutomationStepResponse):
    """带配置的自动化步骤响应模型"""
    tenant_config: Optional[TenantAutomationConfigResponse] = None
    manual_buttons: List[AutomationManualButtonResponse] = Field(default_factory=list)


class AutomationTriggerRequest(BaseModel):
    """手动触发自动化步骤请求"""
    params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="任务参数")


class AutomationTriggerResponse(BaseModel):
    """手动触发自动化步骤响应"""
    success: bool
    message: str
    task_id: Optional[str] = Field(None, description="Celery任务ID")




