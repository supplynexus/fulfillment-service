"""
订单自动化API端点
用于手动触发订单自动化流程
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.timestamp_auth_middleware import verify_timestamp_auth
from app.tasks.order_automation_tasks import (
    process_new_shopify_orders,
    sync_printify_orders_status,
    sync_scm_to_shopify_fulfillment,
)
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/process-shopify-orders", response_model=dict)
async def trigger_process_shopify_orders(
    tenant_id: int = Query(..., description="租户ID"),
    limit: int = Query(50, ge=1, le=200, description="处理订单数量限制"),
    db: AsyncSession = Depends(get_async_db),
    auth: dict = Depends(verify_timestamp_auth),
) -> Any:
    """
    手动触发处理新的Shopify订单
    """
    try:
        logger.info("🔍 手动触发处理Shopify订单", tenant_id=tenant_id, limit=limit)

        # 验证租户访问权限
        if auth.get("tenant_id") != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant",
            )

        # 异步执行任务
        task = process_new_shopify_orders.delay(tenant_id, limit)

        return {
            "success": True,
            "message": "Shopify订单处理任务已启动",
            "task_id": task.id,
            "tenant_id": tenant_id,
            "limit": limit,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ 触发处理Shopify订单失败", tenant_id=tenant_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering Shopify order processing: {str(e)}",
        )


@router.post("/sync-printify-status", response_model=dict)
async def trigger_sync_printify_status(
    tenant_id: int = Query(..., description="租户ID"),
    limit: int = Query(100, ge=1, le=500, description="同步订单数量限制"),
    db: AsyncSession = Depends(get_async_db),
    auth: dict = Depends(verify_timestamp_auth),
) -> Any:
    """
    手动触发同步Printify订单状态
    """
    try:
        logger.info("🔍 手动触发同步Printify状态", tenant_id=tenant_id, limit=limit)

        # 验证租户访问权限
        if auth.get("tenant_id") != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant",
            )

        # 异步执行任务
        task = sync_printify_orders_status.delay(tenant_id, limit)

        return {
            "success": True,
            "message": "Printify状态同步任务已启动",
            "task_id": task.id,
            "tenant_id": tenant_id,
            "limit": limit,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ 触发同步Printify状态失败", tenant_id=tenant_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering Printify status sync: {str(e)}",
        )


@router.post("/sync-shopify-fulfillment", response_model=dict)
async def trigger_sync_shopify_fulfillment(
    tenant_id: int = Query(..., description="租户ID"),
    limit: int = Query(100, ge=1, le=500, description="同步订单数量限制"),
    db: AsyncSession = Depends(get_async_db),
    auth: dict = Depends(verify_timestamp_auth),
) -> Any:
    """
    手动触发同步SCM订单到Shopify履约
    """
    try:
        logger.info("🔍 手动触发同步Shopify履约", tenant_id=tenant_id, limit=limit)

        # 验证租户访问权限
        if auth.get("tenant_id") != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant",
            )

        # 异步执行任务
        task = sync_scm_to_shopify_fulfillment.delay(tenant_id, limit)

        return {
            "success": True,
            "message": "Shopify履约同步任务已启动",
            "task_id": task.id,
            "tenant_id": tenant_id,
            "limit": limit,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ 触发同步Shopify履约失败", tenant_id=tenant_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering Shopify fulfillment sync: {str(e)}",
        )


@router.post("/sync-all", response_model=dict)
async def trigger_full_sync(
    tenant_id: int = Query(..., description="租户ID"),
    process_limit: int = Query(50, ge=1, le=200, description="处理订单数量限制"),
    sync_limit: int = Query(100, ge=1, le=500, description="同步订单数量限制"),
    db: AsyncSession = Depends(get_async_db),
    auth: dict = Depends(verify_timestamp_auth),
) -> Any:
    """
    手动触发完整的订单同步流程
    包括：处理Shopify订单 -> 同步Printify状态 -> 同步Shopify履约
    """
    try:
        logger.info(
            "🔍 手动触发完整订单同步流程",
            tenant_id=tenant_id,
            process_limit=process_limit,
            sync_limit=sync_limit,
        )

        # 验证租户访问权限
        if auth.get("tenant_id") != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant",
            )

        # 依次启动所有任务
        task1 = process_new_shopify_orders.delay(tenant_id, process_limit)
        task2 = sync_printify_orders_status.delay(tenant_id, sync_limit)
        task3 = sync_scm_to_shopify_fulfillment.delay(tenant_id, sync_limit)

        return {
            "success": True,
            "message": "完整订单同步流程已启动",
            "tasks": {
                "process_shopify_orders": task1.id,
                "sync_printify_status": task2.id,
                "sync_shopify_fulfillment": task3.id,
            },
            "tenant_id": tenant_id,
            "process_limit": process_limit,
            "sync_limit": sync_limit,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ 触发完整订单同步流程失败", tenant_id=tenant_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering full sync process: {str(e)}",
        )


@router.get("/task-status/{task_id}", response_model=dict)
async def get_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_async_db),
    auth: dict = Depends(verify_timestamp_auth),
) -> Any:
    """
    获取任务执行状态
    """
    try:
        from celery.result import AsyncResult

        # 获取任务结果
        result = AsyncResult(task_id)

        if result.state == "PENDING":
            response = {
                "state": result.state,
                "status": "Task is waiting to be processed...",
            }
        elif result.state == "PROGRESS":
            response = {
                "state": result.state,
                "current": result.info.get("current", 0),
                "total": result.info.get("total", 1),
                "status": result.info.get("status", ""),
            }
        elif result.state == "SUCCESS":
            response = {"state": result.state, "result": result.result}
        else:  # FAILURE
            response = {"state": result.state, "error": str(result.info)}

        return response

    except Exception as e:
        logger.error("❌ 获取任务状态失败", task_id=task_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting task status: {str(e)}",
        )
