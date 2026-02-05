"""
Shopify Fulfillment Service
处理 SCM 订单到 Shopify 的 fulfillment 更新
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import aiohttp
from app.core.logging import get_logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = get_logger(__name__)


class ShopifyFulfillmentService:
    """Shopify Fulfillment 服务"""
    
    def __init__(self):
        self.timeout = 30
        
    async def _get_shopify_external_system_id(self, scm_order, db: AsyncSession) -> Optional[int]:
        """从 SCM 订单的源订单获取 Shopify 外部系统 ID，确保使用与订单页面相同的店铺"""
        try:
            from app.models.order import Order
            from app.models.scm_order import ScmOrderSource

            # 从 ScmOrderSource 获取源订单 ID
            source_result = await db.execute(
                select(ScmOrderSource.source_order_id).where(
                    ScmOrderSource.scm_order_id == scm_order.id,
                    ScmOrderSource.tenant_id == scm_order.tenant_id
                )
            )
            rows = source_result.fetchall()
            if not rows:
                return None
            source_order_id = rows[0][0]

            # 从 Order 获取 external_system_id
            order_result = await db.execute(
                select(Order.external_system_id).where(
                    Order.id == source_order_id,
                    Order.tenant_id == scm_order.tenant_id
                )
            )
            row = order_result.fetchone()
            return row[0] if row and row[0] else None
        except Exception as e:
            logger.warning(f"⚠️ 无法获取 SCM 订单的 external_system_id: {e}")
            return None

    async def _get_shopify_credentials(
        self, tenant, db: AsyncSession, external_system_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取租户的 Shopify 凭据。
        与 Shopify 订单页面使用相同的 ExternalSystemService.get_decrypted_credentials，
        确保 access_token 等凭据完全一致。
        """
        try:
            from app.models.external_system import ExternalSystem, ExternalSystemType
            from app.services.external_system_service import ExternalSystemService

            # 确定要使用的 external_system
            if external_system_id:
                # 使用 SCM 订单对应的具体店铺
                service = ExternalSystemService(db)
                shopify_system = await service.get_external_system(external_system_id, tenant.id)
            else:
                # 回退：取租户下第一个活跃的 Shopify 店铺
                result = await db.execute(
                    select(ExternalSystem).where(
                        ExternalSystem.tenant_id == tenant.id,
                        ExternalSystem.system_type == ExternalSystemType.SHOPIFY,
                        ExternalSystem.is_active == True
                    )
                )
                shopify_system = result.scalar_one_or_none()

            if not shopify_system:
                logger.error(f"❌ 未找到 Shopify 外部系统: tenant_id={tenant.id}")
                return None

            # 使用与订单页面相同的凭据获取逻辑
            service = ExternalSystemService(db)
            decrypted_credentials = await service.get_decrypted_credentials(
                shopify_system.id, tenant.id
            )
            if not decrypted_credentials:
                logger.error(f"❌ 无法获取解密后的凭据: external_system_id={shopify_system.id}")
                return None

            access_token = decrypted_credentials.get("access_token") or decrypted_credentials.get("api_key")
            if not access_token:
                logger.error(f"❌ 凭据中缺少 access_token: external_system_id={shopify_system.id}")
                return None

            # 构建 shop_domain：优先 base_url，其次 store_url
            store_url = decrypted_credentials.get("store_url") or shopify_system.base_url or ""
            if store_url:
                if store_url.startswith("https://"):
                    shop_domain = store_url[8:].rstrip("/")
                elif store_url.startswith("http://"):
                    shop_domain = store_url[7:].rstrip("/")
                else:
                    shop_domain = store_url.rstrip("/")
            else:
                # 从 external_system_id 构建，例如 x0ri77-4v -> x0ri77-4v.myshopify.com
                subdomain = shopify_system.external_system_id or ""
                shop_domain = f"{subdomain}.myshopify.com" if subdomain and ".myshopify.com" not in subdomain else subdomain

            if not shop_domain:
                logger.error(f"❌ 无法确定 shop_domain: external_system_id={shopify_system.id}")
                return None

            logger.info(f"✅ Shopify 凭据获取成功（与订单页面相同来源）: shop_domain={shop_domain}")

            return {
                "access_token": access_token,
                "shop_domain": shop_domain,
                "api_version": shopify_system.settings.get("api_version", "2024-01") if shopify_system.settings else "2024-01",
            }
        except Exception as e:
            logger.error(f"❌ 获取 Shopify 凭据失败: {str(e)}")
            return None
    
    async def _call_shopify_api(
        self, 
        credentials: Dict[str, Any], 
        endpoint: str, 
        method: str = "GET", 
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """调用 Shopify GraphQL API"""
        try:
            shop_domain = credentials['shop_domain']
            access_token = credentials['access_token']
            api_version = credentials.get('api_version', '2024-01')
            
            url = f"https://{shop_domain}/admin/api/{api_version}/graphql.json"
            
            headers = {
                'X-Shopify-Access-Token': access_token,
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                if method.upper() == "GET":
                    async with session.get(url, headers=headers) as response:
                        result = await response.json()
                else:
                    async with session.post(url, headers=headers, json=data) as response:
                        result = await response.json()
                
                if response.status != 200:
                    logger.error(f"❌ Shopify API 调用失败: status={response.status}, response={result}")
                    raise Exception(f"Shopify API error: {response.status}")
                
                logger.info(f"✅ Shopify API 调用成功: endpoint={endpoint}")
                return result
                
        except Exception as e:
            logger.error(f"❌ Shopify API 调用异常: {str(e)}")
            raise

    async def _call_shopify_graphql_api(
        self,
        credentials: Dict[str, Any],
        query: str,
        variables: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """调用 Shopify GraphQL API"""
        shop_domain = credentials.get("shop_domain")
        access_token = credentials.get("access_token")
        if not shop_domain or not access_token:
            raise Exception("Shopify credentials are incomplete")

        url = f"https://{shop_domain}/admin/api/2024-01/graphql.json"
        headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json"
        }
        payload = {"query": query, "variables": variables}

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    result = await response.json()
                    
                    if response.status != 200:
                        logger.error(f"❌ Shopify GraphQL API 调用失败: status={response.status}, response={result}")
                        raise Exception(f"Shopify GraphQL API error: {response.status}")
                    
                    logger.info(f"✅ Shopify GraphQL API 调用成功")
                    return result
                    
        except Exception as e:
            logger.error(f"❌ 调用 Shopify GraphQL API 失败: {e}")
            raise
    
    async def create_fulfillment(
        self, 
        scm_order, 
        tenant,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        为 SCM 订单创建 Shopify fulfillment
        
        Args:
            scm_order: SCM 订单对象
            tenant: 租户对象
            db: 数据库会话
            
        Returns:
            Dict: fulfillment 结果
        """
        try:
            logger.info(f"🚀 开始创建 Shopify fulfillment: scm_order_id={scm_order.id}")

            # 获取该 SCM 订单对应的 Shopify 店铺 ID，确保与订单页面使用同一套凭据
            external_system_id = await self._get_shopify_external_system_id(scm_order, db)
            credentials = await self._get_shopify_credentials(tenant, db, external_system_id)
            if not credentials:
                raise Exception("Shopify credentials not found for tenant")
            
            # 获取源订单的 Shopify 订单 ID
            shopify_order_id = await self._get_shopify_order_id(scm_order, db)
            if not shopify_order_id:
                raise Exception("Shopify order ID not found for SCM order")
            
            # 构建 fulfillment 数据
            fulfillment_data = await self._build_fulfillment_data(scm_order, shopify_order_id, credentials, db)
            
            # 调用 Shopify API 创建 fulfillment
            result = await self._call_shopify_graphql_api(
                credentials=credentials,
                query=fulfillment_data["query"],
                variables=fulfillment_data["variables"]
            )
            
            # 解析结果
            fulfillment_id = self._extract_fulfillment_id(result)
            
            logger.info(f"✅ Shopify fulfillment 创建成功: fulfillment_id={fulfillment_id}")
            
            return {
                "success": True,
                "fulfillment_id": fulfillment_id,
                "shopify_order_id": shopify_order_id,
                "tracking_number": scm_order.tracking_number,
                "tracking_url": scm_order.tracking_url,
                "carrier": scm_order.carrier
            }
            
        except Exception as e:
            logger.error(f"❌ 创建 Shopify fulfillment 失败: {str(e)}")
            import traceback
            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            raise
    
    async def _get_shopify_order_id(self, scm_order, db: AsyncSession) -> Optional[str]:
        """获取 SCM 订单关联的 Shopify 订单 ID"""
        try:
            # 如果 SCM 订单已经有 shopify_order_id，直接返回
            if scm_order.shopify_order_id:
                logger.info(f"✅ SCM 订单已有 Shopify 订单 ID: {scm_order.shopify_order_id}")
                return scm_order.shopify_order_id
            
            # 通过源订单获取 Shopify 订单 ID
            from app.models.order import Order
            from app.models.scm_order import ScmOrderSource
            
            # 获取源订单
            source_result = await db.execute(
                select(ScmOrderSource.source_order_id).where(
                    ScmOrderSource.scm_order_id == scm_order.id,
                    ScmOrderSource.tenant_id == scm_order.tenant_id
                )
            )
            source_orders = source_result.fetchall()
            
            if not source_orders:
                logger.error(f"❌ 未找到 SCM 订单的源订单: scm_order_id={scm_order.id}")
                return None
            
            source_order_id = source_orders[0][0]
            
            # 获取源订单的 external_order_id (Shopify 订单 ID)
            order_result = await db.execute(
                select(Order.external_order_id).where(
                    Order.id == source_order_id,
                    Order.tenant_id == scm_order.tenant_id
                )
            )
            order = order_result.scalar_one_or_none()
            
            if not order or not order.external_order_id:
                logger.error(f"❌ 源订单没有 Shopify 订单 ID: source_order_id={source_order_id}")
                return None
            
            shopify_order_id = order.external_order_id
            logger.info(f"✅ 通过源订单获取 Shopify 订单 ID: {shopify_order_id}")
            
            # 更新 SCM 订单的 shopify_order_id
            scm_order.shopify_order_id = shopify_order_id
            await db.commit()
            
            return shopify_order_id
            
        except Exception as e:
            logger.error(f"❌ 获取 Shopify 订单 ID 失败: {str(e)}")
            return None
    
    async def _get_shopify_variant_ids(self, scm_order, db) -> List[Dict[str, Any]]:
        """从 SCM 商品清单获取对应的 Shopify 变体 ID"""
        try:
            from app.models.product import ProductVariant
            from sqlalchemy import select, and_
            
            shopify_variants = []
            
            for line_item in scm_order.line_items:
                sku = line_item.get('metadata', {}).get('sku')
                quantity = line_item.get('quantity', 1)
                
                if not sku:
                    logger.warning(f"⚠️ SCM 商品项缺少 SKU: {line_item}")
                    continue
                
                # 查找对应的商品变体
                result = await db.execute(
                    select(ProductVariant).where(
                        and_(
                            ProductVariant.sku == sku,
                            ProductVariant.tenant_id == scm_order.tenant_id
                        )
                    )
                )
                variant = result.scalar_one_or_none()
                
                if variant and variant.external_variant_id:
                    shopify_variants.append({
                        'sku': sku,
                        'shopify_variant_id': variant.external_variant_id,
                        'quantity': quantity,
                        'title': line_item.get('metadata', {}).get('title', '')
                    })
                    logger.info(f"✅ 找到 Shopify 变体映射: {sku} -> {variant.external_variant_id}")
                else:
                    logger.warning(f"⚠️ 未找到 SKU {sku} 的 Shopify 变体映射")
            
            return shopify_variants
            
        except Exception as e:
            logger.error(f"❌ 获取 Shopify 变体 ID 失败: {str(e)}")
            raise

    async def _get_fulfillment_order_data(self, credentials: Dict[str, Any], shopify_order_id: str, shopify_variants: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取 Shopify fulfillment order 数据"""
        try:
            # 查询 fulfillment order
            query = """
                query getFulfillmentOrder($orderId: ID!) {
                    order(id: $orderId) {
                        fulfillmentOrders(first: 5) {
                            edges {
                                node {
                                    id
                                    status
                                    lineItems(first: 10) {
                                        edges {
                                            node {
                                                id
                                                totalQuantity
                                                remainingQuantity
                                                lineItem {
                                                    id
                                                    sku
                                                    variant {
                                                        id
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            """
            
            variables = {"orderId": shopify_order_id}
            
            result = await self._call_shopify_graphql_api(credentials, query, variables)
            
            logger.info(f"🔍 Shopify GraphQL 查询结果: {result}")
            
            if not result:
                raise Exception("Shopify API 返回空结果")
            
            if 'errors' in result:
                error_messages = [error.get('message', '') for error in result['errors']]
                raise Exception(f"Shopify GraphQL 错误: {', '.join(error_messages)}")
            
            if not result.get('data'):
                raise Exception("Shopify API 返回数据为空")
            
            if not result['data'].get('order'):
                raise Exception(f"Shopify 订单不存在: {shopify_order_id}")
            
            order_data = result['data']['order']
            fulfillment_orders = order_data.get('fulfillmentOrders', {}).get('edges', [])
            
            if not fulfillment_orders:
                raise Exception("订单没有可用的 fulfillment orders")
            
            # 使用第一个 fulfillment order
            fulfillment_order = fulfillment_orders[0]['node']
            fulfillment_order_id = fulfillment_order['id']
            fulfillment_status = fulfillment_order.get('status', '')
            line_items = fulfillment_order['lineItems']['edges']
            
            # 检查 fulfillment order 状态
            if fulfillment_status == 'CLOSED':
                raise Exception(f"Shopify fulfillment order 已关闭 (状态: {fulfillment_status})，无法创建新的 fulfillment")
            
            # 匹配 SCM 商品和 Shopify fulfillment order line items
            # 支持按 SKU 或 variant ID 匹配（Shopify 有时返回 sku: null）
            matched_line_items = []
            for shopify_variant in shopify_variants:
                for item_edge in line_items:
                    item_node = item_edge['node']
                    remaining_quantity = item_node.get('remainingQuantity', 0)
                    line_item = item_node.get('lineItem', {}) or {}
                    item_sku = line_item.get('sku')
                    item_variant_id = (line_item.get('variant') or {}).get('id')

                    if remaining_quantity <= 0:
                        logger.warning(f"⚠️ lineItem sku={item_sku} variant={item_variant_id} 剩余数量为 0，跳过")
                        continue

                    # 优先 SKU 匹配，其次 variant ID 匹配
                    sku_match = item_sku and item_sku == shopify_variant.get('sku')
                    variant_match = item_variant_id and item_variant_id == shopify_variant.get('shopify_variant_id')
                    if (sku_match or variant_match) and remaining_quantity >= shopify_variant['quantity']:
                        matched_line_items.append({
                            "id": item_node['id'],
                            "quantity": shopify_variant['quantity']
                        })
                        break
            
            if not matched_line_items:
                raise Exception("没有匹配的 fulfillment order line items（可能所有商品都已完全履行）")
            
            logger.info(f"✅ 获取到 fulfillment order: {fulfillment_order_id}")
            logger.info(f"✅ 匹配到 {len(matched_line_items)} 个 line items")
            
            return {
                'fulfillment_order_id': fulfillment_order_id,
                'line_items': matched_line_items
            }
            
        except Exception as e:
            logger.error(f"❌ 获取 fulfillment order 数据失败: {str(e)}")
            raise

    async def _build_fulfillment_data(self, scm_order, shopify_order_id: str, credentials: Dict[str, Any], db) -> Dict[str, Any]:
        """构建 Shopify fulfillment 数据"""
        try:
            # 1. 获取 SCM 商品对应的 Shopify 变体 ID
            shopify_variants = await self._get_shopify_variant_ids(scm_order, db)
            if not shopify_variants:
                raise Exception("没有找到对应的 Shopify 变体")
            
            # 2. 获取 fulfillment order 数据并匹配商品
            fulfillment_order_data = await self._get_fulfillment_order_data(credentials, shopify_order_id, shopify_variants)
            fulfillment_order_id = fulfillment_order_data['fulfillment_order_id']
            line_items = fulfillment_order_data['line_items']
            
            # 3. 构建 fulfillment 数据
            fulfillment_data = {
                "query": """
                    mutation fulfillmentCreateV2($fulfillment: FulfillmentV2Input!) {
                        fulfillmentCreateV2(fulfillment: $fulfillment) {
                            fulfillment {
                                id
                                status
                                trackingInfo {
                                    number
                                    url
                                    company
                                }
                            }
                            userErrors {
                                field
                                message
                            }
                        }
                    }
                """,
                "variables": {
                    "fulfillment": {
                        "lineItemsByFulfillmentOrder": [
                            {
                                "fulfillmentOrderId": fulfillment_order_id,
                                "fulfillmentOrderLineItems": line_items
                            }
                        ],
                        "trackingInfo": {
                            "number": scm_order.tracking_number or "",
                            "url": scm_order.tracking_url or "",
                            "company": scm_order.carrier or ""
                        },
                        "notifyCustomer": True
                    }
                }
            }
            
            logger.info(f"✅ Shopify fulfillment 数据构建完成: fulfillment_order_id={fulfillment_order_id}")
            return fulfillment_data
            
        except Exception as e:
            logger.error(f"❌ 构建 Shopify fulfillment 数据失败: {str(e)}")
            raise
    
    def _extract_fulfillment_id(self, result: Dict[str, Any]) -> str:
        """从 Shopify API 响应中提取 fulfillment ID"""
        try:
            logger.info(f"🔍 Shopify API 响应: {result}")
            
            # 处理 fulfillmentCreateV2 响应
            fulfillment = result.get('data', {}).get('fulfillmentCreateV2', {}).get('fulfillment', {})
            fulfillment_id = fulfillment.get('id', '')
            
            if not fulfillment_id:
                errors = result.get('data', {}).get('fulfillmentCreateV2', {}).get('userErrors', [])
                error_messages = [error.get('message', '') for error in errors]
                
                # 如果没有用户错误，检查其他可能的错误
                if not error_messages:
                    if 'errors' in result:
                        error_messages.append(f"GraphQL errors: {result['errors']}")
                    if 'data' not in result:
                        error_messages.append("No data in response")
                    elif 'fulfillmentCreateV2' not in result['data']:
                        error_messages.append("No fulfillmentCreateV2 in data")
                    else:
                        error_messages.append("Unknown error - no fulfillment ID returned")
                
                logger.error(f"❌ Shopify API 错误详情: {error_messages}")
                raise Exception(f"Shopify API errors: {', '.join(error_messages)}")
            
            logger.info(f"✅ 成功提取 fulfillment ID: {fulfillment_id}")
            return fulfillment_id
            
        except Exception as e:
            logger.error(f"❌ 提取 fulfillment ID 失败: {str(e)}")
            raise
    
    async def batch_create_fulfillments(
        self, 
        scm_orders: List, 
        tenant,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        批量创建 Shopify fulfillments
        
        Args:
            scm_orders: SCM 订单列表
            tenant: 租户对象
            db: 数据库会话
            
        Returns:
            Dict: 批量处理结果
        """
        try:
            logger.info(f"🚀 开始批量创建 Shopify fulfillments: count={len(scm_orders)}")
            
            results = {
                "success": [],
                "failed": [],
                "total": len(scm_orders)
            }
            
            for scm_order in scm_orders:
                try:
                    result = await self.create_fulfillment(scm_order, tenant, db)
                    results["success"].append({
                        "scm_order_id": scm_order.id,
                        "scm_order_number": scm_order.scm_order_number,
                        "fulfillment_id": result.get("fulfillment_id"),
                        "shopify_order_id": result.get("shopify_order_id")
                    })
                    logger.info(f"✅ SCM 订单 fulfillment 创建成功: {scm_order.scm_order_number}")
                    
                except Exception as e:
                    results["failed"].append({
                        "scm_order_id": scm_order.id,
                        "scm_order_number": scm_order.scm_order_number,
                        "error": str(e)
                    })
                    logger.error(f"❌ SCM 订单 fulfillment 创建失败: {scm_order.scm_order_number}, error={str(e)}")
            
            logger.info(f"✅ 批量创建 Shopify fulfillments 完成: success={len(results['success'])}, failed={len(results['failed'])}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 批量创建 Shopify fulfillments 失败: {str(e)}")
            raise
