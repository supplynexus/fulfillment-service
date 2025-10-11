"""
订单状态同步API端点
提供订单状态同步的REST API接口
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum

from app.core.database import get_async_db
from app.core.tenant_auth_dependency import verify_tenant_auth
from app.core.logging import get_logger
from app.models.tenant import Tenant
from app.models.user import User
from app.services.enhanced_order_status_sync_service import (
    EnhancedOrderStatusSyncService,
    SyncDirection
)

logger = get_logger(__name__)
router = APIRouter()


class SyncDirectionEnum(str, Enum):
    """同步方向枚举"""
    PRINTIFY_TO_SCM = "printify_to_scm"
    SCM_TO_SHOPIFY = "scm_to_shopify"
    SHOPIFY_TO_SCM = "shopify_to_scm"


class OrderStatusSyncRequest(BaseModel):
    """订单状态同步请求"""
    order_id: int = Field(..., description="订单ID")
    direction: SyncDirectionEnum = Field(..., description="同步方向")
    force_sync: bool = Field(False, description="是否强制同步")


class BatchSyncRequest(BaseModel):
    """批量同步请求"""
    direction: SyncDirectionEnum = Field(..., description="同步方向")
    limit: int = Field(100, ge=1, le=1000, description="最大处理数量")
    status_filter: Optional[List[str]] = Field(None, description="状态过滤器")


class SyncResponse(BaseModel):
    """同步响应"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/sync/order", response_model=SyncResponse)
async def sync_order_status(
    request: OrderStatusSyncRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    同步单个订单状态
    """
    tenant, user = auth
    
    logger.info(
        "🔍 开始同步单个订单状态",
        order_id=request.order_id,
        direction=request.direction,
        tenant_id=tenant.id,
        user_id=user.id,
        force_sync=request.force_sync
    )
    
    try:
        # 创建增强的状态同步服务
        sync_service = EnhancedOrderStatusSyncService(db)
        
        # 转换同步方向
        direction = SyncDirection(request.direction.value)
        
        # 执行同步
        result = await sync_service.sync_order_status(
            order_id=request.order_id,
            direction=direction,
            tenant_id=tenant.id,
            force_sync=request.force_sync
        )
        
        if result.get("success"):
            logger.info(
                "✅ 订单状态同步成功",
                order_id=request.order_id,
                direction=request.direction,
                result=result
            )
            return SyncResponse(
                success=True,
                message=result.get("message", "同步成功"),
                data=result
            )
        else:
            logger.warning(
                "⚠️ 订单状态同步失败",
                order_id=request.order_id,
                direction=request.direction,
                result=result
            )
            return SyncResponse(
                success=False,
                message=result.get("message", "同步失败"),
                error=result.get("error")
            )
            
    except Exception as e:
        logger.error(
            "❌ 订单状态同步异常",
            order_id=request.order_id,
            direction=request.direction,
            error=str(e)
        )
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"订单状态同步失败: {str(e)}"
        )


@router.post("/sync/batch", response_model=SyncResponse)
async def batch_sync_orders(
    request: BatchSyncRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    批量同步订单状态
    """
    tenant, user = auth
    
    logger.info(
        "🔍 开始批量同步订单状态",
        direction=request.direction,
        limit=request.limit,
        status_filter=request.status_filter,
        tenant_id=tenant.id,
        user_id=user.id
    )
    
    try:
        # 创建增强的状态同步服务
        sync_service = EnhancedOrderStatusSyncService(db)
        
        # 转换同步方向
        direction = SyncDirection(request.direction.value)
        
        # 执行批量同步
        result = await sync_service.batch_sync_orders(
            direction=direction,
            tenant_id=tenant.id,
            limit=request.limit,
            status_filter=request.status_filter
        )
        
        if result.get("success"):
            logger.info(
                "✅ 批量同步订单状态成功",
                direction=request.direction,
                result=result
            )
            return SyncResponse(
                success=True,
                message=result.get("message", "批量同步成功"),
                data=result
            )
        else:
            logger.warning(
                "⚠️ 批量同步订单状态失败",
                direction=request.direction,
                result=result
            )
            return SyncResponse(
                success=False,
                message=result.get("message", "批量同步失败"),
                error=result.get("error")
            )
            
    except Exception as e:
        logger.error(
            "❌ 批量同步订单状态异常",
            direction=request.direction,
            error=str(e)
        )
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量同步订单状态失败: {str(e)}"
        )


