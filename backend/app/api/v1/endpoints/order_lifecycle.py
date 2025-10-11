"""
订单生命周期管理API端点
提供订单状态生命周期管理的REST API接口
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum

from app.core.database import get_async_db
from app.core.tenant_auth_dependency import verify_tenant_auth
from app.core.logging import get_logger
from app.models.tenant import Tenant
from app.models.user import User
from app.services.order_lifecycle_service import (
    OrderLifecycleService,
    OrderSystemType,
    OrderLifecycleStage
)

logger = get_logger(__name__)
router = APIRouter()


class OrderSystemTypeEnum(str, Enum):
    """订单系统类型枚举"""
    CORE = "core"
    SCM = "scm"
    SHOPIFY = "shopify"
    PRINTIFY = "printify"


class OrderLifecycleStageEnum(str, Enum):
    """订单生命周期阶段枚举"""
    CREATED = "created"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    FULFILLED = "fulfilled"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    FAILED = "failed"


class StatusTransitionRequest(BaseModel):
    """状态转换请求"""
    to_status: str = Field(..., description="目标状态")
    user_id: Optional[int] = Field(None, description="操作用户ID")
    reason: Optional[str] = Field(None, description="转换原因")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class StatusTransitionResponse(BaseModel):
    """状态转换响应"""
    success: bool
    message: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    timestamp: Optional[str] = None
    error: Optional[str] = None


class OrderLifecycleResponse(BaseModel):
    """订单生命周期响应"""
    success: bool
    order_id: int
    system_type: str
    current_status: str
    lifecycle_stages: List[str]
    current_stage: Optional[str]
    lifecycle_progress: Dict[str, Any]
    status_history: List[Dict[str, Any]]
    available_transitions: List[Dict[str, Any]]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    error: Optional[str] = None


@router.post("/lifecycle/{order_id}/transition", response_model=StatusTransitionResponse)
async def transition_order_status(
    order_id: int = Path(..., description="订单ID"),
    system_type: OrderSystemTypeEnum = Query(..., description="系统类型"),
    request: StatusTransitionRequest = ...,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    执行订单状态转换
    """
    tenant, user = auth
    
    logger.info(
        "🔍 开始执行订单状态转换",
        order_id=order_id,
        system_type=system_type.value,
        to_status=request.to_status,
        tenant_id=tenant.id,
        user_id=user.id
    )
    
    try:
        # 创建订单生命周期服务
        lifecycle_service = OrderLifecycleService(db)
        
        # 转换系统类型
        order_system_type = OrderSystemType(system_type.value)
        
        # 执行状态转换
        result = await lifecycle_service.transition_order_status(
            order_id=order_id,
            system_type=order_system_type,
            to_status=request.to_status,
            tenant_id=tenant.id,
            user_id=request.user_id or user.id,
            reason=request.reason,
            metadata=request.metadata
        )
        
        if result.get("success"):
            logger.info(
                "✅ 订单状态转换成功",
                order_id=order_id,
                from_status=result.get("from_status"),
                to_status=result.get("to_status")
            )
            return StatusTransitionResponse(
                success=True,
                message=result.get("message", "状态转换成功"),
                from_status=result.get("from_status"),
                to_status=result.get("to_status"),
                timestamp=result.get("timestamp")
            )
        else:
            logger.warning(
                "⚠️ 订单状态转换失败",
                order_id=order_id,
                to_status=request.to_status,
                error=result.get("message")
            )
            return StatusTransitionResponse(
                success=False,
                message=result.get("message", "状态转换失败"),
                error=result.get("error")
            )
            
    except Exception as e:
        logger.error(
            "❌ 订单状态转换异常",
            order_id=order_id,
            system_type=system_type.value,
            to_status=request.to_status,
            error=str(e)
        )
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"订单状态转换失败: {str(e)}"
        )


