"""
SCM Orders API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_async_db
from app.core.tenant_auth_dependency import verify_tenant_auth
from app.models.tenant import Tenant
from app.models.user import User
from app.models.order import Order
from app.models.scm_order import SCMOrder
from app.schemas.scm_order import SCMOrderResponse, SCMOrderListResponse, SCMOrderCreate
from app.services.order_routing_service import OrderRoutingService

router = APIRouter()


@router.get("/", response_model=SCMOrderListResponse)
async def get_scm_orders(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    status: Optional[str] = Query(None, description="Filter by status"),
    target_system_type: Optional[str] = Query(
        None, description="Filter by target system type"
    ),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> SCMOrderListResponse:
    """
    获取SCM订单列表
    """
    from app.core.logging import RequestLogger

    logger = RequestLogger("scm_orders.get_scm_orders")

    try:
        logger.info(
            f"🔍 开始处理SCM订单列表请求: skip={skip}, limit={limit}, status={status}, target_system_type={target_system_type}"
        )

        tenant, user = auth
        logger.info(
            f"✅ 认证成功: tenant_id={tenant.id}, tenant_name={tenant.name}, user_id={user.id}"
        )

        # 构建查询
        logger.info(f"🔍 构建SCM订单查询...")
        query = select(SCMOrder).where(SCMOrder.tenant_id == tenant.id)

        # 应用过滤器
        if status:
            query = query.where(SCMOrder.status == status)
            logger.info(f"🔍 应用状态过滤器: status={status}")
        if target_system_type:
            query = query.where(SCMOrder.target_system_type == target_system_type)
            logger.info(
                f"🔍 应用系统类型过滤器: target_system_type={target_system_type}"
            )

        # 获取总数
        logger.info(f"🔍 查询SCM订单总数...")
        try:
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar()
            logger.info(f"✅ 查询总数成功: total={total}")
        except Exception as e:
            logger.error(f"❌ 查询总数失败: {str(e)}")
            import traceback

            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            raise HTTPException(
                status_code=500, detail=f"Failed to get SCM orders count: {str(e)}"
            )

        # 分页查询
        logger.info(f"🔍 执行分页查询: skip={skip}, limit={limit}")
        try:
            query = query.order_by(SCMOrder.created_at.desc()).offset(skip).limit(limit)
            result = await db.execute(query)
            scm_orders = result.scalars().all()
            logger.info(f"✅ 分页查询成功: 找到 {len(scm_orders)} 个SCM订单")
        except Exception as e:
            logger.error(f"❌ 分页查询失败: {str(e)}")
            import traceback

            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            raise HTTPException(
                status_code=500, detail=f"Failed to get SCM orders: {str(e)}"
            )

        # 转换为响应格式
        logger.info(f"🔍 转换SCM订单响应格式...")
        try:
            scm_order_responses = [
                SCMOrderResponse.from_orm(scm_order) for scm_order in scm_orders
            ]
            logger.info(f"✅ 响应格式转换成功: {len(scm_order_responses)} 个SCM订单")
        except Exception as e:
            logger.error(f"❌ 转换响应格式失败: {str(e)}")
            import traceback

            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to convert SCM order responses: {str(e)}",
            )

        result = SCMOrderListResponse(
            scm_orders=scm_order_responses, total=total, skip=skip, limit=limit
        )

        logger.info(
            f"✅ SCM订单列表请求处理成功: total={total}, skip={skip}, limit={limit}"
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ SCM订单列表请求处理失败: {str(e)}")
        import traceback

        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{scm_order_id}", response_model=SCMOrderResponse)
async def get_scm_order(
    scm_order_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> SCMOrderResponse:
    """
    获取SCM订单详情
    """
    tenant, user = auth

    result = await db.execute(
        select(SCMOrder).where(
            SCMOrder.id == scm_order_id, SCMOrder.tenant_id == tenant.id
        )
    )
    scm_order = result.scalar_one_or_none()

    if not scm_order:
        raise HTTPException(status_code=404, detail="SCM order not found")

    return SCMOrderResponse.from_orm(scm_order)


@router.get("/order/{order_id}", response_model=List[SCMOrderResponse])
async def get_scm_orders_by_order_id(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> List[SCMOrderResponse]:
    """
    根据原始订单ID获取SCM订单
    """
    tenant, user = auth

    # 验证原始订单存在
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.tenant_id == tenant.id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # 获取SCM订单
    routing_service = OrderRoutingService(db)
    scm_orders = await routing_service.get_scm_orders_by_order_id(order_id, tenant.id)

    return [SCMOrderResponse.from_orm(scm_order) for scm_order in scm_orders]


@router.post("/", response_model=SCMOrderResponse)
async def create_scm_order(
    scm_order_data: SCMOrderCreate,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> SCMOrderResponse:
    """
    手动创建SCM订单
    """
    tenant, user = auth

    # 验证原始订单存在
    result = await db.execute(
        select(Order).where(
            Order.id == scm_order_data.source_order_id, Order.tenant_id == tenant.id
        )
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Source order not found")

    # 创建SCM订单
    scm_order = SCMOrder(
        tenant_id=tenant.id,
        source_order_id=scm_order_data.source_order_id,
        target_system_type=scm_order_data.target_system_type,
        target_system_id=scm_order_data.target_system_id,
        routing_strategy=scm_order_data.routing_strategy,
        line_items=scm_order_data.line_items,
        total_amount=scm_order_data.total_amount,
        currency=scm_order_data.currency,
        customer_email=scm_order_data.customer_email,
        customer_name=scm_order_data.customer_name,
        customer_phone=scm_order_data.customer_phone,
        shipping_address=scm_order_data.shipping_address,
        billing_address=scm_order_data.billing_address,
        routing_metadata=scm_order_data.routing_metadata,
        shopify_order_id=scm_order_data.shopify_order_id,
    )

    db.add(scm_order)
    await db.commit()
    await db.refresh(scm_order)

    return SCMOrderResponse.from_orm(scm_order)


@router.put("/{scm_order_id}", response_model=SCMOrderResponse)
async def update_scm_order(
    scm_order_id: int,
    status: Optional[str] = None,
    target_system_id: Optional[str] = None,
    tracking_number: Optional[str] = None,
    tracking_url: Optional[str] = None,
    fulfillment_status: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> SCMOrderResponse:
    """
    更新SCM订单
    """
    tenant, user = auth

    routing_service = OrderRoutingService(db)

    # 准备更新字段
    update_fields = {}
    if status is not None:
        update_fields["status"] = status
    if target_system_id is not None:
        update_fields["target_system_id"] = target_system_id
    if tracking_number is not None:
        update_fields["tracking_number"] = tracking_number
    if tracking_url is not None:
        update_fields["tracking_url"] = tracking_url
    if fulfillment_status is not None:
        update_fields["fulfillment_status"] = fulfillment_status

    scm_order = await routing_service.update_scm_order_status(
        scm_order_id, status or "updated", tenant.id, **update_fields
    )

    if not scm_order:
        raise HTTPException(status_code=404, detail="SCM order not found")

    return SCMOrderResponse.from_orm(scm_order)


@router.delete("/{scm_order_id}")
async def delete_scm_order(
    scm_order_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
):
    """
    删除SCM订单
    """
    tenant, user = auth

    result = await db.execute(
        select(SCMOrder).where(
            SCMOrder.id == scm_order_id, SCMOrder.tenant_id == tenant.id
        )
    )
    scm_order = result.scalar_one_or_none()

    if not scm_order:
        raise HTTPException(status_code=404, detail="SCM order not found")

    # 检查是否可以删除（只有创建状态的订单可以删除）
    if scm_order.status not in ["created", "failed"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete SCM order with status: " + scm_order.status,
        )

    await db.delete(scm_order)
    await db.commit()

    return {"message": "SCM order deleted successfully"}


@router.post("/sync-printify-orders", response_model=dict)
async def sync_printify_orders(
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> dict:
    """
    同步Printify发货单到SCM订单
    """
    from app.core.logging import get_logger
    from app.services.external_system_service import ExternalSystemService
    from app.services.printify_service import PrintifyService
    from app.core.security import decrypt_data

    logger = get_logger(__name__)

    try:
        logger.info("🔍 开始同步 Printify 发货单", tenant_id=auth[0].id)

        tenant, user = auth

        # 获取所有Printify外部系统
        service = ExternalSystemService(db)
        printify_systems = await service.get_external_systems_by_type(
            tenant.id, "PRINTIFY"
        )

        if not printify_systems:
            logger.warning("⚠️ 没有找到 Printify 外部系统")
            return {
                "success": False,
                "message": "没有找到 Printify 外部系统，请先配置 Printify 连接",
                "synced_count": 0,
            }

        total_synced = 0
        total_errors = 0
        errors = []

        # 为每个Printify系统同步发货单
        for printify_system in printify_systems:
            try:
                logger.info(f"🔍 开始同步 Printify 系统: {printify_system.name}")

                # 解密凭据
                access_token = decrypt_data(
                    printify_system.credentials.get("access_token", "")
                )

                if not access_token:
                    logger.warning(
                        f"⚠️ Printify 系统 {printify_system.name} 没有访问令牌"
                    )
                    continue

                # 创建Printify服务
                printify_service = PrintifyService(access_token)

                # 首先获取所有店铺
                logger.info(f"🔍 开始获取 Printify 店铺列表...")
                shops = await printify_service.get_shops()
                logger.info(f"📊 获取到 {len(shops) if shops else 0} 个 Printify 店铺")

                if not shops:
                    logger.warning(
                        f"⚠️ Printify 系统 {printify_system.name} 没有店铺或获取店铺失败"
                    )
                    continue

                # 为每个店铺获取发货单
                all_orders = []
                for shop in shops:
                    shop_id = shop.get("id")
                    if not shop_id:
                        continue

                    logger.info(f"🔍 获取店铺 {shop.get('title', shop_id)} 的发货单")
                    orders_result = await printify_service.get_orders(shop_id)
                    logger.info(
                        f"📊 店铺 {shop.get('title', shop_id)} 订单API结果: success={orders_result.get('success')}, orders_count={len(orders_result.get('orders', []))}"
                    )

                    if orders_result.get("success") and orders_result.get("orders"):
                        # 为每个订单添加店铺信息
                        for order in orders_result.get("orders", []):
                            order["shop_id"] = shop_id
                            order["shop_title"] = shop.get("title", "")
                            all_orders.append(order)
                        logger.info(
                            f"✅ 店铺 {shop.get('title', shop_id)} 添加了 {len(orders_result.get('orders', []))} 个订单"
                        )
                    else:
                        logger.warning(
                            f"⚠️ 店铺 {shop.get('title', shop_id)} 获取订单失败或无订单: {orders_result.get('message', 'Unknown error')}"
                        )

                orders = all_orders

                if not orders:
                    logger.info(f"ℹ️ Printify 系统 {printify_system.name} 没有发货单")
                    continue

                # 转换发货单为SCM订单
                synced_count = 0
                for order in orders:
                    try:
                        # 检查是否已存在相同的Printify订单ID
                        existing_scm_order = await db.execute(
                            select(SCMOrder).where(
                                SCMOrder.tenant_id == tenant.id,
                                SCMOrder.target_system_id == str(order.get("id", "")),
                                SCMOrder.target_system_type == "PRINTIFY",
                            )
                        )
                        existing_order = existing_scm_order.scalar_one_or_none()

                        if existing_order:
                            # 更新现有订单
                            existing_order.status = order.get("status", "unknown")
                            existing_order.fulfillment_status = order.get(
                                "fulfillment_status", "unknown"
                            )
                            existing_order.tracking_number = order.get(
                                "tracking_number"
                            )
                            existing_order.tracking_url = order.get("tracking_url")
                            existing_order.updated_at = func.now()

                            logger.info(f"✅ 更新现有 SCM 订单: {existing_order.id}")
                        else:
                            # 创建新的SCM订单
                            scm_order = SCMOrder(
                                tenant_id=tenant.id,
                                source_order_id=None,  # Printify订单没有关联的本地订单
                                target_system_type="PRINTIFY",
                                target_system_id=str(order.get("id", "")),
                                routing_strategy="printify_direct",
                                line_items=order.get("line_items", []),
                                total_amount=float(order.get("total_price", 0)),
                                currency=order.get("currency", "USD"),
                                customer_email=order.get("customer_email", ""),
                                customer_name=order.get("customer_name", ""),
                                customer_phone=order.get("customer_phone"),
                                shipping_address=order.get("shipping_address", {}),
                                billing_address=order.get("billing_address", {}),
                                status=order.get("status", "unknown"),
                                fulfillment_status=order.get(
                                    "fulfillment_status", "unknown"
                                ),
                                tracking_number=order.get("tracking_number"),
                                tracking_url=order.get("tracking_url"),
                                routing_metadata={
                                    "printify_order_id": order.get("id"),
                                    "printify_order_number": order.get("order_number"),
                                    "printify_shop_id": order.get("shop_id"),
                                    "sync_source": "printify_api",
                                },
                            )

                            db.add(scm_order)
                            synced_count += 1

                            logger.info(
                                f"✅ 创建新 SCM 订单: Printify ID {order.get('id')}"
                            )

                    except Exception as order_error:
                        logger.error(f"❌ 处理 Printify 订单失败: {str(order_error)}")
                        errors.append(
                            f"订单 {order.get('id', 'unknown')}: {str(order_error)}"
                        )
                        total_errors += 1

                await db.commit()
                total_synced += synced_count

                logger.info(
                    f"✅ Printify 系统 {printify_system.name} 同步完成: {synced_count} 个订单"
                )

            except Exception as system_error:
                logger.error(
                    f"❌ 同步 Printify 系统 {printify_system.name} 失败: {str(system_error)}"
                )
                errors.append(f"系统 {printify_system.name}: {str(system_error)}")
                total_errors += 1

        result = {
            "success": total_errors == 0,
            "message": f"同步完成，共同步了 {total_synced} 个发货单",
            "synced_count": total_synced,
            "error_count": total_errors,
            "errors": errors[:10] if errors else [],  # 只返回前10个错误
        }

        logger.info(
            f"✅ Printify 发货单同步完成: {total_synced} 个订单, {total_errors} 个错误"
        )
        return result

    except Exception as e:
        logger.error(f"❌ Printify 发货单同步失败: {str(e)}")
        import traceback

        logger.error(f"   异常堆栈: {traceback.format_exc()}")

        return {
            "success": False,
            "message": f"同步失败: {str(e)}",
            "synced_count": 0,
            "error_count": 1,
            "errors": [str(e)],
        }
