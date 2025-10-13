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
        self.base_url = "https://api.printify.com"
        self.timeout = 30
        
        # 国家代码映射表
        self.country_code_mapping = {
            "canada": "CA",
            "united states": "US",
            "united kingdom": "GB",
            "australia": "AU",
            "germany": "DE",
            "france": "FR",
            "spain": "ES",
            "italy": "IT",
            "netherlands": "NL",
            "belgium": "BE",
            "sweden": "SE",
            "norway": "NO",
            "denmark": "DK",
            "finland": "FI",
            "switzerland": "CH",
            "austria": "AT",
            "japan": "JP",
            "south korea": "KR",
            "china": "CN",
            "india": "IN",
            "brazil": "BR",
            "mexico": "MX",
            "argentina": "AR",
            "chile": "CL",
            "colombia": "CO",
            "peru": "PE",
            "venezuela": "VE",
            "south africa": "ZA",
            "egypt": "EG",
            "nigeria": "NG",
            "kenya": "KE",
            "morocco": "MA",
            "tunisia": "TN",
            "algeria": "DZ",
            "libya": "LY",
            "sudan": "SD",
            "ethiopia": "ET",
            "ghana": "GH",
            "uganda": "UG",
            "tanzania": "TZ",
            "zimbabwe": "ZW",
            "botswana": "BW",
            "namibia": "NA",
            "zambia": "ZM",
            "malawi": "MW",
            "madagascar": "MG",
            "mozambique": "MZ",
            "angola": "AO",
            "cameroon": "CM",
            "cote d'ivoire": "CI",
            "senegal": "SN",
            "mali": "ML",
            "burkina faso": "BF",
            "niger": "NE",
            "chad": "TD",
            "central african republic": "CF",
            "democratic republic of the congo": "CD",
            "republic of the congo": "CG",
            "gabon": "GA",
            "equatorial guinea": "GQ",
            "sao tome and principe": "ST",
            "cape verde": "CV",
            "guinea-bissau": "GW",
            "guinea": "GN",
            "sierra leone": "SL",
            "liberia": "LR",
            "gambia": "GM",
            "mauritania": "MR",
            "western sahara": "EH",
            "morocco": "MA",
            "algeria": "DZ",
            "tunisia": "TN",
            "libya": "LY",
            "egypt": "EG",
            "sudan": "SD",
            "south sudan": "SS",
            "ethiopia": "ET",
            "eritrea": "ER",
            "djibouti": "DJ",
            "somalia": "SO",
            "kenya": "KE",
            "uganda": "UG",
            "tanzania": "TZ",
            "rwanda": "RW",
            "burundi": "BI",
            "democratic republic of the congo": "CD",
            "central african republic": "CF",
            "cameroon": "CM",
            "chad": "TD",
            "niger": "NE",
            "nigeria": "NG",
            "benin": "BJ",
            "togo": "TG",
            "ghana": "GH",
            "burkina faso": "BF",
            "mali": "ML",
            "senegal": "SN",
            "gambia": "GM",
            "guinea-bissau": "GW",
            "guinea": "GN",
            "sierra leone": "SL",
            "liberia": "LR",
            "cote d'ivoire": "CI",
            "ghana": "GH",
            "togo": "TG",
            "benin": "BJ",
            "nigeria": "NG",
            "niger": "NE",
            "chad": "TD",
            "cameroon": "CM",
            "central african republic": "CF",
            "democratic republic of the congo": "CD",
            "republic of the congo": "CG",
            "gabon": "GA",
            "equatorial guinea": "GQ",
            "sao tome and principe": "ST",
            "angola": "AO",
            "zambia": "ZM",
            "malawi": "MW",
            "mozambique": "MZ",
            "madagascar": "MG",
            "mauritius": "MU",
            "seychelles": "SC",
            "comoros": "KM",
            "mayotte": "YT",
            "reunion": "RE",
            "french southern territories": "TF",
            "british indian ocean territory": "IO",
            "south africa": "ZA",
            "lesotho": "LS",
            "swaziland": "SZ",
            "botswana": "BW",
            "namibia": "NA",
            "zimbabwe": "ZW",
            "zambia": "ZM",
            "malawi": "MW",
            "mozambique": "MZ",
            "madagascar": "MG",
            "mauritius": "MU",
            "seychelles": "SC",
            "comoros": "KM",
            "mayotte": "YT",
            "reunion": "RE",
            "french southern territories": "TF",
            "british indian ocean territory": "IO"
        }
    
    def _normalize_country_code(self, country: str) -> str:
        """标准化国家代码为 Printify API 要求的格式"""
        if not country:
            return "US"
        
        country_lower = country.lower().strip()
        
        # 如果已经是两位字母代码，直接返回大写
        if len(country_lower) == 2 and country_lower.isalpha():
            return country_lower.upper()
        
        # 查找映射表
        if country_lower in self.country_code_mapping:
            return self.country_code_mapping[country_lower]
        
        # 如果没有找到映射，返回原始值的大写形式
        return country.upper()
    
    def _extract_first_name(self, shipping_address: dict) -> str:
        """从发货地址中提取名字"""
        if not shipping_address:
            return "Customer"
        
        # 尝试从 name 字段中提取名字
        full_name = shipping_address.get("name", "")
        if full_name:
            # 按空格分割，取最后一部分作为名字
            name_parts = full_name.strip().split()
            if name_parts:
                return name_parts[-1]  # 取最后一部分作为名字
        
        # 如果没有 name 字段，尝试使用 firstName
        first_name = shipping_address.get("firstName", "")
        if first_name:
            return first_name
        
        return "Customer"
    
    def _extract_last_name(self, shipping_address: dict) -> str:
        """从发货地址中提取姓氏"""
        if not shipping_address:
            return ""
        
        # 尝试从 name 字段中提取姓氏
        full_name = shipping_address.get("name", "")
        if full_name:
            # 按空格分割，取除最后一部分外的所有部分作为姓氏
            name_parts = full_name.strip().split()
            if len(name_parts) > 1:
                return " ".join(name_parts[:-1])  # 取除最后一部分外的所有部分作为姓氏
            elif len(name_parts) == 1:
                return ""  # 只有一个词，没有姓氏
        
        # 如果没有 name 字段，尝试使用 lastName
        last_name = shipping_address.get("lastName", "")
        if last_name:
            return last_name
        
        return ""
    
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
            printify_credentials = await self._get_printify_credentials(tenant, db)
            if not printify_credentials:
                raise Exception("Printify credentials not found for tenant")
            
            # 构建发货订单数据
            fulfillment_data = await self._build_fulfillment_data(scm_order, db, tenant)
            
            # 调用 Printify API - 使用正确的端点格式
            shop_id = printify_credentials.get('store_url')  # store_url 实际上是 shop_id
            endpoint = f"/v1/shops/{shop_id}/orders.json"
            logger.info(f"🔍 调用 Printify API: endpoint={endpoint}, shop_id={shop_id}")
            logger.info(f"🔍 发货订单数据: {fulfillment_data}")
            
            result = await self._call_printify_api(
                credentials=printify_credentials,
                endpoint=endpoint,
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
    
    async def _get_printify_credentials(self, tenant, db: AsyncSession = None) -> Optional[Dict[str, str]]:
        """获取租户的 Printify 凭据"""
        try:
            from app.models.external_system import ExternalSystem, ExternalSystemType
            from app.core.security import decrypt_data
            from sqlalchemy import select
            
            if not db:
                logger.error("❌ 数据库会话未提供")
                return None
            
            # 查询 Printify 外部系统
            result = await db.execute(
                select(ExternalSystem).where(
                    ExternalSystem.tenant_id == tenant.id,
                    ExternalSystem.system_type == ExternalSystemType.PRINTIFY,
                    ExternalSystem.is_active == True
                )
            )
            external_system = result.scalar_one_or_none()
            
            if not external_system:
                logger.error(f"❌ 未找到 Printify 外部系统: tenant_id={tenant.id}")
                return None
            
            # 解密凭据
            credentials = external_system.credentials or {}
            decrypted_credentials = {}
            
            for key, encrypted_value in credentials.items():
                try:
                    if encrypted_value:
                        decrypted_credentials[key] = decrypt_data(encrypted_value)
                        logger.info(f"✅ 凭据解密成功: {key}")
                    else:
                        logger.warning(f"⚠️ 凭据为空: {key}")
                except Exception as e:
                    logger.error(f"❌ 凭据解密失败: {key}, 错误: {str(e)}")
                    return None
            
            logger.info(f"🔍 解密完成，开始映射逻辑 - 强制测试日志")
            # 映射字段名到期望的格式
            mapped_credentials = {}
            logger.info(f"🔍 开始映射凭据: {list(decrypted_credentials.keys())}")
            logger.info(f"🔍 调试信息: access_token={decrypted_credentials.get('access_token', 'None')[:10]}..., shop_id={decrypted_credentials.get('shop_id', 'None')}")
            
            # 优先从 api_key 和 store_url 获取，如果不存在或为空，则从 access_token 和 shop_id 映射
            api_key = decrypted_credentials.get('api_key')
            if not api_key:
                api_key = decrypted_credentials.get('access_token')
                if api_key:
                    logger.info(f"✅ 映射 access_token -> api_key")
            else:
                logger.info(f"✅ 使用现有 api_key")
            
            store_url = decrypted_credentials.get('store_url')
            if not store_url:
                store_url = decrypted_credentials.get('shop_id')
                if store_url:
                    logger.info(f"✅ 映射 shop_id -> store_url")
            else:
                logger.info(f"✅ 使用现有 store_url")
            
            if api_key:
                mapped_credentials['api_key'] = api_key
            if store_url:
                mapped_credentials['store_url'] = store_url
            
            logger.info(f"🔍 映射后的凭据: {list(mapped_credentials.keys())}")
            
            # 检查必需的凭据
            required_credentials = ['api_key', 'store_url']
            missing_credentials = [key for key in required_credentials if not mapped_credentials.get(key)]
            
            if missing_credentials:
                logger.error(f"❌ 缺少必需的凭据: {missing_credentials}")
                logger.error(f"   可用凭据: {list(decrypted_credentials.keys())}")
                return None
            
            logger.info(f"✅ Printify 凭据获取成功: store_url={mapped_credentials.get('store_url')}")
            return mapped_credentials
            
        except Exception as e:
            logger.error(f"❌ 获取 Printify 凭据失败: {str(e)}")
            import traceback
            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            return None

    
    async def _build_fulfillment_data(self, scm_order, db, tenant) -> Dict[str, Any]:
        """构建发货订单数据"""
        try:
            # 从 SCM 订单构建 Printify 订单数据
            fulfillment_data = {
                "external_id": f"scm_{scm_order.id}",
                "line_items": [],
                "shipping_method": 1,  # 标准发货
                "send_shipping_notification": True,
                "status": "onhold",  # 添加状态字段
                "address_to": {
                    "first_name": self._extract_first_name(scm_order.shipping_address),
                    "last_name": self._extract_last_name(scm_order.shipping_address),
                    "email": scm_order.customer_email,
                    "phone": scm_order.customer_phone or "",
                    "country": self._normalize_country_code(scm_order.shipping_address.get("country", "US")),
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
                    printify_product = await self._get_printify_product(item["core_variant_id"], db, tenant.id)
                    if printify_product:
                        fulfillment_data["line_items"].append({
                            "product_id": printify_product["printify_product_id"],
                            "variant_id": int(printify_product["printify_variant_id"]),  # 确保是整数
                            "quantity": item["quantity"]
                        })
            
            logger.info(f"✅ 发货订单数据构建完成: line_items_count={len(fulfillment_data['line_items'])}")
            return fulfillment_data
            
        except Exception as e:
            logger.error(f"❌ 构建发货订单数据失败: {str(e)}")
            raise
    
    async def _get_printify_product(self, core_variant_id: int, db, tenant_id: int) -> Optional[Dict[str, Any]]:
        """根据核心变体ID获取对应的Printify产品"""
        try:
            from app.models.product import ProductMapping
            from app.models.external_system import ExternalSystem, ExternalSystemType
            from sqlalchemy import select, and_
            
            # 查询 Printify 外部系统
            external_system_result = await db.execute(
                select(ExternalSystem).where(
                    and_(
                        ExternalSystem.tenant_id == tenant_id,
                        ExternalSystem.system_type == ExternalSystemType.PRINTIFY
                    )
                )
            )
            external_system = external_system_result.scalar_one_or_none()
            
            if not external_system:
                logger.error(f"❌ 未找到 Printify 外部系统: tenant_id={tenant_id}")
                return None
            
            # 查询产品映射
            mapping_result = await db.execute(
                select(ProductMapping).where(
                    and_(
                        ProductMapping.core_variant_id == core_variant_id,
                        ProductMapping.tenant_id == tenant_id,
                        ProductMapping.external_system_id == external_system.id
                    )
                )
            )
            mapping = mapping_result.scalar_one_or_none()
            
            if not mapping:
                logger.warning(f"⚠️ 未找到 Printify 产品映射: core_variant_id={core_variant_id}")
                return None
            
            logger.info(f"✅ 找到 Printify 产品映射: core_variant_id={core_variant_id}, external_product_id={mapping.external_product_id}, external_variant_id={mapping.external_variant_id}")
            
            return {
                "printify_product_id": mapping.external_product_id,
                "printify_variant_id": mapping.external_variant_id
            }
        except Exception as e:
            logger.error(f"❌ 获取 Printify 产品失败: {str(e)}")
            import traceback
            logger.error(f"   异常堆栈: {traceback.format_exc()}")
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
            # Printify API 使用固定的基础 URL
            base_url = self.base_url  # https://api.printify.com
            url = f"{base_url}{endpoint}"
            headers = {
                "Authorization": f"Bearer {credentials['api_key']}",
                "Content-Type": "application/json",
                "User-Agent": "SupplyNexus-Printify-Integration"
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
