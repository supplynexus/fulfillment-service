"""
Shopify Fulfillment API 服务
用于管理Shopify订单的履约状态
"""

import asyncio
import aiohttp
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from app.core.config import settings
from app.core.logging import get_logger
from app.utils.retry_client import (
    RetryableHTTPClient,
    create_shopify_retry_config,
    retry_async,
)

logger = get_logger(__name__)


class ShopifyFulfillmentService:
    """Shopify Fulfillment API 服务"""

    def __init__(self, shop_name: str, access_token: str):
        self.shop_name = shop_name
        self.access_token = access_token
        self.base_url = (
            f"https://{shop_name}.myshopify.com/admin/api/2024-10/graphql.json"
        )
        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": access_token,
        }
        # 创建针对Shopify优化的重试配置
        self.retry_config = create_shopify_retry_config()

    @retry_async(max_retries=5, base_delay=2.0, max_delay=60.0)
    async def _make_request(self, query: str, variables: Dict = None) -> Dict[str, Any]:
        """发送 GraphQL 请求（带重试机制）"""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        logger.info(
            "📡 发送Shopify GraphQL请求",
            query_type="fulfillment",
            shop_name=self.shop_name,
        )

        # 使用可重试的HTTP客户端
        async with RetryableHTTPClient(self.retry_config) as client:
            response = await client.post(
                self.base_url,
                headers=self.headers,
                json_data=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            )

            if response.status == 200:
                data = await response.json()
                if "errors" in data:
                    logger.error("❌ Shopify GraphQL错误", errors=data["errors"])
                    raise Exception(f"GraphQL errors: {data['errors']}")
                return data.get("data", {})
            else:
                error_text = await response.text()
                logger.error(
                    "❌ Shopify API请求失败", status=response.status, error=error_text
                )
                raise Exception(f"HTTP {response.status}: {error_text}")

    async def get_fulfillment_orders(self, order_id: str) -> List[Dict[str, Any]]:
        """
        获取订单的履约订单列表

        Args:
            order_id: Shopify订单ID (gid://shopify/Order/xxx)

        Returns:
            履约订单列表
        """
        query = """
        query getFulfillmentOrders($orderId: ID!) {
            order(id: $orderId) {
                id
                name
                fulfillmentOrders(first: 10) {
                    edges {
                        node {
                            id
                            status
                            requestStatus
                            createdAt
                            updatedAt
                            lineItems(first: 50) {
                                edges {
                                    node {
                                        id
                                        sku
                                        totalQuantity
                                        remainingQuantity
                                        lineItem {
                                            id
                                            title
                                            variantTitle
                                        }
                                    }
                                }
                            }
                            assignedLocation {
                                location {
                                    id
                                    name
                                    address {
                                        address1
                                        city
                                        province
                                        country
                                        zip
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """

        variables = {"orderId": order_id}

        try:
            result = await self._make_request(query, variables)
            order_data = result.get("order", {})
            fulfillment_orders = order_data.get("fulfillmentOrders", {}).get(
                "edges", []
            )

            fulfillment_list = []
            for edge in fulfillment_orders:
                fulfillment_order = edge.get("node", {})
                fulfillment_list.append(fulfillment_order)

            logger.info(
                "✅ 获取履约订单成功",
                order_id=order_id,
                fulfillment_count=len(fulfillment_list),
            )

            return fulfillment_list

        except Exception as e:
            logger.error("❌ 获取履约订单失败", order_id=order_id, error=str(e))
            raise

    async def create_fulfillment(
        self,
        fulfillment_order_id: str,
        tracking_info: Optional[Dict[str, Any]] = None,
        notify_customer: bool = True,
        fulfillment_order: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        创建履约记录

        Args:
            fulfillment_order_id: 履约订单ID
            tracking_info: 物流跟踪信息
            notify_customer: 是否通知客户

        Returns:
            创建的履约记录信息
        """
        # 构建履约数据
        fulfillment_data = {
            "notifyCustomer": notify_customer,
            "locationId": None,  # 使用默认位置
            "trackingInfo": tracking_info or {},
        }

        query = """
        mutation fulfillmentCreate($fulfillment: FulfillmentInput!) {
            fulfillmentCreate(fulfillment: $fulfillment) {
                fulfillment {
                    id
                    status
                    trackingInfo {
                        number
                        url
                        company
                    }
                    createdAt
                    updatedAt
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """

        # 使用预先传递的履约订单信息，如果没有则获取
        if fulfillment_order:
            target_fulfillment_order = fulfillment_order
        else:
            # 从履约订单ID中提取订单ID
            order_id = fulfillment_order_id.replace("FulfillmentOrder", "Order")
            fulfillment_orders = await self.get_fulfillment_orders(order_id)

            if not fulfillment_orders:
                raise Exception("未找到履约订单")

            # 找到匹配的履约订单
            target_fulfillment_order = None
            for fo in fulfillment_orders:
                if fo.get("id") == fulfillment_order_id:
                    target_fulfillment_order = fo
                    break

            if not target_fulfillment_order:
                raise Exception(f"未找到匹配的履约订单: {fulfillment_order_id}")

        # 获取履约订单的行项目
        line_items = target_fulfillment_order.get("lineItems", {}).get("edges", [])

        if not line_items:
            raise Exception("履约订单没有行项目")

        # 构建行项目数据
        fulfillment_order_line_items = []
        for edge in line_items:
            line_item = edge.get("node", {})
            fulfillment_order_line_items.append(
                {
                    "id": line_item.get("id"),
                    "quantity": line_item.get("totalQuantity", 1),
                }
            )

        variables = {
            "fulfillment": {
                "lineItemsByFulfillmentOrder": [
                    {
                        "fulfillmentOrderId": fulfillment_order_id,
                        "fulfillmentOrderLineItems": fulfillment_order_line_items,
                    }
                ],
                "notifyCustomer": notify_customer,
                "trackingInfo": tracking_info or {},
            }
        }

        try:
            result = await self._make_request(query, variables)
            fulfillment_create = result.get("fulfillmentCreate", {})

            if fulfillment_create.get("userErrors"):
                errors = fulfillment_create["userErrors"]
                logger.error("❌ 创建履约记录失败", errors=errors)
                raise Exception(f"Fulfillment creation errors: {errors}")

            fulfillment = fulfillment_create.get("fulfillment", {})
            logger.info(
                "✅ 创建履约记录成功",
                fulfillment_id=fulfillment.get("id"),
                status=fulfillment.get("status"),
            )

            return fulfillment

        except Exception as e:
            logger.error(
                "❌ 创建履约记录失败",
                fulfillment_order_id=fulfillment_order_id,
                error=str(e),
            )
            raise

    async def update_fulfillment_tracking(
        self, fulfillment_id: str, tracking_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        更新履约记录的物流跟踪信息

        Args:
            fulfillment_id: 履约记录ID
            tracking_info: 物流跟踪信息

        Returns:
            更新后的履约记录信息
        """
        query = """
        mutation fulfillmentTrackingInfoUpdate($fulfillmentId: ID!, $trackingInfoInput: FulfillmentTrackingInput!) {
            fulfillmentTrackingInfoUpdate(fulfillmentId: $fulfillmentId, trackingInfoInput: $trackingInfoInput) {
                fulfillment {
                    id
                    status
                    trackingInfo {
                        number
                        url
                        company
                    }
                    updatedAt
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """

        variables = {
            "fulfillmentId": fulfillment_id,
            "trackingInfoInput": tracking_info,
        }

        try:
            result = await self._make_request(query, variables)
            tracking_update = result.get("fulfillmentTrackingInfoUpdate", {})

            if tracking_update.get("userErrors"):
                errors = tracking_update["userErrors"]
                logger.error("❌ 更新物流跟踪信息失败", errors=errors)
                raise Exception(f"Tracking update errors: {errors}")

            fulfillment = tracking_update.get("fulfillment", {})
            logger.info(
                "✅ 更新物流跟踪信息成功",
                fulfillment_id=fulfillment.get("id"),
                tracking_number=tracking_info.get("number"),
            )

            return fulfillment

        except Exception as e:
            logger.error(
                "❌ 更新物流跟踪信息失败", fulfillment_id=fulfillment_id, error=str(e)
            )
            raise

    async def get_fulfillment(self, fulfillment_id: str) -> Dict[str, Any]:
        """
        获取履约记录详情

        Args:
            fulfillment_id: 履约记录ID

        Returns:
            履约记录详情
        """
        query = """
        query getFulfillment($id: ID!) {
            fulfillment(id: $id) {
                id
                status
                createdAt
                updatedAt
                trackingInfo {
                    number
                    url
                    company
                }
                fulfillmentLineItems(first: 50) {
                    edges {
                        node {
                            id
                            quantity
                            lineItem {
                                id
                                title
                                sku
                            }
                        }
                    }
                }
            }
        }
        """

        variables = {"id": fulfillment_id}

        try:
            result = await self._make_request(query, variables)
            fulfillment = result.get("fulfillment", {})

            logger.info(
                "✅ 获取履约记录成功",
                fulfillment_id=fulfillment.get("id"),
                status=fulfillment.get("status"),
            )

            return fulfillment

        except Exception as e:
            logger.error(
                "❌ 获取履约记录失败", fulfillment_id=fulfillment_id, error=str(e)
            )
            raise

    async def cancel_fulfillment(self, fulfillment_id: str) -> Dict[str, Any]:
        """
        取消履约记录

        Args:
            fulfillment_id: 履约记录ID

        Returns:
            取消结果
        """
        query = """
        mutation fulfillmentCancel($id: ID!) {
            fulfillmentCancel(id: $id) {
                fulfillment {
                    id
                    status
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """

        variables = {"id": fulfillment_id}

        try:
            result = await self._make_request(query, variables)
            cancel_result = result.get("fulfillmentCancel", {})

            if cancel_result.get("userErrors"):
                errors = cancel_result["userErrors"]
                logger.error("❌ 取消履约记录失败", errors=errors)
                raise Exception(f"Fulfillment cancellation errors: {errors}")

            fulfillment = cancel_result.get("fulfillment", {})
            logger.info(
                "✅ 取消履约记录成功",
                fulfillment_id=fulfillment.get("id"),
                status=fulfillment.get("status"),
            )

            return fulfillment

        except Exception as e:
            logger.error(
                "❌ 取消履约记录失败", fulfillment_id=fulfillment_id, error=str(e)
            )
            raise


# 工厂函数
def create_shopify_fulfillment_service(
    shop_name: str, access_token: str
) -> ShopifyFulfillmentService:
    """创建 Shopify Fulfillment 服务实例

    Args:
        shop_name: Shopify 商店名称
        access_token: Shopify 访问令牌

    Returns:
        ShopifyFulfillmentService 实例

    Raises:
        ValueError: 如果缺少必需的参数
    """
    if not shop_name or not access_token:
        raise ValueError("shop_name 和 access_token 都是必需的参数")

    return ShopifyFulfillmentService(shop_name, access_token)