@router.get("/lifecycle/{order_id}", response_model=OrderLifecycleResponse)
async def get_order_lifecycle(
    order_id: int = Path(..., description="订单ID"),
    system_type: OrderSystemTypeEnum = Query(..., description="系统类型"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    获取订单生命周期信息
    """
    tenant, user = auth
    
    logger.info(
        "🔍 获取订单生命周期信息",
        order_id=order_id,
        system_type=system_type.value,
        tenant_id=tenant.id,
        user_id=user.id
    )
    
    try:
        # 创建订单生命周期服务
        lifecycle_service = OrderLifecycleService(db)
        
        # 转换系统类型
        order_system_type = OrderSystemType(system_type.value)
        
        # 获取生命周期信息
        result = await lifecycle_service.get_order_lifecycle(
            order_id=order_id,
            system_type=order_system_type,
            tenant_id=tenant.id
        )
        
        if result.get("success"):
            logger.info(
                "✅ 获取订单生命周期信息成功",
                order_id=order_id,
                current_status=result.get("current_status")
            )
            return OrderLifecycleResponse(
                success=True,
                order_id=result.get("order_id"),
                system_type=result.get("system_type"),
                current_status=result.get("current_status"),
                lifecycle_stages=result.get("lifecycle_stages", []),
                current_stage=result.get("current_stage"),
                lifecycle_progress=result.get("lifecycle_progress", {}),
                status_history=result.get("status_history", []),
                available_transitions=result.get("available_transitions", []),
                created_at=result.get("created_at"),
                updated_at=result.get("updated_at")
            )
        else:
            logger.warning(
                "⚠️ 获取订单生命周期信息失败",
                order_id=order_id,
                error=result.get("message")
            )
            return OrderLifecycleResponse(
                success=False,
                order_id=order_id,
                system_type=system_type.value,
                current_status="",
                lifecycle_stages=[],
                current_stage=None,
                lifecycle_progress={},
                status_history=[],
                available_transitions=[],
                error=result.get("message")
            )
            
    except Exception as e:
        logger.error(
            "❌ 获取订单生命周期信息异常",
            order_id=order_id,
            system_type=system_type.value,
            error=str(e)
        )
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取订单生命周期信息失败: {str(e)}"
        )


@router.get("/lifecycle/{order_id}/validate-transition")
async def validate_status_transition(
    order_id: int = Path(..., description="订单ID"),
    system_type: OrderSystemTypeEnum = Query(..., description="系统类型"),
    to_status: str = Query(..., description="目标状态"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    验证状态转换是否允许
    """
    tenant, user = auth
    
    logger.info(
        "🔍 验证状态转换",
        order_id=order_id,
        system_type=system_type.value,
        to_status=to_status,
        tenant_id=tenant.id,
        user_id=user.id
    )
    
    try:
        # 创建订单生命周期服务
        lifecycle_service = OrderLifecycleService(db)
        
        # 转换系统类型
        order_system_type = OrderSystemType(system_type.value)
        
        # 获取当前状态
        order = await lifecycle_service._get_order(order_id, order_system_type, tenant.id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"订单不存在: {order_id}"
            )
        
        from_status = order.status
        
        # 验证状态转换
        is_valid, error_message, missing_conditions = await lifecycle_service.validate_status_transition(
            order_id=order_id,
            system_type=order_system_type,
            from_status=from_status,
            to_status=to_status,
            tenant_id=tenant.id
        )
        
        return {
            "success": True,
            "order_id": order_id,
            "system_type": system_type.value,
            "from_status": from_status,
            "to_status": to_status,
            "is_valid": is_valid,
            "error_message": error_message if not is_valid else None,
            "missing_conditions": missing_conditions,
            "message": "状态转换验证完成"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "❌ 验证状态转换异常",
            order_id=order_id,
            system_type=system_type.value,
            to_status=to_status,
            error=str(e)
        )
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"验证状态转换失败: {str(e)}"
        )


@router.get("/lifecycle/{order_id}/available-transitions")
async def get_available_transitions(
    order_id: int = Path(..., description="订单ID"),
    system_type: OrderSystemTypeEnum = Query(..., description="系统类型"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    获取可用的状态转换
    """
    tenant, user = auth
    
    logger.info(
        "🔍 获取可用的状态转换",
        order_id=order_id,
        system_type=system_type.value,
        tenant_id=tenant.id,
        user_id=user.id
    )
    
    try:
        # 创建订单生命周期服务
        lifecycle_service = OrderLifecycleService(db)
        
        # 转换系统类型
        order_system_type = OrderSystemType(system_type.value)
        
        # 获取订单
        order = await lifecycle_service._get_order(order_id, order_system_type, tenant.id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"订单不存在: {order_id}"
            )
        
        # 获取可用的状态转换
        available_transitions = await lifecycle_service._get_available_transitions(
            order_id=order_id,
            system_type=order_system_type,
            current_status=order.status,
            tenant_id=tenant.id
        )
        
        return {
            "success": True,
            "order_id": order_id,
            "system_type": system_type.value,
            "current_status": order.status,
            "available_transitions": available_transitions,
            "total_count": len(available_transitions),
            "message": "获取可用状态转换成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "❌ 获取可用状态转换异常",
            order_id=order_id,
            system_type=system_type.value,
            error=str(e)
        )
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取可用状态转换失败: {str(e)}"
        )


@router.get("/lifecycle/stages/{system_type}")
async def get_lifecycle_stages(
    system_type: OrderSystemTypeEnum = Path(..., description="系统类型"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    获取系统类型的生命周期阶段
    """
    tenant, user = auth
    
    logger.info(
        "🔍 获取生命周期阶段",
        system_type=system_type.value,
        tenant_id=tenant.id,
        user_id=user.id
    )
    
    try:
        # 创建订单生命周期服务
        lifecycle_service = OrderLifecycleService(db)
        
        # 获取生命周期阶段
        stages = lifecycle_service.lifecycle_stages.get(system_type.value, [])
        stage_names = [stage.value for stage in stages]
        
        return {
            "success": True,
            "system_type": system_type.value,
            "stages": stage_names,
            "total_count": len(stage_names),
            "message": "获取生命周期阶段成功"
        }
        
    except Exception as e:
        logger.error(
            "❌ 获取生命周期阶段异常",
            system_type=system_type.value,
            error=str(e)
        )
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取生命周期阶段失败: {str(e)}"
        )


@router.get("/lifecycle/transitions/{system_type}")
async def get_status_transitions(
    system_type: OrderSystemTypeEnum = Path(..., description="系统类型"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    获取系统类型的状态转换规则
    """
    tenant, user = auth
    
    logger.info(
        "🔍 获取状态转换规则",
        system_type=system_type.value,
        tenant_id=tenant.id,
        user_id=user.id
    )
    
    try:
        # 创建订单生命周期服务
        lifecycle_service = OrderLifecycleService(db)
        
        # 获取状态转换规则
        transitions = lifecycle_service.status_transitions.get(system_type.value, [])
        transition_data = []
        
        for transition in transitions:
            transition_data.append({
                "from_status": transition.from_status,
                "to_status": transition.to_status,
                "allowed": transition.allowed,
                "requires_approval": transition.requires_approval,
                "auto_transition": transition.auto_transition,
                "conditions": transition.conditions or [],
                "description": transition.description
            })
        
        return {
            "success": True,
            "system_type": system_type.value,
            "transitions": transition_data,
            "total_count": len(transition_data),
            "message": "获取状态转换规则成功"
        }
        
    except Exception as e:
        logger.error(
            "❌ 获取状态转换规则异常",
            system_type=system_type.value,
            error=str(e)
        )
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取状态转换规则失败: {str(e)}"
        )
