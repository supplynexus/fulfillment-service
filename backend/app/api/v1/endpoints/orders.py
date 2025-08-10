"""
订单相关的 API 端点
包括批量获取和同步功能
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from celery.result import AsyncResult

from app.core.database import get_async_db
from app.models.order import Order
from app.schemas.order import Order as OrderSchema, OrderCreate
from app.tasks.shopify_tasks import (
    fetch_shopify_orders_task,
    fetch_recent_orders_task,
    fetch_unfulfilled_orders_task,
    sync_all_orders_task
)
from app.core.config import settings

router = APIRouter()


@router.get("/", response_model=List[OrderSchema])
def get_orders(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db)
):
    """获取订单列表"""
    orders = db.query(Order).offset(skip).limit(limit).all()
    return orders


@router.get("/{order_id}", response_model=OrderSchema)
def get_order(order_id: int, db: AsyncSession = Depends(get_async_db)):
    """获取单个订单"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单未找到")
    return order


@router.post("/sync/batch")
def start_batch_sync(
    query_filter: Optional[str] = Query(None, description="订单过滤条件"),
    max_orders: Optional[int] = Query(None, description="最大订单数量"),
    shop_name: Optional[str] = Query(None, description="商店名称"),
    access_token: Optional[str] = Query(None, description="访问令牌")
):
    """
    启动批量订单同步任务
    
    Args:
        query_filter: 订单过滤条件，例如:
            - "created_at:>2024-01-01"
            - "financial_status:paid"  
            - "fulfillment_status:unfulfilled"
        max_orders: 最大订单数量限制
        shop_name: Shopify 商店名称（可选，默认使用配置）
        access_token: API 访问令牌（可选，默认使用配置）
    """
    # 使用提供的参数或默认配置
    shop_name = shop_name or settings.SHOPIFY_SHOP_NAME
    access_token = access_token or settings.SHOPIFY_ACCESS_TOKEN
    
    if not shop_name or not access_token:
        raise HTTPException(
            status_code=400, 
            detail="缺少 Shopify 配置信息"
        )
    
    # 启动异步任务
    task = fetch_shopify_orders_task.delay(
        shop_name=shop_name,
        access_token=access_token,
        query_filter=query_filter,
        max_orders=max_orders
    )
    
    return {
        "task_id": task.id,
        "status": "任务已启动",
        "message": "批量订单同步任务已在后台开始执行"
    }


@router.post("/sync/recent")
def sync_recent_orders(
    hours: int = Query(24, description="最近几小时"),
    shop_name: Optional[str] = Query(None),
    access_token: Optional[str] = Query(None)
):
    """同步最近的订单"""
    shop_name = shop_name or settings.SHOPIFY_SHOP_NAME
    access_token = access_token or settings.SHOPIFY_ACCESS_TOKEN
    
    if not shop_name or not access_token:
        raise HTTPException(status_code=400, detail="缺少 Shopify 配置信息")
    
    task = fetch_recent_orders_task.delay(
        shop_name=shop_name,
        access_token=access_token,
        hours=hours
    )
    
    return {
        "task_id": task.id,
        "status": "任务已启动",
        "message": f"同步最近 {hours} 小时的订单"
    }


@router.post("/sync/unfulfilled")
def sync_unfulfilled_orders(
    shop_name: Optional[str] = Query(None),
    access_token: Optional[str] = Query(None)
):
    """同步未履约的订单"""
    shop_name = shop_name or settings.SHOPIFY_SHOP_NAME
    access_token = access_token or settings.SHOPIFY_ACCESS_TOKEN
    
    if not shop_name or not access_token:
        raise HTTPException(status_code=400, detail="缺少 Shopify 配置信息")
    
    task = fetch_unfulfilled_orders_task.delay(
        shop_name=shop_name,
        access_token=access_token
    )
    
    return {
        "task_id": task.id,
        "status": "任务已启动",
        "message": "同步未履约订单任务已启动"
    }


@router.post("/sync/all")
def sync_all_orders(
    shop_name: Optional[str] = Query(None),
    access_token: Optional[str] = Query(None)
):
    """同步所有订单（初始导入）"""
    shop_name = shop_name or settings.SHOPIFY_SHOP_NAME
    access_token = access_token or settings.SHOPIFY_ACCESS_TOKEN
    
    if not shop_name or not access_token:
        raise HTTPException(status_code=400, detail="缺少 Shopify 配置信息")
    
    task = sync_all_orders_task.delay(
        shop_name=shop_name,
        access_token=access_token
    )
    
    return {
        "task_id": task.id,
        "status": "任务已启动",
        "message": "全量订单同步任务已启动（此操作可能需要较长时间）"
    }


@router.get("/tasks/{task_id}")
def get_task_status(task_id: str):
    """获取任务状态"""
    task = AsyncResult(task_id)
    
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'status': '任务等待中...'
        }
    elif task.state == 'PROGRESS':
        response = {
            'state': task.state,
            'status': task.info.get('status', ''),
            'progress': task.info.get('progress', 0),
            'orders_saved': task.info.get('orders_saved', 0)
        }
    elif task.state == 'SUCCESS':
        response = {
            'state': task.state,
            'status': '任务完成',
            'result': task.result
        }
    else:  # FAILURE
        response = {
            'state': task.state,
            'status': '任务失败',
            'error': str(task.info)
        }
    
    return response


@router.get("/stats/summary")
def get_order_stats(db: AsyncSession = Depends(get_async_db)):
    """获取订单统计信息"""
    total_orders = db.query(Order).count()
    paid_orders = db.query(Order).filter(Order.financial_status == 'PAID').count()
    unfulfilled_orders = db.query(Order).filter(Order.fulfillment_status == 'UNFULFILLED').count()
    
    return {
        "total_orders": total_orders,
        "paid_orders": paid_orders,
        "unfulfilled_orders": unfulfilled_orders,
        "fulfillment_rate": round((total_orders - unfulfilled_orders) / total_orders * 100, 2) if total_orders > 0 else 0
    }