@router.get("/sync/status/{order_id}")
async def get_sync_status(
    order_id: int,
    direction: SyncDirectionEnum = Query(..., description="同步方向"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    获取订单同步状态
    """
    tenant, user = auth
    
    logger.info(
        "🔍 获取订单同步状态",
        order_id=order_id,
        direction=direction,
        tenant_id=tenant.id,
        user_id=user.id
    )
    
    try:
        # 创建增强的状态同步服务
        sync_service = EnhancedOrderStatusSyncService(db)
        
        # 检查同步历史
        sync_key = f"{order_id}_{direction.value}"
        is_recently_synced = sync_service._is_recently_synced(sync_key)
        
        if is_recently_synced:
            sync_history = sync_service.sync_history.get(sync_key, {})
            return {
                "success": True,
                "order_id": order_id,
                "direction": direction.value,
                "recently_synced": True,
                "last_sync": sync_history.get("timestamp"),
                "last_result": sync_history.get("result")
            }
        else:
            return {
                "success": True,
                "order_id": order_id,
                "direction": direction.value,
                "recently_synced": False,
                "message": "最近未同步"
            }
            
    except Exception as e:
        logger.error(
            "❌ 获取订单同步状态失败",
            order_id=order_id,
            direction=direction,
            error=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取订单同步状态失败: {str(e)}"
        )


@router.get("/sync/history")
async def get_sync_history(
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    获取同步历史记录
    """
    tenant, user = auth
    
    logger.info(
        "🔍 获取同步历史记录",
        limit=limit,
        tenant_id=tenant.id,
        user_id=user.id
    )
    
    try:
        # 创建增强的状态同步服务
        sync_service = EnhancedOrderStatusSyncService(db)
        
        # 获取同步历史（按时间倒序）
        history_items = []
        for sync_key, sync_data in sync_service.sync_history.items():
            history_items.append({
                "sync_key": sync_key,
                "timestamp": sync_data.get("timestamp"),
                "result": sync_data.get("result")
            })
        
        # 按时间排序并限制数量
        history_items.sort(key=lambda x: x["timestamp"], reverse=True)
        history_items = history_items[:limit]
        
        return {
            "success": True,
            "total_count": len(sync_service.sync_history),
            "returned_count": len(history_items),
            "history": history_items
        }
        
    except Exception as e:
        logger.error(
            "❌ 获取同步历史记录失败",
            error=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取同步历史记录失败: {str(e)}"
        )


@router.post("/sync/printify-to-scm")
async def sync_printify_to_scm(
    order_id: int = Query(..., description="订单ID"),
    force_sync: bool = Query(False, description="是否强制同步"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    同步Printify订单状态到SCM（便捷接口）
    """
    tenant, user = auth
    
    logger.info(
        "🔍 同步Printify订单状态到SCM",
        order_id=order_id,
        tenant_id=tenant.id,
        user_id=user.id,
        force_sync=force_sync
    )
    
    try:
        # 创建增强的状态同步服务
        sync_service = EnhancedOrderStatusSyncService(db)
        
        # 执行同步
        result = await sync_service.sync_order_status(
            order_id=order_id,
            direction=SyncDirection.PRINTIFY_TO_SCM,
            tenant_id=tenant.id,
            force_sync=force_sync
        )
        
        return {
            "success": result.get("success", False),
            "message": result.get("message", "同步完成"),
            "data": result
        }
        
    except Exception as e:
        logger.error(
            "❌ 同步Printify订单状态到SCM失败",
            order_id=order_id,
            error=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"同步Printify订单状态到SCM失败: {str(e)}"
        )


@router.post("/sync/scm-to-shopify")
async def sync_scm_to_shopify(
    order_id: int = Query(..., description="订单ID"),
    force_sync: bool = Query(False, description="是否强制同步"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    同步SCM订单状态到Shopify（便捷接口）
    """
    tenant, user = auth
    
    logger.info(
        "🔍 同步SCM订单状态到Shopify",
        order_id=order_id,
        tenant_id=tenant.id,
        user_id=user.id,
        force_sync=force_sync
    )
    
    try:
        # 创建增强的状态同步服务
        sync_service = EnhancedOrderStatusSyncService(db)
        
        # 执行同步
        result = await sync_service.sync_order_status(
            order_id=order_id,
            direction=SyncDirection.SCM_TO_SHOPIFY,
            tenant_id=tenant.id,
            force_sync=force_sync
        )
        
        return {
            "success": result.get("success", False),
            "message": result.get("message", "同步完成"),
            "data": result
        }
        
    except Exception as e:
        logger.error(
            "❌ 同步SCM订单状态到Shopify失败",
            order_id=order_id,
            error=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"同步SCM订单状态到Shopify失败: {str(e)}"
        )
