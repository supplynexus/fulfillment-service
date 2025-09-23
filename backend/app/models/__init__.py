"""
Database models package
"""

from .user import User
from .tenant import Tenant
from .user_tenant import UserTenant, UserRole
from .customer import Customer
from .supplier import Supplier
from .external_system import ExternalSystem, ExternalSystemType
from .external_data import ExternalData, ExternalDataType
from .order import Order, OrderStatus
# from .product import Product  # 已替换为新的商品系统
from .product_new import (
    Product,
    ProductDimension,
    ProductVariant,
    VariantAttribute,
    BarcodeType,
    VariantBarcode,
    Tag,
    ProductTag,
    ProductCombination,
    ProductCombinationItem,
    ProductMapping,
    ExternalProduct,
    ProductStatus
)
from .scm_order import SCMOrder, SCMOrderStatus, RoutingRule, RoutingStatus

from .jwt_blacklist import JwtBlacklist


from .sync_config import SyncConfig, SyncJob, SyncType, SyncFrequency, SyncJobStatus

__all__ = [
    "User",
    "Tenant",
    "UserTenant", 
    "UserRole",
    "Customer",
    "Supplier",
    "ExternalSystem",
    "ExternalSystemType",
    "ExternalData",
    "ExternalDataType",
    "Order",
    "OrderStatus",
    "Product",
    "ProductDimension",
    "ProductVariant", 
    "VariantAttribute",
    "BarcodeType",
    "VariantBarcode",
    "Tag",
    "ProductTag",
    "ProductCombination",
    "ProductCombinationItem",
    "ProductMapping",
    "ExternalProduct",
    "ProductStatus",
    "SCMOrder",
    "SCMOrderStatus",
    "RoutingRule",
    "RoutingStatus",

    "JwtBlacklist",


    "SyncConfig",
    "SyncJob", 
    "SyncType",
    "SyncFrequency",
    "SyncJobStatus"
]
