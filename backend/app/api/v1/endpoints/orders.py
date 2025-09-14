"""
Order management endpoints
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

from app.core.database import get_async_db
from app.core.tenant_auth_dependency import verify_tenant_auth
from app.models.tenant import Tenant
from app.models.user import User
from app.models.external_system import ExternalSystemType
from app.schemas.order import OrderResponse, OrderListResponse, OrderSyncResponse
from app.services.shopify.order_service import ShopifyOrderService
from app.services.printify_service import PrintifyService
from app.services.external_system_service import ExternalSystemService
from app.tasks.shopify_tasks import sync_shopify_orders_task

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=OrderListResponse)
async def get_orders(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> OrderListResponse:
    """
    获取订单列表
    """
    from app.core.logging import RequestLogger
    logger = RequestLogger("orders.get_orders")
    
    try:
        logger.info(f"🔍 开始处理订单列表请求: skip={skip}, limit={limit}, status={status}")
        
        tenant, user = auth
        logger.info(f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}")
        
        logger.info(f"🔍 初始化 ShopifyOrderService...")
        order_service = ShopifyOrderService(db)
        logger.info(f"✅ ShopifyOrderService 初始化成功")
        
        if status:
            logger.info(f"🔍 按状态查询订单: status={status}, limit={limit}")
            try:
                orders = await order_service.get_orders_by_status(
                    tenant_id=tenant.id,
                    status=status,
                    limit=limit
                )
                total = len(orders)
                logger.info(f"✅ 按状态查询成功: 找到 {total} 个订单")
            except Exception as e:
                logger.error(f"❌ 按状态查询订单失败: {str(e)}")
                import traceback
                logger.error(f"   异常堆栈: {traceback.format_exc()}")
                raise HTTPException(status_code=500, detail=f"Failed to get orders by status: {str(e)}")
        else:
            logger.info(f"🔍 查询所有订单: limit={limit}")
            try:
                orders = await order_service.get_all_orders(
                    tenant_id=tenant.id,
                    limit=limit
                )
                total = len(orders)
                logger.info(f"✅ 查询所有订单成功: 找到 {total} 个订单")
            except Exception as e:
                logger.error(f"❌ 查询所有订单失败: {str(e)}")
                import traceback
                logger.error(f"   异常堆栈: {traceback.format_exc()}")
                raise HTTPException(status_code=500, detail=f"Failed to get all orders: {str(e)}")
        
        # 转换为响应格式
        logger.info(f"🔍 转换订单响应格式...")
        try:
            order_responses = []
            for order in orders:
                order_responses.append(OrderResponse.from_orm(order))
            logger.info(f"✅ 订单响应格式转换成功: {len(order_responses)} 个订单")
        except Exception as e:
            logger.error(f"❌ 转换订单响应格式失败: {str(e)}")
            import traceback
            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Failed to convert order responses: {str(e)}")
        
        # 返回符合 OrderListResponse 模型的数据结构
        result = {
            "orders": order_responses,
            "total": total,
            "skip": skip,
            "limit": limit
        }
        
        logger.info(f"✅ 订单列表请求处理成功: total={total}, skip={skip}, limit={limit}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 订单列表请求处理失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> OrderResponse:
    """
    获取单个订单详情
    """
    tenant, user = auth
    
    logger.info(f"🔍 开始处理订单详情请求: order_id={order_id}, tenant_id={tenant.id}")
    
    try:
        order_service = ShopifyOrderService(db)
        
        # 获取订单详情
        order = await order_service.get_order_by_id(
            order_id=order_id,
            tenant_id=tenant.id
        )
        
        if not order:
            logger.warning(f"⚠️ 订单不存在: order_id={order_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="Order not found")
        
        # 转换为响应格式
        order_response = OrderResponse.from_orm(order)
        
        logger.info(f"✅ 订单详情请求处理成功: order_id={order_id}")
        return order_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 订单详情请求处理失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/sync", response_model=OrderSyncResponse)
async def sync_orders(
    sync_recent_only: bool = True,
    max_orders: Optional[int] = 100,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> OrderSyncResponse:
    """
    手动触发订单同步
    """
    tenant, user = auth
    
    order_service = ShopifyOrderService(db)
    
    try:
        result = await order_service.sync_orders(
            tenant_id=tenant.id,
            sync_recent_only=sync_recent_only,
            max_orders=max_orders
        )
        
        return OrderSyncResponse(**result)
        
    except Exception as e:
        return OrderSyncResponse(
            success=False,
            error=str(e),
            orders_fetched=0,
            orders_saved=0,
            orders_updated=0,
            errors=[str(e)]
        )


@router.post("/sync/background")
async def sync_orders_background(
    sync_recent_only: bool = True,
    max_orders: Optional[int] = 100,
    background_tasks: BackgroundTasks = None,
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    后台异步同步订单
    """
    tenant, user = auth
    
    # 启动后台任务
    task = sync_shopify_orders_task.delay(
        tenant_id=tenant.id,
        sync_recent_only=sync_recent_only,
        max_orders=max_orders
    )
    
    return {
        "message": "订单同步任务已启动",
        "task_id": task.id,
        "status": "PENDING"
    }


