"""
Printify 发货服务
处理 SCM 订单到 Printify 的发货指示
"""

from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
import aiohttp
from app.core.logging import get_logger
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class PrintifyFulfillmentService:
    """Printify 发货服务"""
    
    def __init__(self):
        self.base_url = "https://api.printify.com/v1"
        self.timeout = 30
    
    async def create_fulfillment_order(
        self, 
        scm_order, 
        tenant,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        创建 Printify 发货订单
        
        Args:
            scm_order: SCM 订单对象
            tenant: 租户对象
            
        Returns:
            Dict: 发货结果，包含 tracking_number, tracking_url, carrier 等
        """
        try:
            logger.info(f"🚀 开始创建 Printify 发货订单: scm_order_id={scm_order.id}")
            
            # 获取租户的 Printify 凭据
            printify_credentials = await self._get_printify_credentials(tenant)
            if not printify_credentials:
                raise Exception("Printify credentials not found for tenant")
            
            # 构建发货订单数据
            fulfillment_data = await self._build_fulfillment_data(scm_order)
            
            # 调用 Printify API
            result = await self._call_printify_api(
                credentials=printify_credentials,
                endpoint="/orders",
                method="POST",
                data=fulfillment_data
            )
            
            logger.info(f"✅ Printify 发货订单创建成功: fulfillment_id={result.get('id')}")
            
            return {
                "fulfillment_id": result.get('id'),
                "tracking_number": result.get('tracking_number'),
                "tracking_url": result.get('tracking_url'),
                "carrier": result.get('carrier'),
                "status": result.get('status'),
                "printify_order_id": result.get('id')
            }
            
        except Exception as e:
            logger.error(f"❌ Printify 发货订单创建失败: {str(e)}")
            import traceback
            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            raise
    
    async def _get_printify_credentials(self, tenant) -> Optional[Dict[str, str]]:
        """获取租户的 Printify 凭据"""
        try:
            # 这里应该从数据库获取租户的 Printify 凭据
            # 暂时返回模拟数据
            return {
                "api_token": "printify_api_token_here",
                "shop_id": "printify_shop_id_here"
            }
        except Exception as e:
            logger.error(f"❌ 获取 Printify 凭据失败: {str(e)}")
            return None
    
    async def _build_fulfillment_data(self, scm_order) -> Dict[str, Any]:
        """构建发货订单数据"""
        try:
            # 从 SCM 订单构建 Printify 订单数据
            fulfillment_data = {
                "external_id": f"scm_{scm_order.id}",
                "line_items": [],
                "shipping_method": 1,  # 标准发货
                "send_shipping_notification": True,
                "address_to": {
                    "first_name": scm_order.customer_name or "Customer",
                    "last_name": "",
                    "email": scm_order.customer_email,
                    "phone": scm_order.customer_phone or "",
                    "country": scm_order.shipping_address.get("country", "US"),
                    "region": scm_order.shipping_address.get("province", ""),
                    "city": scm_order.shipping_address.get("city", ""),
                    "address1": scm_order.shipping_address.get("address1", ""),
                    "address2": scm_order.shipping_address.get("address2", ""),
                    "zip": scm_order.shipping_address.get("zip", "")
                }
            }
            
            # 处理商品行项目
            for item in scm_order.line_items:
                if item.get("core_variant_id"):
                    # 这里需要根据 core_variant_id 查找对应的 Printify 产品
                    printify_product = await self._get_printify_product(item["core_variant_id"])
                    if printify_product:
                        fulfillment_data["line_items"].append({
                            "printify_product_id": printify_product["printify_product_id"],
                            "printify_variant_id": printify_product["printify_variant_id"],
                            "quantity": item["quantity"]
                        })
            
            logger.info(f"✅ 发货订单数据构建完成: line_items_count={len(fulfillment_data['line_items'])}")
            return fulfillment_data
            
        except Exception as e:
            logger.error(f"❌ 构建发货订单数据失败: {str(e)}")
            raise
    
    async def _get_printify_product(self, core_variant_id: int) -> Optional[Dict[str, Any]]:
        """根据核心变体ID获取对应的Printify产品"""
        try:
            # 这里应该从数据库查询产品映射关系
            # 暂时返回模拟数据
            return {
                "printify_product_id": "printify_product_id_here",
                "printify_variant_id": "printify_variant_id_here"
            }
        except Exception as e:
            logger.error(f"❌ 获取 Printify 产品失败: {str(e)}")
            return None
    
    async def _call_printify_api(
        self, 
        credentials: Dict[str, str], 
        endpoint: str, 
        method: str = "GET", 
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """调用 Printify API"""
        try:
            url = f"{self.base_url}{endpoint}"
            headers = {
                "Authorization": f"Bearer {credentials['api_token']}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                if method.upper() == "POST":
                    async with session.post(url, headers=headers, json=data) as response:
                        response_data = await response.json()
                        if response.status != 200:
                            raise Exception(f"Printify API error: {response.status} - {response_data}")
                        return response_data
                else:
                    async with session.get(url, headers=headers) as response:
                        response_data = await response.json()
                        if response.status != 200:
                            raise Exception(f"Printify API error: {response.status} - {response_data}")
                        return response_data
                        
        except Exception as e:
            logger.error(f"❌ Printify API 调用失败: {str(e)}")
            raise
