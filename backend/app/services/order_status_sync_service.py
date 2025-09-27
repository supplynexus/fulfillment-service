"""
订单状态同步服务
用于同步SCM订单状态到Shopify和Printify
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.logging import get_logger
from app.models.order import Order
from app.models.scm_order import SCMOrder
from app.services.shopify.fulfillment_service import create_shopify_fulfillment_service
from app.services.printify_service import PrintifyService
from app.core.security import decrypt_data

logger = get_logger(__name__)


class OrderStatusSyncService:
    """订单状态同步服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def sync_scm_to_shopify(self, scm_order_id: int) -> bool:
        """
        同步SCM订单状态到Shopify

        Args:
            scm_order_id: SCM订单ID

        Returns:
            同步是否成功
        """
        try:
            logger.info("🔍 开始同步SCM订单到Shopify", scm_order_id=scm_order_id)

            # 获取SCM订单
            result = await self.db.execute(
                select(SCMOrder).where(SCMOrder.id == scm_order_id)
            )
            scm_order = result.scalar_one_or_none()

            if not scm_order:
                logger.error("❌ SCM订单不存在", scm_order_id=scm_order_id)
                return False

            # 获取Shopify订单ID
            shopify_order_id = None

            if scm_order.source_order_id:
                # 从源订单获取Shopify订单ID
                result = await self.db.execute(
                    select(Order).where(Order.id == scm_order.source_order_id)
                )
                source_order = result.scalar_one_or_none()

                if not source_order:
                    logger.error(
                        "❌ 源订单不存在", source_order_id=scm_order.source_order_id
                    )
                    return False

                shopify_order_id = source_order.shopify_order_id
            elif scm_order.shopify_order_id:
                # 直接从SCM订单获取Shopify订单ID
                shopify_order_id = scm_order.shopify_order_id
            else:
                logger.error(
                    "❌ SCM订单没有关联的Shopify订单ID", scm_order_id=scm_order_id
                )
                return False

            if not shopify_order_id:
                logger.warning("⚠️ 没有找到Shopify订单ID", scm_order_id=scm_order_id)
                return False

            # 获取Shopify凭据
            shopify_credentials = await self._get_shopify_credentials(
                scm_order.tenant_id
            )
            if not shopify_credentials:
                logger.error("❌ 无法获取Shopify凭据", tenant_id=scm_order.tenant_id)
                return False

            # 创建Shopify Fulfillment服务
            shopify_service = create_shopify_fulfillment_service(
                shopify_credentials["shop_name"], shopify_credentials["access_token"]
            )

            # 根据SCM订单状态决定操作
            if scm_order.status == "fulfilled" and scm_order.tracking_number:
                # 创建或更新履约记录
                success = await self._create_or_update_fulfillment(
                    shopify_service, shopify_order_id, scm_order
                )
            elif scm_order.status == "cancelled":
                # 取消履约记录
                success = await self._cancel_fulfillment(
                    shopify_service, shopify_order_id, scm_order
                )
            else:
                logger.info(
                    "ℹ️ SCM订单状态无需同步到Shopify",
                    scm_order_id=scm_order_id,
                    status=scm_order.status,
                )
                success = True

            if success:
                # 更新SCM订单的履约状态
                scm_order.fulfillment_status = scm_order.status
                scm_order.updated_at = datetime.utcnow()

                await self.db.commit()

                logger.info(
                    "✅ SCM订单状态同步到Shopify成功",
                    scm_order_id=scm_order_id,
                    shopify_order_id=shopify_order_id,
                )

            return success

        except Exception as e:
            logger.error(
                "❌ 同步SCM订单到Shopify失败", scm_order_id=scm_order_id, error=str(e)
            )
            import traceback

            logger.error("   异常堆栈", stack=traceback.format_exc())
            return False

    async def sync_printify_to_scm(
        self, printify_order_id: str, tenant_id: int
    ) -> bool:
        """
        同步Printify订单状态到SCM

        Args:
            printify_order_id: Printify订单ID
            tenant_id: 租户ID

        Returns:
            同步是否成功
        """
        try:
            logger.info(
                "🔍 开始同步Printify订单到SCM",
                printify_order_id=printify_order_id,
                tenant_id=tenant_id,
            )

            # 查找对应的SCM订单
            result = await self.db.execute(
                select(SCMOrder).where(
                    and_(
                        SCMOrder.printify_order_id == printify_order_id,
                        SCMOrder.tenant_id == tenant_id,
                    )
                )
            )
            scm_order = result.scalar_one_or_none()

            if not scm_order:
                logger.error(
                    "❌ 未找到对应的SCM订单",
                    printify_order_id=printify_order_id,
                    tenant_id=tenant_id,
                )
                return False

            # 获取Printify凭据
            printify_credentials = await self._get_printify_credentials(tenant_id)
            if not printify_credentials:
                logger.error("❌ 无法获取Printify凭据", tenant_id=tenant_id)
                return False

            # 创建Printify服务
            printify_service = PrintifyService(self.db)

            # 获取Printify订单状态
            order_status = await printify_service.get_order_status(
                printify_credentials["shop_id"],
                printify_order_id,
                printify_credentials["access_token"],
            )

            if not order_status:
                logger.error(
                    "❌ 无法获取Printify订单状态", printify_order_id=printify_order_id
                )
                return False

            # 更新SCM订单状态
            old_status = scm_order.status
            scm_order.status = order_status.get("status", scm_order.status)
            scm_order.fulfillment_status = order_status.get(
                "fulfillment_status", scm_order.fulfillment_status
            )
            scm_order.tracking_number = order_status.get(
                "tracking_number", scm_order.tracking_number
            )
            scm_order.tracking_url = order_status.get(
                "tracking_url", scm_order.tracking_url
            )
            scm_order.updated_at = datetime.utcnow()

            if scm_order.status == "fulfilled":
                scm_order.fulfilled_at = datetime.utcnow()

            await self.db.commit()

            logger.info(
                "✅ Printify订单状态同步到SCM成功",
                scm_order_id=scm_order.id,
                printify_order_id=printify_order_id,
                old_status=old_status,
                new_status=scm_order.status,
            )

            # 如果状态变更，触发Shopify同步
            if old_status != scm_order.status:
                await self.sync_scm_to_shopify(scm_order.id)

            return True

        except Exception as e:
            logger.error(
                "❌ 同步Printify订单到SCM失败",
                printify_order_id=printify_order_id,
                tenant_id=tenant_id,
                error=str(e),
            )
            import traceback

            logger.error("   异常堆栈", stack=traceback.format_exc())
            return False

    async def _create_or_update_fulfillment(
        self, shopify_service, shopify_order_id: str, scm_order: SCMOrder
    ) -> bool:
        """创建或更新Shopify履约记录"""
        try:
            # 获取履约订单
            fulfillment_orders = await shopify_service.get_fulfillment_orders(
                shopify_order_id
            )

            if not fulfillment_orders:
                logger.error("❌ 未找到履约订单", shopify_order_id=shopify_order_id)
                return False

            # 使用第一个履约订单
            fulfillment_order = fulfillment_orders[0]
            fulfillment_order_id = fulfillment_order["id"]

            # 构建跟踪信息
            tracking_info = {
                "number": scm_order.tracking_number,
                "url": scm_order.tracking_url or "",
                "company": "Printify",  # 默认使用Printify作为物流公司
            }

            if scm_order.shopify_fulfillment_id:
                # 更新现有履约记录
                await shopify_service.update_fulfillment_tracking(
                    scm_order.shopify_fulfillment_id, tracking_info
                )
                logger.info(
                    "✅ 更新Shopify履约记录成功",
                    fulfillment_id=scm_order.shopify_fulfillment_id,
                )
            else:
                # 创建新履约记录 - 预先获取履约订单的行项目信息
                fulfillment = await shopify_service.create_fulfillment(
                    fulfillment_order_id,
                    tracking_info,
                    notify_customer=True,
                    fulfillment_order=fulfillment_order,
                )

                # 保存履约ID到SCM订单
                scm_order.shopify_fulfillment_id = fulfillment["id"]
                scm_order.shopify_fulfillment_order_id = fulfillment_order_id

                logger.info(
                    "✅ 创建Shopify履约记录成功", fulfillment_id=fulfillment["id"]
                )

            return True

        except Exception as e:
            logger.error("❌ 创建或更新Shopify履约记录失败", error=str(e))
            return False

    async def _cancel_fulfillment(
        self, shopify_service, source_order: Order, scm_order: SCMOrder
    ) -> bool:
        """取消Shopify履约记录"""
        try:
            if not source_order.shopify_fulfillment_id:
                logger.warning(
                    "⚠️ 没有履约记录需要取消",
                    shopify_order_id=source_order.shopify_order_id,
                )
                return True

            await shopify_service.cancel_fulfillment(
                source_order.shopify_fulfillment_id
            )

            logger.info(
                "✅ 取消Shopify履约记录成功",
                fulfillment_id=source_order.shopify_fulfillment_id,
            )

            return True

        except Exception as e:
            logger.error("❌ 取消Shopify履约记录失败", error=str(e))
            return False

    async def _get_shopify_credentials(
        self, tenant_id: int
    ) -> Optional[Dict[str, Any]]:
        """获取Shopify凭据"""
        try:
            from app.services.external_system_service import ExternalSystemService

            service = ExternalSystemService(self.db)
            shopify_systems = await service.get_external_systems_by_type(
                tenant_id, "SHOPIFY"
            )

            if not shopify_systems:
                return None

            # 使用第一个Shopify系统
            shopify_system = shopify_systems[0]
            credentials = shopify_system.credentials or {}

            # 解密凭据
            access_token = decrypt_data(credentials.get("access_token", ""))
            store_url = decrypt_data(credentials.get("store_url", ""))

            # 从store_url提取shop_name
            if store_url.startswith("https://"):
                shop_name = store_url.replace("https://", "").replace(
                    ".myshopify.com", ""
                )
            else:
                shop_name = store_url.replace(".myshopify.com", "")

            return {"shop_name": shop_name, "access_token": access_token}

        except Exception as e:
            logger.error("❌ 获取Shopify凭据失败", tenant_id=tenant_id, error=str(e))
            return None

    async def _get_printify_credentials(
        self, tenant_id: int
    ) -> Optional[Dict[str, Any]]:
        """获取Printify凭据"""
        try:
            from app.services.external_system_service import ExternalSystemService

            service = ExternalSystemService(self.db)
            printify_systems = await service.get_external_systems_by_type(
                tenant_id, "PRINTIFY"
            )

            if not printify_systems:
                return None

            # 使用第一个Printify系统
            printify_system = printify_systems[0]
            credentials = printify_system.get("credentials", {})

            # 解密凭据
            access_token = decrypt_data(credentials.get("access_token", ""))
            shop_id = credentials.get("shop_id", "")

            return {"shop_id": shop_id, "access_token": access_token}

        except Exception as e:
            logger.error("❌ 获取Printify凭据失败", tenant_id=tenant_id, error=str(e))
            return None

    async def batch_sync_pending_orders(
        self, tenant_id: int, limit: int = 100
    ) -> Dict[str, Any]:
        """
        批量同步待处理的订单

        Args:
            tenant_id: 租户ID
            limit: 最大处理数量

        Returns:
            同步结果统计
        """
        try:
            logger.info("🔍 开始批量同步待处理订单", tenant_id=tenant_id, limit=limit)

            # 获取需要同步的SCM订单
            result = await self.db.execute(
                select(SCMOrder)
                .where(
                    and_(
                        SCMOrder.tenant_id == tenant_id,
                        SCMOrder.status.in_(["processing", "fulfilled"]),
                        SCMOrder.source_order_id.isnot(None),
                    )
                )
                .limit(limit)
            )
            scm_orders = result.scalars().all()

            success_count = 0
            error_count = 0
            errors = []

            for scm_order in scm_orders:
                try:
                    success = await self.sync_scm_to_shopify(scm_order.id)
                    if success:
                        success_count += 1
                    else:
                        error_count += 1
                        errors.append(f"SCM订单 {scm_order.id} 同步失败")
                except Exception as e:
                    error_count += 1
                    errors.append(f"SCM订单 {scm_order.id} 同步异常: {str(e)}")

            result = {
                "success": error_count == 0,
                "total_processed": len(scm_orders),
                "success_count": success_count,
                "error_count": error_count,
                "errors": errors,
            }

            logger.info(
                "✅ 批量同步完成",
                tenant_id=tenant_id,
                total_processed=len(scm_orders),
                success_count=success_count,
                error_count=error_count,
            )

            return result

        except Exception as e:
            logger.error("❌ 批量同步失败", tenant_id=tenant_id, error=str(e))
            return {
                "success": False,
                "total_processed": 0,
                "success_count": 0,
                "error_count": 1,
                "errors": [str(e)],
            }
