"""
Printify 发货服务
处理 SCM 订单到 Printify 的发货指示
"""

from typing import Dict, Any, Optional, List
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
    
    def _get_phone_number(self, scm_order) -> str:
        """获取电话号码，优先使用 customer_phone，其次从 shipping_address 获取，都没有则返回默认值"""
        # 优先使用 customer_phone（兼容 SimpleNamespace 等可能无该属性的对象）
        customer_phone = getattr(scm_order, "customer_phone", None)
        if customer_phone:
            phone = str(customer_phone).strip()
            if phone:
                return phone
        
        # 其次从 shipping_address 获取
        shipping_address = getattr(scm_order, "shipping_address", None)
        if shipping_address and isinstance(shipping_address, dict):
            phone = shipping_address.get("phone")
            if phone:
                phone = str(phone).strip()
                if phone:
                    return phone
        
        # 如果都没有，返回默认值（Printify API 要求 phone 字段必须有值）
        # 使用一个合理的默认值，格式为 +1XXXXXXXXXX（美国格式）
        return "+10000000000"
    
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
            
            # 验证产品是否存在于 Printify 店铺中（在创建订单前验证）
            shop_id = printify_credentials.get('store_url')  # store_url 实际上是 shop_id
            validation_result = await self._validate_printify_products_strict(printify_credentials, shop_id, fulfillment_data.get('line_items', []), db, tenant)
            if not validation_result["valid"]:
                error_msg = "产品验证失败"
                if validation_result.get("errors"):
                    error_msg += f": {', '.join(validation_result['errors'])}"
                logger.error(f"❌ {error_msg}")
                raise ValueError(error_msg)
            
            # 调用 Printify API - 使用正确的端点格式
            endpoint = f"/v1/shops/{shop_id}/orders.json"
            logger.info(f"🔍 调用 Printify API: endpoint={endpoint}, shop_id={shop_id}")
            logger.info(f"🔍 发货订单数据: {fulfillment_data}")
            
            try:
                result = await self._call_printify_api(
                    credentials=printify_credentials,
                    endpoint=endpoint,
                    method="POST",
                    data=fulfillment_data
                )
            except Exception as e:
                error_str = str(e)
                # 检查是否是订单已存在的错误
                if "already exists" in error_str.lower() or "unique_id" in error_str.lower():
                    logger.warning(
                        f"⚠️ Printify 订单已存在: external_id={fulfillment_data.get('external_id')}, 尝试从数据库查找"
                    )
                    # 尝试从数据库查找已存在的订单
                    from app.models.printify_order import PrintifyOrder
                    from sqlalchemy import select, and_
                    
                    existing_order_result = await db.execute(
                        select(PrintifyOrder).where(
                            and_(
                                PrintifyOrder.scm_order_id == scm_order.id,
                                PrintifyOrder.tenant_id == tenant.id
                            )
                        )
                    )
                    existing_order = existing_order_result.scalar_one_or_none()
                    
                    if existing_order:
                        logger.info(
                            f"✅ 找到已存在的 Printify 订单: external_order_id={existing_order.external_order_id}"
                        )
                        # 返回已存在的订单信息
                        return {
                            "fulfillment_id": existing_order.external_order_id,
                            "tracking_number": existing_order.tracking_number,
                            "tracking_url": existing_order.tracking_url,
                            "carrier": existing_order.carrier,
                            "status": existing_order.status,
                            "printify_order_id": existing_order.external_order_id
                        }
                    else:
                        # 订单在 Printify 中存在但不在本地数据库，需要同步
                        logger.error(
                            f"❌ Printify 订单已存在但未在本地数据库中找到: external_id={fulfillment_data.get('external_id')}"
                        )
                        logger.error(
                            f"   建议：运行同步任务从 Printify API 同步订单到本地数据库"
                        )
                        raise Exception(
                            f"Printify 订单已存在 (external_id={fulfillment_data.get('external_id')})，但未在本地数据库中找到。"
                            f"请运行同步任务或手动同步订单。"
                        )
                else:
                    # 其他错误，直接抛出
                    raise
            
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
            # 检查是否已经存在 Printify 订单（通过 external_id）
            # 如果已存在，使用现有的 external_id；否则使用更唯一的标识
            from app.models.printify_order import PrintifyOrder
            from sqlalchemy import select, and_
            
            # 先尝试使用 scm_order.id 查找
            existing_order_result = await db.execute(
                select(PrintifyOrder).where(
                    and_(
                        PrintifyOrder.scm_order_id == scm_order.id,
                        PrintifyOrder.tenant_id == tenant.id
                    )
                )
            )
            existing_order = existing_order_result.scalar_one_or_none()
            
            if existing_order:
                # 如果已存在，使用现有的 external_order_id 作为 external_id
                external_id = existing_order.external_order_id
                logger.info(f"ℹ️ 使用已存在的 Printify 订单 external_id: {external_id}")
            else:
                # 如果不存在，使用 SCM 订单编号或 ID 作为 external_id
                # 优先使用 scm_order_number，如果没有则使用 scm_{id}
                if scm_order.scm_order_number:
                    external_id = scm_order.scm_order_number
                else:
                    external_id = f"scm_{scm_order.id}"
                logger.info(f"ℹ️ 使用新的 external_id: {external_id}")
            
            # 从 SCM 订单构建 Printify 订单数据（兼容 SCMOrder 与 SimpleNamespace，防御 shipping_address 为空）
            shipping_address = getattr(scm_order, "shipping_address", None) or {}
            if not isinstance(shipping_address, dict):
                shipping_address = {}
            fulfillment_data = {
                "external_id": external_id,
                "line_items": [],
                "shipping_method": 1,  # 标准发货
                "send_shipping_notification": True,
                "status": "onhold",  # 添加状态字段
                "address_to": {
                    "first_name": self._extract_first_name(shipping_address),
                    "last_name": self._extract_last_name(shipping_address),
                    "email": getattr(scm_order, "customer_email", "") or "",
                    "phone": self._get_phone_number(scm_order),
                    "country": self._normalize_country_code(shipping_address.get("country", "US")),
                    "region": shipping_address.get("province", ""),
                    "city": shipping_address.get("city", ""),
                    "address1": shipping_address.get("address1", ""),
                    "address2": shipping_address.get("address2") or "",  # 确保 None 转换为空字符串
                    "zip": shipping_address.get("zip", "")
                }
            }
            
            # 处理商品行项目
            for item in scm_order.line_items:
                # 优先使用已提供的 external_product_id 和 external_variant_id（来自 generate_printify_order）
                if item.get("external_product_id") and item.get("external_variant_id"):
                    product_id = item["external_product_id"]
                    variant_id = item["external_variant_id"]
                    
                    # 验证 product_id 格式（Printify 产品 ID 应该是 24 位十六进制字符串，类似 MongoDB ObjectId）
                    if not isinstance(product_id, str) or len(product_id) != 24:
                        logger.warning(f"⚠️ 产品 ID 格式可能不正确: product_id={product_id}, 长度={len(str(product_id))}, 类型={type(product_id)}")
                    
                    fulfillment_data["line_items"].append({
                        "product_id": product_id,
                        "variant_id": int(variant_id),  # 确保是整数
                        "quantity": item.get("quantity", 1)
                    })
                    logger.info(f"✅ 添加商品到 line_items (使用外部ID): product_id={product_id}, variant_id={variant_id}, quantity={item.get('quantity', 1)}")
                    continue
                
                # 如果没有外部ID，尝试通过 core_variant_id 查找
                printify_product = None
                if item.get("core_variant_id"):
                    printify_product = await self._get_printify_product(item["core_variant_id"], db, tenant.id)
                else:
                    # 如果没有 core_variant_id，尝试通过 SKU 查找
                    sku = item.get("metadata", {}).get("sku")
                    if sku:
                        printify_product = await self._get_printify_product_by_sku(sku, db, tenant.id)
                
                if printify_product:
                    fulfillment_data["line_items"].append({
                        "product_id": printify_product["printify_product_id"],
                        "variant_id": int(printify_product["printify_variant_id"]),  # 确保是整数
                        "quantity": item.get("quantity", 1)
                    })
                    logger.info(f"✅ 添加商品到 line_items: product_id={printify_product['printify_product_id']}, variant_id={printify_product['printify_variant_id']}, quantity={item.get('quantity', 1)}")
                else:
                    logger.warning(f"⚠️ 跳过商品，未找到 Printify 映射: {item}")
            
            logger.info(f"✅ 发货订单数据构建完成: line_items_count={len(fulfillment_data['line_items'])}")
            
            # 验证 line_items 不为空
            if not fulfillment_data["line_items"]:
                logger.error(f"❌ line_items 为空，无法创建 Printify 订单")
                raise ValueError("line_items is required but empty. Please ensure all selected items have valid Printify product mappings.")
            
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
    
    async def _get_printify_product_by_sku(self, sku: str, db, tenant_id: int) -> Optional[Dict[str, Any]]:
        """根据 SKU 获取对应的 Printify 产品"""
        try:
            from app.models.product import ProductVariant, ProductMapping
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
            
            # 通过 SKU 查找核心变体
            variant_result = await db.execute(
                select(ProductVariant).where(
                    and_(
                        ProductVariant.tenant_id == tenant_id,
                        ProductVariant.sku == sku
                    )
                )
            )
            core_variant = variant_result.scalar_one_or_none()
            
            if not core_variant:
                logger.warning(f"⚠️ 未找到核心变体: sku={sku}")
                return None
            
            # 查询产品映射
            mapping_result = await db.execute(
                select(ProductMapping).where(
                    and_(
                        ProductMapping.core_variant_id == core_variant.id,
                        ProductMapping.tenant_id == tenant_id,
                        ProductMapping.external_system_id == external_system.id
                    )
                )
            )
            mapping = mapping_result.scalar_one_or_none()
            
            if not mapping:
                logger.warning(f"⚠️ 未找到 Printify 产品映射: sku={sku}, core_variant_id={core_variant.id}")
                return None
            
            logger.info(f"✅ 通过 SKU 找到 Printify 产品映射: sku={sku}, external_product_id={mapping.external_product_id}, external_variant_id={mapping.external_variant_id}")
            
            return {
                "printify_product_id": mapping.external_product_id,
                "printify_variant_id": mapping.external_variant_id
            }
        except Exception as e:
            logger.error(f"❌ 通过 SKU 获取 Printify 产品失败: {str(e)}")
            import traceback
            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            return None

    async def enrich_line_items_with_printify_mapping(
        self, line_items: list, db, tenant_id: int, source_order_id: Optional[int] = None
    ) -> list:
        """
        为 line_items 预填充 external_product_id 和 external_variant_id（与 generate-printify 逻辑一致）
        用于自动化流程，在调用 create_fulfillment_order 前增强行项目。
        当 core_variant_id 和 sku 为空时，可选通过 source_order_id + source_line_item_id 从 OrderItem 解析（与手动创建时 SCM API 的规范化逻辑一致）。
        """
        from app.models.product import ProductVariant, ProductMapping
        from app.models.order import OrderItem
        from app.models.external_system import ExternalSystem, ExternalSystemType
        from sqlalchemy import select, and_

        if not line_items:
            return []

        # 获取 Printify 外部系统
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
            logger.warning(f"⚠️ 未找到 Printify 外部系统: tenant_id={tenant_id}")
            return list(line_items)

        enhanced_items = []
        for item in line_items:
            item_copy = dict(item) if isinstance(item, dict) else item.copy()

            # 已有映射则跳过
            if item_copy.get("external_product_id") and item_copy.get("external_variant_id"):
                enhanced_items.append(item_copy)
                continue

            core_variant = None
            mapping = None

            # 优先通过 core_variant_id 查找
            if item_copy.get("core_variant_id"):
                variant_result = await db.execute(
                    select(ProductVariant).where(
                        and_(
                            ProductVariant.id == item_copy["core_variant_id"],
                            ProductVariant.tenant_id == tenant_id
                        )
                    )
                )
                core_variant = variant_result.scalar_one_or_none()
            # 其次通过 metadata.sku 查找
            elif item_copy.get("metadata", {}).get("sku"):
                sku = item_copy["metadata"]["sku"]
                if isinstance(sku, str) and sku.strip():
                    variant_result = await db.execute(
                        select(ProductVariant).where(
                            and_(
                                ProductVariant.tenant_id == tenant_id,
                                ProductVariant.sku == sku
                            )
                        )
                    )
                    core_variant = variant_result.scalar_one_or_none()
            # 回退：通过 source_line_item_id 从 OrderItem 解析（source_line_item_id 即 OrderItem.id；有 source_order_id 时限定订单范围）
            meta = dict(item_copy.get("metadata") or {})
            source_line_item_id = meta.get("source_line_item_id")
            if not core_variant and source_line_item_id is not None:
                if source_order_id:
                    order_item_result = await db.execute(
                        select(OrderItem).where(
                            and_(
                                OrderItem.order_id == source_order_id,
                                OrderItem.tenant_id == tenant_id
                            )
                        )
                    )
                    order_items = order_item_result.scalars().all()
                else:
                    order_item_result = await db.execute(
                        select(OrderItem).where(
                            and_(OrderItem.tenant_id == tenant_id, OrderItem.id == source_line_item_id)
                        )
                    )
                    order_items = order_item_result.scalars().all()
                for oi in order_items:
                    if oi.id == source_line_item_id or str(oi.id) == str(source_line_item_id):
                        if oi.core_variant_id:
                            item_copy["core_variant_id"] = oi.core_variant_id
                            item_copy["core_product_id"] = oi.core_product_id
                            if oi.sku and (not meta.get("sku") or not str(meta.get("sku", "")).strip()):
                                meta["sku"] = oi.sku
                                item_copy["metadata"] = meta
                            logger.info(f"✅ 从 OrderItem 解析: source_line_item_id={source_line_item_id} -> core_variant_id={oi.core_variant_id}, sku={oi.sku}")
                        break

            # 若通过 OrderItem 解析到了 core_variant_id，再查 ProductVariant 获取 core_variant
            if not core_variant and item_copy.get("core_variant_id"):
                variant_result = await db.execute(
                    select(ProductVariant).where(
                        and_(
                            ProductVariant.id == item_copy["core_variant_id"],
                            ProductVariant.tenant_id == tenant_id
                        )
                    )
                )
                core_variant = variant_result.scalar_one_or_none()
            elif not core_variant and item_copy.get("metadata", {}).get("sku"):
                sku = item_copy["metadata"]["sku"]
                if isinstance(sku, str) and sku.strip():
                    variant_result = await db.execute(
                        select(ProductVariant).where(
                            and_(
                                ProductVariant.tenant_id == tenant_id,
                                ProductVariant.sku == sku
                            )
                        )
                    )
                    core_variant = variant_result.scalar_one_or_none()

            if core_variant:
                mapping_result = await db.execute(
                    select(ProductMapping).where(
                        and_(
                            ProductMapping.core_variant_id == core_variant.id,
                            ProductMapping.tenant_id == tenant_id,
                            ProductMapping.external_system_id == external_system.id
                        )
                    )
                )
                mapping = mapping_result.scalar_one_or_none()

            if mapping:
                item_copy["core_product_id"] = core_variant.product_id
                item_copy["core_variant_id"] = core_variant.id
                item_copy["external_product_id"] = mapping.external_product_id
                item_copy["external_variant_id"] = mapping.external_variant_id
                logger.info(f"✅ 预增强行项目: sku={item_copy.get('metadata', {}).get('sku')}, external_variant_id={mapping.external_variant_id}")
            else:
                sku = item_copy.get("metadata", {}).get("sku")
                logger.debug(f"⚠️ 行项目无 Printify 映射: sku={sku}, core_variant_id={item_copy.get('core_variant_id')}")

            enhanced_items.append(item_copy)

        return enhanced_items

    async def get_printify_products(self, credentials: Dict[str, str], shop_id: str) -> List[Dict[str, Any]]:
        """获取 Printify 店铺中的产品列表"""
        try:
            endpoint = f"/v1/shops/{shop_id}/products.json"
            logger.info(f"🔍 调用 Printify API 获取产品列表: endpoint={endpoint}, shop_id={shop_id}")
            products_data = await self._call_printify_api(credentials, endpoint, "GET")
            products_list = products_data.get("data", [])
            logger.info(f"✅ 获取到 {len(products_list)} 个 Printify 产品")
            return products_list
        except Exception as e:
            logger.error(f"❌ 获取 Printify 产品列表失败: {str(e)}")
            import traceback
            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            return []

    async def _validate_printify_products(self, credentials: Dict[str, str], shop_id: str, line_items: List[Dict], db, tenant) -> None:
        """验证产品是否存在于 Printify 店铺中，如果不存在则尝试更新映射"""
        try:
            # 获取店铺中的实际产品列表
            actual_products = await self.get_printify_products(credentials, shop_id)
            if not actual_products:
                logger.warning(f"⚠️ 无法获取 Printify 店铺产品列表: shop_id={shop_id}")
                return
            
            # 创建产品ID到产品信息的映射
            product_map = {}
            for product in actual_products:
                product_id = product.get('id')
                if product_id:
                    product_map[product_id] = product
            
            # 检查每个line_item中的产品
            for item in line_items:
                product_id = item.get('product_id')
                variant_id = item.get('variant_id')
                
                if product_id not in product_map:
                    logger.error(f"❌ 产品不存在于 Printify 店铺: product_id={product_id}, shop_id={shop_id}")
                    # 这里可以添加更新产品映射的逻辑
                    await self._update_product_mapping_for_missing_product(product_id, variant_id, actual_products, db, tenant)
                else:
                    # 验证变体是否存在
                    product = product_map[product_id]
                    variants = product.get('variants', [])
                    variant_exists = any(str(v.get('id')) == str(variant_id) for v in variants)
                    
                    if not variant_exists:
                        logger.error(f"❌ 变体不存在于产品中: product_id={product_id}, variant_id={variant_id}")
                        # 这里可以添加更新变体映射的逻辑
                        await self._update_variant_mapping_for_missing_variant(product_id, variant_id, variants, db, tenant)
                    else:
                        logger.info(f"✅ 产品验证通过: product_id={product_id}, variant_id={variant_id}")
                        
        except Exception as e:
            logger.error(f"❌ 验证 Printify 产品失败: {str(e)}")
            import traceback
            logger.error(f"   异常堆栈: {traceback.format_exc()}")
    
    async def _validate_printify_products_strict(self, credentials: Dict[str, str], shop_id: str, line_items: List[Dict], db, tenant) -> Dict[str, Any]:
        """
        严格验证产品是否存在于 Printify 店铺中（创建订单前必须验证）
        如果产品不存在，直接返回错误，不创建订单
        
        Returns:
            Dict: {
                "valid": bool,
                "errors": List[str],
                "missing_products": List[str]
            }
        """
        try:
            logger.info(f"🔍 开始严格验证 Printify 产品: shop_id={shop_id}, line_items_count={len(line_items)}")
            
            # 获取店铺中的实际产品列表
            actual_products = await self.get_printify_products(credentials, shop_id)
            if not actual_products:
                logger.error(f"❌ 无法获取 Printify 店铺产品列表: shop_id={shop_id}")
                return {
                    "valid": False,
                    "errors": [f"无法获取 Printify 店铺 {shop_id} 的产品列表"],
                    "missing_products": []
                }
            
            logger.info(f"✅ 获取到 {len(actual_products)} 个 Printify 产品")
            
            # 创建产品ID到产品信息的映射
            product_map = {}
            product_ids_list = []
            for product in actual_products:
                product_id = product.get('id')
                if product_id:
                    product_map[product_id] = product
                    product_ids_list.append(product_id)
            
            # 记录产品列表的前几个 ID 用于调试
            logger.info(f"🔍 Printify 店铺 {shop_id} 中的产品 ID 列表（前10个）: {product_ids_list[:10]}")
            logger.info(f"🔍 要验证的产品 ID: {[item.get('product_id') for item in line_items]}")
            
            # 如果数据库中有 PrintifyProduct 记录，也检查一下 shop_id 匹配情况
            from app.models.printify_product import PrintifyProduct
            from app.models.external_system import ExternalSystem, ExternalSystemType
            from sqlalchemy import select, and_
            
            # 获取 Printify 外部系统
            external_system_result = await db.execute(
                select(ExternalSystem).where(
                    and_(
                        ExternalSystem.tenant_id == tenant.id,
                        ExternalSystem.system_type == ExternalSystemType.PRINTIFY
                    )
                )
            )
            external_system = external_system_result.scalar_one_or_none()
            
            errors = []
            missing_products = []
            
            # 检查每个line_item中的产品
            for item in line_items:
                try:
                    product_id = item.get('product_id')
                    variant_id = item.get('variant_id')
                    
                    if not product_id:
                        errors.append(f"line_item 缺少 product_id: {item}")
                        continue
                    
                    # 检查数据库中 PrintifyProduct 记录的 shop_id
                    if external_system:
                        printify_product_result = await db.execute(
                            select(PrintifyProduct).where(
                                and_(
                                    PrintifyProduct.tenant_id == tenant.id,
                                    PrintifyProduct.external_system_id == external_system.id,
                                    PrintifyProduct.printify_product_id == product_id
                                )
                            )
                        )
                        printify_product = printify_product_result.scalar_one_or_none()
                        
                        if printify_product:
                            product_shop_id = printify_product.printify_shop_id
                            logger.info(f"🔍 产品 {product_id} 在数据库中的 shop_id: {product_shop_id}, 当前使用的 shop_id: {shop_id}")
                            
                            # 如果 shop_id 不匹配，记录详细信息
                            if product_shop_id and str(product_shop_id) != str(shop_id):
                                logger.warning(f"⚠️ Shop ID 不匹配: 数据库中的 shop_id={product_shop_id}, 当前使用的 shop_id={shop_id}")
                                logger.warning(f"⚠️ 产品 {product_id} 可能属于不同的 shop，尝试使用数据库中的 shop_id 验证...")
                                
                                # 尝试使用数据库中的 shop_id 获取产品列表
                                try:
                                    alternative_products = await self.get_printify_products(credentials, str(product_shop_id))
                                    alternative_product_map = {}
                                    for alt_product in alternative_products:
                                        alt_product_id = alt_product.get('id')
                                        if alt_product_id:
                                            alternative_product_map[alt_product_id] = alt_product
                                    
                                    if product_id in alternative_product_map:
                                        logger.info(f"✅ 产品 {product_id} 存在于 shop {product_shop_id} 中，但不在 shop {shop_id} 中")
                                        logger.warning(f"⚠️ 建议检查外部系统配置的 shop_id 是否正确，或者产品是否需要在正确的 shop 中")
                                        # 仍然标记为错误，因为当前使用的 shop_id 不正确
                                        error_msg = f"产品 ID {product_id} 不存在于 Printify 店铺 {shop_id}（产品属于 shop {product_shop_id}）"
                                        logger.error(f"❌ {error_msg}")
                                        errors.append(error_msg)
                                        missing_products.append(product_id)
                                        continue
                                except Exception as alt_error:
                                    logger.error(f"❌ 使用替代 shop_id {product_shop_id} 验证失败: {str(alt_error)}")
                    
                    if product_id not in product_map:
                        error_msg = f"产品 ID {product_id} 不存在于 Printify 店铺 {shop_id}"
                        logger.error(f"❌ {error_msg}")
                        logger.error(f"   可用的产品 ID 列表（前20个）: {product_ids_list[:20]}")
                        errors.append(error_msg)
                        missing_products.append(product_id)
                    else:
                        # 验证变体是否存在
                        product = product_map[product_id]
                        variants = product.get('variants', [])
                        if not isinstance(variants, list):
                            variants = []
                        
                        # 记录变体信息用于调试
                        variant_ids = [str(v.get('id')) for v in variants if v and isinstance(v, dict)]
                        logger.info(f"🔍 产品 {product_id} 的变体列表: {variant_ids[:10]}")
                        logger.info(f"🔍 要验证的变体 ID: {variant_id}")
                        
                        variant_exists = any(str(v.get('id')) == str(variant_id) for v in variants if v and isinstance(v, dict))
                        
                        if not variant_exists:
                            error_msg = f"产品 {product_id} 的变体 {variant_id} 不存在（可用变体: {variant_ids[:5]}）"
                            logger.error(f"❌ {error_msg}")
                            errors.append(error_msg)
                        else:
                            logger.info(f"✅ 产品验证通过: product_id={product_id}, variant_id={variant_id}")
                except Exception as item_error:
                    logger.error(f"❌ 验证单个产品时出错: {str(item_error)}, item={item}")
                    import traceback
                    logger.error(f"   异常堆栈: {traceback.format_exc()}")
                    errors.append(f"验证产品时出错: {str(item_error)}")
            
            if errors:
                return {
                    "valid": False,
                    "errors": errors,
                    "missing_products": missing_products
                }
            else:
                logger.info(f"✅ 所有产品验证通过: {len(line_items)} 个产品")
                return {
                    "valid": True,
                    "errors": [],
                    "missing_products": []
                }
                        
        except Exception as e:
            logger.error(f"❌ 验证 Printify 产品失败: {str(e)}")
            import traceback
            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            return {
                "valid": False,
                "errors": [f"验证过程出错: {str(e)}"],
                "missing_products": []
            }

    async def _update_product_mapping_for_missing_product(self, missing_product_id: str, variant_id: int, actual_products: List[Dict], db, tenant) -> None:
        """当产品不存在时，尝试更新产品映射"""
        try:
            logger.info(f"🔍 尝试为缺失的产品更新映射: product_id={missing_product_id}")
            
            # 这里可以实现更复杂的映射逻辑
            # 比如根据产品名称、SKU等匹配实际的产品
            # 暂时只记录日志
            logger.warning(f"⚠️ 需要手动更新产品映射: missing_product_id={missing_product_id}")
            
        except Exception as e:
            logger.error(f"❌ 更新产品映射失败: {str(e)}")

    async def _update_variant_mapping_for_missing_variant(self, product_id: str, missing_variant_id: int, variants: List[Dict], db, tenant) -> None:
        """当变体不存在时，尝试更新变体映射"""
        try:
            logger.info(f"🔍 尝试为缺失的变体更新映射: product_id={product_id}, variant_id={missing_variant_id}")
            
            # 这里可以实现更复杂的映射逻辑
            # 比如根据变体属性匹配实际的变体
            # 暂时只记录日志
            logger.warning(f"⚠️ 需要手动更新变体映射: product_id={product_id}, missing_variant_id={missing_variant_id}")
            
        except Exception as e:
            logger.error(f"❌ 更新变体映射失败: {str(e)}")

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
                        # 检查 Content-Type
                        content_type = response.headers.get('Content-Type', '').lower()
                        
                        # 如果返回的是 HTML，说明可能是错误页面
                        if 'text/html' in content_type:
                            response_text = await response.text()
                            logger.error(f"❌ Printify API 返回 HTML 错误页面: status={response.status}, url={url}")
                            logger.error(f"   响应内容（前500字符）: {response_text[:500]}")
                            raise Exception(f"Printify API 返回错误页面 (status={response.status}): 可能是认证失败或端点不存在")
                        
                        # 尝试解析 JSON
                        try:
                            response_data = await response.json()
                        except Exception as json_error:
                            # 如果 JSON 解析失败，读取文本内容
                            response_text = await response.text()
                            logger.error(f"❌ Printify API 响应 JSON 解析失败: {str(json_error)}")
                            logger.error(f"   状态码: {response.status}")
                            logger.error(f"   Content-Type: {content_type}")
                            logger.error(f"   响应内容（前500字符）: {response_text[:500]}")
                            raise Exception(f"Printify API 响应解析失败 (status={response.status}): {str(json_error)}")
                        
                        # 检查状态码
                        if response.status not in [200, 201]:
                            error_msg = response_data.get('message', 'Unknown error')
                            error_code = response_data.get('code', response.status)
                            errors = response_data.get('errors', {})
                            
                            # 记录详细的错误信息
                            logger.error(f"❌ Printify API 错误: status={response.status}, code={error_code}, message={error_msg}")
                            if errors:
                                logger.error(f"   详细错误信息: {errors}")
                                # 构建更详细的错误消息
                                error_details = []
                                if isinstance(errors, dict):
                                    for key, value in errors.items():
                                        if isinstance(value, dict):
                                            error_details.append(f"{key}: {value.get('reason', value.get('message', str(value)))}")
                                        else:
                                            error_details.append(f"{key}: {value}")
                                else:
                                    error_details.append(str(errors))
                                
                                if error_details:
                                    detailed_msg = f"{error_msg}. 详细信息: {'; '.join(error_details)}"
                                else:
                                    detailed_msg = f"{error_msg}. 错误详情: {errors}"
                            else:
                                detailed_msg = error_msg
                            
                            raise Exception(f"Printify API error (status={response.status}, code={error_code}): {detailed_msg}")
                        
                        return response_data
                else:
                    async with session.get(url, headers=headers) as response:
                        # 检查 Content-Type
                        content_type = response.headers.get('Content-Type', '').lower()
                        
                        # 如果返回的是 HTML，说明可能是错误页面
                        if 'text/html' in content_type:
                            response_text = await response.text()
                            logger.error(f"❌ Printify API 返回 HTML 错误页面: status={response.status}, url={url}")
                            logger.error(f"   响应内容（前500字符）: {response_text[:500]}")
                            raise Exception(f"Printify API 返回错误页面 (status={response.status}): 可能是认证失败或端点不存在")
                        
                        # 尝试解析 JSON
                        try:
                            response_data = await response.json()
                        except Exception as json_error:
                            # 如果 JSON 解析失败，读取文本内容
                            response_text = await response.text()
                            logger.error(f"❌ Printify API 响应 JSON 解析失败: {str(json_error)}")
                            logger.error(f"   状态码: {response.status}")
                            logger.error(f"   Content-Type: {content_type}")
                            logger.error(f"   响应内容（前500字符）: {response_text[:500]}")
                            raise Exception(f"Printify API 响应解析失败 (status={response.status}): {str(json_error)}")
                        
                        # 检查状态码
                        if response.status not in [200, 201]:
                            error_msg = response_data.get('message', 'Unknown error')
                            error_code = response_data.get('code', response.status)
                            errors = response_data.get('errors', {})
                            
                            # 记录详细的错误信息
                            logger.error(f"❌ Printify API 错误: status={response.status}, code={error_code}, message={error_msg}")
                            if errors:
                                logger.error(f"   详细错误信息: {errors}")
                                # 构建更详细的错误消息
                                error_details = []
                                if isinstance(errors, dict):
                                    for key, value in errors.items():
                                        if isinstance(value, dict):
                                            error_details.append(f"{key}: {value.get('reason', value.get('message', str(value)))}")
                                        else:
                                            error_details.append(f"{key}: {value}")
                                else:
                                    error_details.append(str(errors))
                                
                                if error_details:
                                    detailed_msg = f"{error_msg}. 详细信息: {'; '.join(error_details)}"
                                else:
                                    detailed_msg = f"{error_msg}. 错误详情: {errors}"
                            else:
                                detailed_msg = error_msg
                            
                            raise Exception(f"Printify API error (status={response.status}, code={error_code}): {detailed_msg}")
                        
                        return response_data
                        
        except Exception as e:
            logger.error(f"❌ Printify API 调用失败: {str(e)}")
            raise
