"""
订单状态同步服务
用于同步SCM订单状态到Shopify和Printify
"""

from typing import Dict, Any, Optional, List
import asyncio
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.logging import get_logger
from app.models.order import Order
from app.models.scm_order import SCMOrder
from app.services.shopify.fulfillment_service import (
    create_shopify_fulfillment_service,
)
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

    async def batch_sync_printify_to_scm(
        self, tenant_id: int, limit: int = 100
    ) -> Dict[str, Any]:
        """
        批量同步Printify订单状态到SCM

        Args:
            tenant_id: 租户ID
            limit: 最大处理数量

        Returns:
            同步结果统计
        """
        try:
            logger.info(
                "🔍 开始批量同步Printify订单状态", tenant_id=tenant_id, limit=limit
            )

            # 获取需要同步的SCM订单
            result = await self.db.execute(
                select(SCMOrder)
                .where(
                    and_(
                        SCMOrder.tenant_id == tenant_id,
                        SCMOrder.target_system_type == "PRINTIFY",
                        SCMOrder.printify_order_id.isnot(None),
                        SCMOrder.status.in_(["created", "processing"]),
                    )
                )
                .limit(limit)
            )
            scm_orders = result.scalars().all()

            if not scm_orders:
                logger.info("ℹ️ 没有需要同步的Printify订单", tenant_id=tenant_id)
                return {
                    "success": True,
                    "message": "没有需要同步的订单",
                    "synced_count": 0,
                }

            # 获取Printify凭据
            printify_credentials = await self._get_printify_credentials(tenant_id)
            if not printify_credentials:
                logger.error("❌ 无法获取Printify凭据", tenant_id=tenant_id)
                return {
                    "success": False,
                    "message": "无法获取Printify凭据",
                    "synced_count": 0,
                }

            # 创建Printify服务
            printify_service = PrintifyService(self.db)

            # 批量获取Printify订单状态
            printify_order_ids = [order.printify_order_id for order in scm_orders]
            logger.info(f"📦 批量获取 {len(printify_order_ids)} 个Printify订单状态")

            # 使用批量API获取订单状态
            batch_orders_data = await printify_service.get_orders_batch(
                printify_credentials["shop_id"],
                printify_credentials["access_token"],
                printify_order_ids,
            )

            if not batch_orders_data.get("success"):
                logger.error(
                    "❌ 批量获取Printify订单状态失败",
                    error=batch_orders_data.get("message"),
                )
                return {
                    "success": False,
                    "message": "批量获取订单状态失败",
                    "synced_count": 0,
                }

            # 创建订单状态映射
            orders_status_map = {}
            for order_data in batch_orders_data.get("orders", []):
                order_id = str(order_data.get("id", ""))
                orders_status_map[order_id] = order_data

            success_count = 0
            error_count = 0
            errors = []

            # 批量更新SCM订单状态
            for scm_order in scm_orders:
                try:
                    order_data = orders_status_map.get(scm_order.printify_order_id)
                    if not order_data:
                        error_msg = (
                            f"SCM订单 {scm_order.id} 未找到对应的Printify订单数据"
                        )
                        errors.append(error_msg)
                        error_count += 1
                        continue

                    # 更新SCM订单状态
                    new_status = self._map_printify_status_to_scm(
                        order_data.get("status")
                    )
                    if new_status and new_status != scm_order.status:
                        scm_order.status = new_status
                        scm_order.updated_at = datetime.utcnow()

                        # 如果有跟踪信息，也更新
                        if order_data.get("tracking_number"):
                            scm_order.tracking_number = order_data.get(
                                "tracking_number"
                            )
                        if order_data.get("tracking_url"):
                            scm_order.tracking_url = order_data.get("tracking_url")

                        success_count += 1
                        logger.info(
                            f"✅ SCM订单 {scm_order.id} 状态更新: {scm_order.status} -> {new_status}"
                        )

                except Exception as e:
                    error_msg = f"SCM订单 {scm_order.id} 状态更新异常: {str(e)}"
                    errors.append(error_msg)
                    error_count += 1
                    logger.error(f"❌ {error_msg}")

            # 提交所有更改
            await self.db.commit()

            result = {
                "success": error_count == 0,
                "total_processed": len(scm_orders),
                "success_count": success_count,
                "error_count": error_count,
                "errors": errors,
            }

            logger.info(
                "✅ 批量同步Printify订单状态完成",
                tenant_id=tenant_id,
                success_count=success_count,
                error_count=error_count,
                total_processed=len(scm_orders),
            )

            return result

        except Exception as e:
            logger.error(
                "❌ 批量同步Printify订单状态失败", tenant_id=tenant_id, error=str(e)
            )
            return {
                "success": False,
                "message": f"批量同步失败: {str(e)}",
                "synced_count": 0,
            }

    def batch_sync_printify_to_scm_sync(
        self, tenant_id: int, limit: int = 100
    ) -> Dict[str, Any]:
        """
        批量同步Printify订单状态到SCM (同步版本)
        只使用 GET /shops/{shop_id}/orders.json API，不需要物流详细信息

        优化说明：
        - 只使用批量订单列表API，不需要单个订单详情API
        - 不更新物流公司(carrier)、发货时间(shipped_at)、送达时间(
          delivered_at)
        - 只更新基本状态和跟踪号信息，提升同步速度
        """
        try:
            logger.info(
                "🔍 开始批量同步Printify订单状态", tenant_id=tenant_id, limit=limit
            )

            # 获取需要同步的SCM订单
            from sqlalchemy import and_
            from app.models.scm_order import SCMOrder

            scm_orders = (
                self.db.query(SCMOrder)
                .filter(
                    and_(
                        SCMOrder.tenant_id == tenant_id,
                        SCMOrder.target_system_type == "PRINTIFY",
                        SCMOrder.printify_order_id.isnot(None),
                        SCMOrder.status.in_(["created", "processing"]),
                    )
                )
                .limit(limit)
                .all()
            )

            if not scm_orders:
                logger.info("ℹ️ 没有需要同步的Printify订单", tenant_id=tenant_id)
                return {
                    "success": True,
                    "message": "没有需要同步的订单",
                    "synced_count": 0,
                }

            # 获取Printify凭据
            printify_credentials = self._get_printify_credentials_sync(tenant_id)
            if not printify_credentials:
                logger.error("❌ 无法获取Printify凭据", tenant_id=tenant_id)
                return {
                    "success": False,
                    "message": "无法获取Printify凭据",
                    "synced_count": 0,
                }

            # 创建Printify服务
            from app.services.printify_service import PrintifyService

            printify_service = PrintifyService(self.db)

            # 批量获取Printify订单状态
            printify_order_ids = [order.printify_order_id for order in scm_orders]
            logger.info(f"📦 批量获取 {len(printify_order_ids)} 个Printify订单状态")

            # 使用批量API获取订单状态（只需要基本状态，不需要物流详细信息）
            import asyncio

            batch_orders_data = asyncio.run(
                printify_service.get_orders_batch(
                    printify_credentials["shop_id"],
                    printify_credentials["access_token"],
                    printify_order_ids,
                )
            )

            if not batch_orders_data.get("success"):
                logger.error(
                    "❌ 批量获取Printify订单状态失败",
                    error=batch_orders_data.get("message"),
                )
                return {
                    "success": False,
                    "message": "批量获取订单状态失败",
                    "synced_count": 0,
                }

            # 创建订单状态映射
            orders_status_map = {}
            for order_data in batch_orders_data.get("orders", []):
                order_id = str(order_data.get("id", ""))
                orders_status_map[order_id] = order_data

            success_count = 0
            error_count = 0
            errors = []

            # 批量更新SCM订单状态
            for scm_order in scm_orders:
                try:
                    order_data = orders_status_map.get(scm_order.printify_order_id)
                    if not order_data:
                        error_msg = (
                            f"SCM订单 {scm_order.id} 未找到对应的Printify订单数据"
                        )
                        errors.append(error_msg)
                        error_count += 1
                        continue

                    # 更新SCM订单状态
                    new_status = self._map_printify_status_to_scm(
                        order_data.get("status")
                    )
                    if new_status and new_status != scm_order.status:
                        scm_order.status = new_status
                        scm_order.updated_at = datetime.utcnow()

                        # 如果有跟踪信息，也更新
                        if order_data.get("tracking_number"):
                            scm_order.tracking_number = order_data.get(
                                "tracking_number"
                            )
                        if order_data.get("tracking_url"):
                            scm_order.tracking_url = order_data.get("tracking_url")

                        success_count += 1
                        logger.info(
                            f"✅ SCM订单 {scm_order.id} 状态更新: {scm_order.status} -> {new_status}"
                        )

                except Exception as e:
                    error_msg = f"SCM订单 {scm_order.id} 状态更新异常: {str(e)}"
                    errors.append(error_msg)
                    error_count += 1
                    logger.error(f"❌ {error_msg}")

            # 提交所有更改
            self.db.commit()

            result = {
                "success": error_count == 0,
                "total_processed": len(scm_orders),
                "success_count": success_count,
                "error_count": error_count,
                "errors": errors,
            }

            logger.info(
                "✅ 批量同步Printify订单状态完成",
                tenant_id=tenant_id,
                success_count=success_count,
                error_count=error_count,
                total_processed=len(scm_orders),
            )

            return result

        except Exception as e:
            logger.error(
                "❌ 批量同步Printify订单状态失败", tenant_id=tenant_id, error=str(e)
            )
            return {
                "success": False,
                "message": f"批量同步失败: {str(e)}",
                "synced_count": 0,
            }

    def _get_printify_credentials_sync(
        self, tenant_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        获取Printify凭据 (同步版本)
        """
        try:
            from app.services.external_system_service import ExternalSystemService
            from app.core.security import decrypt_data

            external_system_service = ExternalSystemService(self.db)
            printify_systems = (
                external_system_service.get_external_systems_by_type_sync(
                    tenant_id, "PRINTIFY", active_only=True
                )
            )

            if not printify_systems:
                logger.error("❌ 未找到Printify配置", tenant_id=tenant_id)
                return None

            printify_system = printify_systems[0]

            # 解密凭据
            credentials = printify_system.credentials
            if not credentials:
                logger.error("❌ Printify凭据为空", tenant_id=tenant_id)
                return None

            # 解密凭据
            try:
                decrypted_credentials = decrypt_data(credentials)
                logger.info("✅ Printify凭据解密成功", tenant_id=tenant_id)
                return decrypted_credentials
            except Exception as e:
                logger.error(
                    "❌ Printify凭据解密失败", tenant_id=tenant_id, error=str(e)
                )
                return None

        except Exception as e:
            logger.error("❌ 获取Printify凭据失败", tenant_id=tenant_id, error=str(e))
            return None

    def _map_printify_status_to_scm(self, printify_status: str) -> Optional[str]:
        """
        将Printify状态映射到SCM状态

        Args:
            printify_status: Printify订单状态

        Returns:
            SCM状态
        """
        status_mapping = {
            "pending": "processing",
            "in_production": "processing",
            "shipped": "fulfilled",
            "delivered": "fulfilled",
            "cancelled": "cancelled",
            "failed": "cancelled",
        }
        return status_mapping.get(printify_status.lower())

    async def sync_printify_to_scm(
        self, printify_order_id: str, tenant_id: int
    ) -> bool:
        """
        同步Printify订单状态到SCM (单个订单，保持向后兼容)

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

    def batch_sync_pending_orders_sync(
        self, tenant_id: int, limit: int = 100, ignore_flags: bool = False
    ) -> Dict[str, Any]:
        """
        批量同步待处理的订单 (同步版本)

        Args:
            tenant_id: 租户ID
            limit: 最大处理数量

        Returns:
            同步结果统计
        """
        try:
            logger.info("🔍 开始批量同步待处理订单", tenant_id=tenant_id, limit=limit)

            # 获取需要同步的SCM订单
            from app.core.database import get_sync_db

            db = next(get_sync_db())

            scm_orders = (
                db.query(SCMOrder)
                .filter(
                    and_(
                        SCMOrder.tenant_id == tenant_id,
                        SCMOrder.status.in_(["processing", "fulfilled"]),
                        SCMOrder.source_order_id.isnot(None),
                        SCMOrder.auto_synced_fulfillment_to_shopify == False,  # 只处理未自动同步的订单
                    )
                )
                .limit(limit)
                .all()
            )

            success_count = 0
            error_count = 0
            errors = []

            for scm_order in scm_orders:
                try:
                    # 使用同步方式调用 Shopify API
                    success = self.sync_scm_to_shopify_sync(scm_order.id)
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
                "✅ 批量同步待处理订单完成",
                tenant_id=tenant_id,
                result=result,
            )

            return result

        except Exception as e:
            logger.error("❌ 批量同步待处理订单失败", tenant_id=tenant_id, error=str(e))
            import traceback

            logger.error("   异常堆栈", stack=traceback.format_exc())
            return {
                "success": False,
                "total_processed": 0,
                "success_count": 0,
                "error_count": 1,
                "errors": [str(e)],
            }

    def sync_scm_to_shopify_sync(self, scm_order_id: int, ignore_flags: bool = False) -> bool:
        """
        同步SCM订单状态到Shopify (同步版本)

        Args:
            scm_order_id: SCM订单ID

        Returns:
            同步是否成功
        """
        try:
            logger.info("🔍 开始同步SCM订单到Shopify", scm_order_id=scm_order_id)

            # 获取SCM订单
            from app.core.database import get_sync_db

            db = next(get_sync_db())

            scm_order = db.query(SCMOrder).filter(SCMOrder.id == scm_order_id).first()

            if not scm_order:
                logger.error("❌ SCM订单不存在", scm_order_id=scm_order_id)
                return False

            # 获取Shopify订单ID
            shopify_order_id = None

            if scm_order.source_order_id:
                # 从源订单获取Shopify订单ID
                from app.models.order import Order

                source_order = (
                    db.query(Order)
                    .filter(Order.id == scm_order.source_order_id)
                    .first()
                )

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
            shopify_credentials = self._get_shopify_credentials_sync(
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
            if scm_order.status == "fulfilled":
                # 创建或更新履约记录（即使没有跟踪号也要创建履约记录）
                success = self._create_or_update_fulfillment_sync(
                    shopify_service, shopify_order_id, scm_order
                )
            elif scm_order.status == "cancelled":
                # 取消履约记录
                success = self._cancel_fulfillment_sync(
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
                # 标记为已自动同步发货信息到Shopify（手动处理时也标记，避免下次自动处理）
                if not ignore_flags:
                    scm_order.auto_synced_fulfillment_to_shopify = True

                db.commit()

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

    def _get_shopify_credentials_sync(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """获取Shopify凭据 (同步版本)"""
        try:
            from app.services.external_system_service import ExternalSystemService
            from app.core.database import get_sync_db

            db = next(get_sync_db())
            service = ExternalSystemService(db)
            shopify_systems = service.get_external_systems_by_type_sync(
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

    def _create_or_update_fulfillment_sync(
        self, shopify_service, shopify_order_id: str, scm_order: SCMOrder
    ) -> bool:
        """创建或更新Shopify履约记录 (同步版本)"""
        import asyncio

        try:
            # 构建跟踪信息
            tracking_info = {
                "number": scm_order.tracking_number,
                "url": scm_order.tracking_url or "",
                "company": "Printify",
            }

            if scm_order.shopify_fulfillment_id:
                # 更新现有履约记录
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        shopify_service.update_fulfillment_tracking(
                            scm_order.shopify_fulfillment_id, tracking_info
                        )
                    )
                    return result is not None
                finally:
                    loop.close()
            else:
                # 创建新履约记录 - 需要先获取履约订单ID
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    # 先获取履约订单
                    fulfillment_orders = loop.run_until_complete(
                        shopify_service.get_fulfillment_orders(shopify_order_id)
                    )

                    if not fulfillment_orders:
                        logger.error(
                            "❌ 未找到履约订单", shopify_order_id=shopify_order_id
                        )
                        return False

                    # 智能匹配履约订单 - 根据 SCM 订单的商品信息匹配
                    fulfillment_order = self._find_matching_fulfillment_order(
                        fulfillment_orders, scm_order
                    )

                    if not fulfillment_order:
                        logger.error(
                            "❌ 未找到匹配的履约订单",
                            scm_order_id=scm_order.id,
                            fulfillment_orders_count=len(fulfillment_orders),
                        )
                        return False

                    fulfillment_order_id = fulfillment_order["id"]

                    try:
                        result = loop.run_until_complete(
                            shopify_service.create_fulfillment(
                                fulfillment_order_id,
                                tracking_info,
                                notify_customer=True,
                                fulfillment_order=fulfillment_order,
                            )
                        )
                        if result:
                            # 保存履约ID
                            from app.core.database import get_sync_db

                            db = next(get_sync_db())
                            scm_order.shopify_fulfillment_id = result["id"]
                            db.commit()
                            return True
                        return False
                    except Exception as create_error:
                        # 如果创建履约记录失败，可能是已经存在履约记录
                        logger.warning(
                            "⚠️ 创建履约记录失败，尝试获取现有履约记录",
                            error=str(create_error),
                            scm_order_id=scm_order.id,
                        )

                        # 尝试获取现有的履约记录
                        try:
                            # 先获取履约订单，然后尝试获取履约记录
                            fulfillment_orders = loop.run_until_complete(
                                shopify_service.get_fulfillment_orders(shopify_order_id)
                            )

                            if fulfillment_orders:
                                # 检查履约订单是否已经有履约记录
                                fulfillment_order = fulfillment_orders[0]
                                fulfillment_order_id = fulfillment_order["id"]

                                # 尝试从履约订单获取履约记录
                                # 这里我们需要通过其他方式获取履约记录
                                # 由于Shopify API的限制，我们暂时跳过这个逻辑
                                logger.warning(
                                    "⚠️ 无法获取现有履约记录，跳过更新",
                                    scm_order_id=scm_order.id,
                                    shopify_order_id=shopify_order_id,
                                )
                                return False

                        except Exception as get_error:
                            logger.error(
                                "❌ 获取现有履约记录也失败",
                                error=str(get_error),
                                scm_order_id=scm_order.id,
                            )

                        # 如果都失败了，记录错误但继续
                        logger.error(
                            "❌ 无法创建或更新履约记录",
                            create_error=str(create_error),
                            scm_order_id=scm_order.id,
                        )
                        return False
                finally:
                    loop.close()

        except Exception as e:
            logger.error(
                "❌ 创建或更新履约记录失败",
                shopify_order_id=shopify_order_id,
                scm_order_id=scm_order.id,
                error=str(e),
            )
            return False

    def _cancel_fulfillment_sync(
        self, shopify_service, shopify_order_id: str, scm_order: SCMOrder
    ) -> bool:
        """取消Shopify履约记录 (同步版本)"""
        try:
            if not scm_order.shopify_fulfillment_id:
                logger.warning("⚠️ SCM订单没有履约记录ID", scm_order_id=scm_order.id)
                return True

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    shopify_service.cancel_fulfillment(scm_order.shopify_fulfillment_id)
                )
                return result is not None
            finally:
                loop.close()

        except Exception as e:
            logger.error(
                "❌ 取消履约记录失败",
                shopify_order_id=shopify_order_id,
                scm_order_id=scm_order.id,
                error=str(e),
            )
            return False

    def _find_matching_fulfillment_order(
        self, fulfillment_orders: List[Dict[str, Any]], scm_order: SCMOrder
    ) -> Optional[Dict[str, Any]]:
        """
        智能匹配履约订单
        根据 SCM 订单的商品信息匹配最合适的履约订单
        """
        if not fulfillment_orders:
            return None

        # 如果只有一个履约订单，直接返回
        if len(fulfillment_orders) == 1:
            return fulfillment_orders[0]

        # 获取 SCM 订单的商品信息
        scm_line_items = scm_order.line_items or []
        if not scm_line_items:
            logger.warning(
                "⚠️ SCM订单没有行项目信息，使用第一个履约订单",
                scm_order_id=scm_order.id,
            )
            return fulfillment_orders[0]

        # 提取 SCM 订单的关键商品信息
        scm_skus = set()
        scm_variant_ids = set()
        scm_titles = set()

        for item in scm_line_items:
            if isinstance(item, dict):
                # 提取 SKU
                if "metadata" in item and "sku" in item["metadata"]:
                    scm_skus.add(item["metadata"]["sku"])

                # 提取变体ID
                if "variant_id" in item:
                    scm_variant_ids.add(str(item["variant_id"]))

                # 提取商品标题
                if "metadata" in item and "title" in item["metadata"]:
                    scm_titles.add(item["metadata"]["title"])

        logger.info(
            "🔍 开始智能匹配履约订单",
            scm_order_id=scm_order.id,
            scm_skus=list(scm_skus),
            scm_variant_ids=list(scm_variant_ids),
            scm_titles=list(scm_titles),
            fulfillment_orders_count=len(fulfillment_orders),
        )

        # 为每个履约订单计算匹配分数
        best_match = None
        best_score = 0

        for fulfillment_order in fulfillment_orders:
            score = 0
            fulfillment_order_id = fulfillment_order.get("id", "")

            # 获取履约订单的行项目
            line_items = fulfillment_order.get("lineItems", {}).get("edges", [])

            for edge in line_items:
                line_item = edge.get("node", {})

                # 检查 SKU 匹配
                sku = line_item.get("sku", "")
                if sku in scm_skus:
                    score += 10
                    logger.debug(
                        "✅ SKU匹配",
                        fulfillment_order_id=fulfillment_order_id,
                        sku=sku,
                    )

                # 检查变体ID匹配
                variant_id = line_item.get("variant", {}).get("id", "")
                if variant_id and any(vid in variant_id for vid in scm_variant_ids):
                    score += 8
                    logger.debug(
                        "✅ 变体ID匹配",
                        fulfillment_order_id=fulfillment_order_id,
                        variant_id=variant_id,
                    )

                # 检查商品标题匹配
                title = line_item.get("title", "")
                if title and any(t in title for t in scm_titles):
                    score += 5
                    logger.debug(
                        "✅ 商品标题匹配",
                        fulfillment_order_id=fulfillment_order_id,
                        title=title,
                    )

                # 检查数量匹配
                quantity = line_item.get("quantity", 0)
                scm_quantity = sum(item.get("quantity", 0) for item in scm_line_items)
                if quantity == scm_quantity:
                    score += 3
                    logger.debug(
                        "✅ 数量匹配",
                        fulfillment_order_id=fulfillment_order_id,
                        quantity=quantity,
                        scm_quantity=scm_quantity,
                    )

            logger.debug(
                "📊 履约订单匹配分数",
                fulfillment_order_id=fulfillment_order_id,
                score=score,
            )

            if score > best_score:
                best_score = score
                best_match = fulfillment_order

        if best_match:
            logger.info(
                "✅ 找到最佳匹配的履约订单",
                scm_order_id=scm_order.id,
                fulfillment_order_id=best_match.get("id"),
                match_score=best_score,
            )
        else:
            logger.warning(
                "⚠️ 未找到匹配的履约订单，使用第一个",
                scm_order_id=scm_order.id,
            )
            best_match = fulfillment_orders[0]

        return best_match