@router.post("/sync/full")
async def full_sync_orders(
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    完全重新同步所有Shopify订单（不限制数量和时间）
    """
    tenant, user = auth
    
    # 启动后台任务，完全重新同步
    task = sync_shopify_orders_task.delay(
        tenant_id=tenant.id,
        sync_recent_only=False,  # 完全重新同步
        max_orders=None  # 不限制数量
    )
    
    return {
        "message": "完全重新同步任务已启动",
        "task_id": task.id,
        "status": "PENDING",
        "sync_type": "full_resync"
    }


@router.get("/recent", response_model=List[OrderResponse])
async def get_recent_orders(
    hours: int = 24,
    limit: int = 50,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> List[OrderResponse]:
    """
    获取最近的订单
    """
    tenant, user = auth
    
    order_service = ShopifyOrderService(db)
    orders = await order_service.get_recent_orders(
        tenant_id=tenant.id,
        hours=hours,
        limit=limit
    )
    
    return [OrderResponse.from_orm(order) for order in orders]


@router.get("/status/{status}", response_model=List[OrderResponse])
async def get_orders_by_status(
    status: str,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> List[OrderResponse]:
    """
    根据状态获取订单
    """
    tenant, user = auth
    
    order_service = ShopifyOrderService(db)
    orders = await order_service.get_orders_by_status(
        tenant_id=tenant.id,
        status=status,
        limit=limit
    )
    
    return [OrderResponse.from_orm(order) for order in orders]


@router.post("/{order_id}/create-shipping-label")
async def create_shipping_label(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    为订单创建发货单 (通过 Printify API)
    """
    tenant, user = auth
    
    logger.info(f"🚚 开始创建发货单: order_id={order_id}, tenant_id={tenant.id}")
    
    try:
        # 获取订单详情
        order_service = ShopifyOrderService(db)
        order = await order_service.get_order_by_id(
            order_id=order_id,
            tenant_id=tenant.id
        )
        
        if not order:
            logger.error(f"❌ 订单不存在: order_id={order_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="订单不存在")
        
        logger.info(f"✅ 找到订单: {order.id}, external_order_id={order.external_order_id}")
        
        # 获取 Printify 配置
        from app.services.external_system_service import ExternalSystemService
        external_system_service = ExternalSystemService(db)
        
        # 查找 Printify 配置
        printify_configs = await external_system_service.get_external_systems_by_type(
            tenant_id=tenant.id,
            system_type=ExternalSystemType.PRINTIFY
        )
        
        if not printify_configs:
            logger.error(f"❌ 未找到 Printify 配置: tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="未找到 Printify 配置")
        
        # 使用第一个 Printify 配置
        printify_config = printify_configs[0]
        
        logger.info(f"✅ 找到 Printify 配置: {printify_config.id}")
        
        # 获取解密的 Printify 凭据
        credentials = await external_system_service.get_decrypted_credentials(
            external_system_id=printify_config.id,
            tenant_id=tenant.id
        )
        
        if not credentials:
            logger.error(f"❌ 无法解密 Printify 凭据: printify_config_id={printify_config.id}")
            raise HTTPException(status_code=400, detail="无法解密 Printify 凭据")
        
        access_token = credentials.get("access_token")
        shop_id = credentials.get("shop_id")
        
        if not access_token or not shop_id:
            logger.error(f"❌ Printify 凭据不完整: access_token={bool(access_token)}, shop_id={shop_id}")
            raise HTTPException(status_code=400, detail="Printify 凭据不完整")
        
        # 创建 Printify 服务实例
        printify_service = PrintifyService(access_token)
        
        # 从订单的原始数据中提取 Shopify 订单信息
        shopify_raw_data = order.shopify_raw_data
        if not shopify_raw_data:
            logger.error(f"❌ 订单缺少 Shopify 原始数据: order_id={order_id}")
            raise HTTPException(status_code=400, detail="订单缺少 Shopify 原始数据")
        
        logger.info(f"📦 开始创建 Printify 订单...")
        
        # 创建 Printify 订单
        printify_order = await printify_service.create_shipping_label_from_shopify_order(
            shop_id=shop_id,
            shopify_order=shopify_raw_data
        )
        
        if not printify_order:
            logger.error(f"❌ 创建 Printify 订单失败: order_id={order_id}")
            raise HTTPException(status_code=500, detail="创建 Printify 订单失败")
        
        logger.info(f"✅ 成功创建 Printify 订单: {printify_order.get('id')}")
        
        return {
            "success": True,
            "message": "发货单创建成功",
            "printify_order_id": printify_order.get("id"),
            "external_id": printify_order.get("external_id"),
            "status": printify_order.get("status"),
            "total_price": printify_order.get("total_price"),
            "created_at": printify_order.get("created_at")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 创建发货单时发生错误: {e}")
        raise HTTPException(status_code=500, detail=f"创建发货单失败: {str(e)}")