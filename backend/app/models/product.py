"""
New Product System Models - Core Product Management
"""

from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text, JSON, Numeric, ForeignKey, Index, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import Enum

from app.core.database import Base


class ProductStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class Product(Base):
    """
    商品主表 - 核心系统的商品信息
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    
    # 基本信息
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    handle = Column(String(255), nullable=True)  # URL handle
    
    # 分类信息
    product_type = Column(String(100), nullable=True)  # 商品类型
    vendor = Column(String(100), nullable=True)  # 品牌/供应商
    
    # 状态信息
    status = Column(String(20), default=ProductStatus.DRAFT, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)
    
    # 媒体信息
    images = Column(JSON, nullable=True)  # 商品图片列表
    seo = Column(JSON, nullable=True)  # SEO 信息
    
    # 外部系统关联（可选）
    external_system_id = Column(Integer, ForeignKey("external_systems.id"), nullable=True)
    external_product_id = Column(String(100), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    tenant = relationship("Tenant", back_populates="products_new")
    external_system = relationship("ExternalSystem")
    dimensions = relationship("ProductDimension", back_populates="product", cascade="all, delete-orphan")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    tags = relationship("ProductTag", back_populates="product", cascade="all, delete-orphan")
    combinations = relationship("ProductCombination", back_populates="product", cascade="all, delete-orphan")
    mappings = relationship("ProductMapping", back_populates="core_product", cascade="all, delete-orphan")
    
    # PIM 新关系
    product_attributes = relationship("ProductAttribute", back_populates="product", cascade="all, delete-orphan")
    category_assignments = relationship("ProductCategoryAssignment", back_populates="product", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_products_new_tenant_status', 'tenant_id', 'status'),
        Index('idx_products_new_tenant_type', 'tenant_id', 'product_type'),
        Index('idx_products_new_tenant_vendor', 'tenant_id', 'vendor'),
        Index('idx_products_new_handle', 'tenant_id', 'handle'),
        UniqueConstraint('tenant_id', 'handle', name='uq_products_new_tenant_handle'),
    )


class ProductDimension(Base):
    """
    商品维度表 - 定义商品的可变维度
    """
    __tablename__ = "product_dimensions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    
    # 维度定义
    dimension_name = Column(String(50), nullable=False)  # 维度名称，如：color, size, material
    dimension_type = Column(String(20), nullable=False)  # 维度类型：select, text, number, boolean
    display_name = Column(String(100), nullable=True)  # 显示名称
    description = Column(Text, nullable=True)  # 维度描述
    
    # 维度配置
    options = Column(JSON, nullable=True)  # 选项列表（用于 select 类型）
    is_required = Column(Boolean, default=True, nullable=False)  # 是否必填
    display_order = Column(Integer, default=0, nullable=False)  # 显示顺序
    
    # 验证规则
    validation_rules = Column(JSON, nullable=True)  # 验证规则
    
    # 状态
    is_active = Column(Boolean, default=True, nullable=False)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    tenant = relationship("Tenant")
    product = relationship("Product", back_populates="dimensions")
    attributes = relationship("VariantAttribute", back_populates="dimension", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_product_dimensions_tenant_product', 'tenant_id', 'product_id'),
        Index('idx_product_dimensions_name', 'tenant_id', 'dimension_name'),
        UniqueConstraint('tenant_id', 'product_id', 'dimension_name', name='uq_product_dimensions_tenant_product_name'),
    )


class ProductVariant(Base):
    """
    商品变体表 - 具体的商品变体（SKU级别）
    """
    __tablename__ = "product_variants"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    
    # 变体标识
    sku = Column(String(100), nullable=True, index=True)  # SKU，租户内唯一
    barcode = Column(String(50), nullable=True, index=True)  # 主要条码
    
    # 变体属性（JSON存储，用于快速查询）
    attributes = Column(JSON, nullable=False, default=dict)  # 变体属性值
    
    # 价格信息
    price = Column(Numeric(10, 2), nullable=True)
    compare_at_price = Column(Numeric(10, 2), nullable=True)
    cost_price = Column(Numeric(10, 2), nullable=True)
    
    # 库存信息
    inventory_quantity = Column(Integer, default=0, nullable=False)
    inventory_policy = Column(String(20), default="deny", nullable=False)  # deny, continue
    tracks_inventory = Column(Boolean, default=True, nullable=False)
    
    # 状态
    is_active = Column(Boolean, default=True, nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)
    
    # 媒体
    image_url = Column(String(500), nullable=True)  # 变体图片
    
    # 物理属性
    weight = Column(Numeric(8, 2), nullable=True)  # 重量
    dimensions = Column(JSON, nullable=True)  # 尺寸信息
    
    # 外部系统关联
    external_variant_id = Column(String(100), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    tenant = relationship("Tenant")
    product = relationship("Product", back_populates="variants")
    attributes_rel = relationship("VariantAttribute", back_populates="variant", cascade="all, delete-orphan")
    barcodes = relationship("VariantBarcode", back_populates="variant", cascade="all, delete-orphan")
    
    # PIM 新关系
    variant_attributes = relationship("ProductVariantAttribute", back_populates="variant", cascade="all, delete-orphan")
    variant_dimensions = relationship("ProductVariantDimension", back_populates="variant", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_product_variants_tenant_product', 'tenant_id', 'product_id'),
        Index('idx_product_variants_tenant_sku', 'tenant_id', 'sku'),
        Index('idx_product_variants_tenant_barcode', 'tenant_id', 'barcode'),
        Index('idx_product_variants_inventory', 'tenant_id', 'inventory_quantity'),
        UniqueConstraint('tenant_id', 'sku', name='uq_product_variants_tenant_sku'),
    )


class VariantAttribute(Base):
    """
    变体属性表 - 存储变体的具体属性值
    """
    __tablename__ = "variant_attributes"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False, index=True)
    dimension_id = Column(Integer, ForeignKey("product_dimensions.id"), nullable=False, index=True)
    
    # 属性值
    value = Column(String(200), nullable=False)  # 属性值
    display_value = Column(String(200), nullable=True)  # 显示值
    
    # 排序
    sort_order = Column(Integer, default=0, nullable=False)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    tenant = relationship("Tenant")
    variant = relationship("ProductVariant", back_populates="attributes_rel")
    dimension = relationship("ProductDimension", back_populates="attributes")
    
    # 索引
    __table_args__ = (
        Index('idx_variant_attributes_tenant_variant', 'tenant_id', 'variant_id'),
        Index('idx_variant_attributes_tenant_dimension', 'tenant_id', 'dimension_id'),
        Index('idx_variant_attributes_value', 'tenant_id', 'value'),
        UniqueConstraint('tenant_id', 'variant_id', 'dimension_id', name='uq_variant_attributes_tenant_variant_dimension'),
    )


class BarcodeType(Base):
    """
    条码类型表 - 定义条码类型
    """
    __tablename__ = "barcode_types"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    
    # 条码类型信息
    name = Column(String(50), nullable=False)  # 条码类型名称，如：UPC, EAN, 门店条码, WMS条码
    display_name = Column(String(100), nullable=True)  # 显示名称
    description = Column(Text, nullable=True)  # 描述
    
    # 条码格式
    format_pattern = Column(String(100), nullable=True)  # 格式正则表达式
    length_min = Column(Integer, nullable=True)  # 最小长度
    length_max = Column(Integer, nullable=True)  # 最大长度
    
    # 外部系统关联
    external_system_id = Column(Integer, ForeignKey("external_systems.id"), nullable=True)
    
    # 状态
    is_active = Column(Boolean, default=True, nullable=False)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    tenant = relationship("Tenant")
    external_system = relationship("ExternalSystem")
    barcodes = relationship("VariantBarcode", back_populates="barcode_type", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_barcode_types_tenant_name', 'tenant_id', 'name'),
        Index('idx_barcode_types_tenant_system', 'tenant_id', 'external_system_id'),
        UniqueConstraint('tenant_id', 'name', name='uq_barcode_types_tenant_name'),
    )


class VariantBarcode(Base):
    """
    变体条码表 - 存储变体的多条码
    """
    __tablename__ = "variant_barcodes"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False, index=True)
    barcode_type_id = Column(Integer, ForeignKey("barcode_types.id"), nullable=False, index=True)
    
    # 条码信息
    barcode_value = Column(String(100), nullable=False)  # 条码值
    
    # 条码属性
    is_primary = Column(Boolean, default=False, nullable=False)  # 是否为主要条码
    is_active = Column(Boolean, default=True, nullable=False)  # 是否激活
    
    # 外部系统关联
    external_system_id = Column(Integer, ForeignKey("external_systems.id"), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    tenant = relationship("Tenant")
    variant = relationship("ProductVariant", back_populates="barcodes")
    barcode_type = relationship("BarcodeType", back_populates="barcodes")
    external_system = relationship("ExternalSystem")
    
    # 索引
    __table_args__ = (
        Index('idx_variant_barcodes_tenant_variant', 'tenant_id', 'variant_id'),
        Index('idx_variant_barcodes_tenant_type', 'tenant_id', 'barcode_type_id'),
        Index('idx_variant_barcodes_value', 'tenant_id', 'barcode_value'),
        Index('idx_variant_barcodes_primary', 'tenant_id', 'is_primary'),
        UniqueConstraint('tenant_id', 'variant_id', 'barcode_type_id', name='uq_variant_barcodes_tenant_variant_type'),
        UniqueConstraint('tenant_id', 'barcode_value', name='uq_variant_barcodes_tenant_value'),
    )


class Tag(Base):
    """
    标签表 - 系统标签定义
    """
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    
    # 标签信息
    name = Column(String(100), nullable=False)  # 标签名称
    display_name = Column(String(100), nullable=True)  # 显示名称
    description = Column(Text, nullable=True)  # 描述
    color = Column(String(7), nullable=True)  # 标签颜色（十六进制）
    
    # 标签分类
    category = Column(String(50), nullable=True)  # 标签分类：分类、属性、状态、营销等
    
    # 状态
    is_active = Column(Boolean, default=True, nullable=False)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    tenant = relationship("Tenant")
    product_tags = relationship("ProductTag", back_populates="tag", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_tags_tenant_name', 'tenant_id', 'name'),
        Index('idx_tags_tenant_category', 'tenant_id', 'category'),
        UniqueConstraint('tenant_id', 'name', name='uq_tags_tenant_name'),
    )


class ProductTag(Base):
    """
    商品标签关联表 - 商品与标签的多对多关系
    """
    __tablename__ = "product_tags"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    tag_id = Column(Integer, ForeignKey("tags.id"), nullable=False, index=True)
    
    # 标签属性
    is_primary = Column(Boolean, default=False, nullable=False)  # 是否为主要标签
    sort_order = Column(Integer, default=0, nullable=False)  # 排序
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    tenant = relationship("Tenant")
    product = relationship("Product", back_populates="tags")
    tag = relationship("Tag", back_populates="product_tags")
    
    # 索引
    __table_args__ = (
        Index('idx_product_tags_tenant_product', 'tenant_id', 'product_id'),
        Index('idx_product_tags_tenant_tag', 'tenant_id', 'tag_id'),
        Index('idx_product_tags_primary', 'tenant_id', 'is_primary'),
        UniqueConstraint('tenant_id', 'product_id', 'tag_id', name='uq_product_tags_tenant_product_tag'),
    )


class ProductCombination(Base):
    """
    商品组合表 - 商品组合关系
    """
    __tablename__ = "product_combinations"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    
    # 组合信息
    combination_name = Column(String(255), nullable=False)  # 组合名称
    description = Column(Text, nullable=True)  # 组合描述
    
    # 组合类型
    combination_type = Column(String(50), nullable=False)  # 组合类型：fixed, optional, recommended
    
    # 价格策略
    price_strategy = Column(String(50), nullable=False, default="sum")  # 价格策略：sum, fixed, discount
    combination_price = Column(Numeric(10, 2), nullable=True)  # 组合价格
    discount_percentage = Column(Numeric(5, 2), nullable=True)  # 折扣百分比
    
    # 库存策略
    inventory_policy = Column(String(50), nullable=False, default="check_all")  # 库存策略：check_all, check_any
    
    # 状态
    is_active = Column(Boolean, default=True, nullable=False)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    tenant = relationship("Tenant")
    product = relationship("Product", back_populates="combinations")
    items = relationship("ProductCombinationItem", back_populates="combination", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_product_combinations_tenant_product', 'tenant_id', 'product_id'),
        Index('idx_product_combinations_tenant_type', 'tenant_id', 'combination_type'),
    )


class ProductCombinationItem(Base):
    """
    商品组合项表 - 组合中的具体商品
    """
    __tablename__ = "product_combination_items"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    combination_id = Column(Integer, ForeignKey("product_combinations.id"), nullable=False, index=True)
    
    # 组合商品信息
    item_product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    item_variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True, index=True)
    
    # 数量信息
    quantity_min = Column(Integer, default=1, nullable=False)  # 最小数量
    quantity_max = Column(Integer, nullable=True)  # 最大数量
    quantity_default = Column(Integer, default=1, nullable=False)  # 默认数量
    
    # 是否必选
    is_required = Column(Boolean, default=True, nullable=False)  # 是否必选
    
    # 排序
    sort_order = Column(Integer, default=0, nullable=False)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    tenant = relationship("Tenant")
    combination = relationship("ProductCombination", back_populates="items")
    item_product = relationship("Product", foreign_keys=[item_product_id])
    item_variant = relationship("ProductVariant", foreign_keys=[item_variant_id])
    
    # 索引
    __table_args__ = (
        Index('idx_product_combination_items_tenant_combination', 'tenant_id', 'combination_id'),
        Index('idx_product_combination_items_tenant_product', 'tenant_id', 'item_product_id'),
        Index('idx_product_combination_items_tenant_variant', 'tenant_id', 'item_variant_id'),
    )


class ProductMapping(Base):
    """
    商品映射表 - 核心商品与外部系统商品的映射关系
    """
    __tablename__ = "product_mappings"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    
    # 核心商品
    core_product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    core_variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True, index=True)
    
    # 外部系统
    external_system_id = Column(Integer, ForeignKey("external_systems.id"), nullable=False, index=True)
    external_product_id = Column(String(100), nullable=False, index=True)  # 外部系统商品ID
    external_variant_id = Column(String(100), nullable=True, index=True)  # 外部系统变体ID
    
    # 映射信息
    mapping_type = Column(String(50), nullable=False)  # 映射类型：sync, manual, auto
    sync_direction = Column(String(20), nullable=False, default="bidirectional")  # 同步方向：to_external, from_external, bidirectional
    
    # 同步状态
    sync_status = Column(String(20), nullable=False, default="pending")  # 同步状态：pending, synced, failed, conflict
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    sync_error = Column(Text, nullable=True)  # 同步错误信息
    
    # 映射配置
    sync_config = Column(JSON, nullable=True)  # 同步配置
    field_mappings = Column(JSON, nullable=True)  # 字段映射配置
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    tenant = relationship("Tenant")
    core_product = relationship("Product", back_populates="mappings")
    core_variant = relationship("ProductVariant")
    external_system = relationship("ExternalSystem")
    
    # 索引
    __table_args__ = (
        Index('idx_product_mappings_tenant_core', 'tenant_id', 'core_product_id'),
        Index('idx_product_mappings_tenant_external', 'tenant_id', 'external_system_id'),
        Index('idx_product_mappings_tenant_sync', 'tenant_id', 'sync_status'),
        Index('idx_product_mappings_external_product', 'tenant_id', 'external_system_id', 'external_product_id'),
        UniqueConstraint('tenant_id', 'core_product_id', 'external_system_id', name='uq_product_mappings_tenant_core_external'),
    )


class ExternalProduct(Base):
    """
    外部商品表 - 存储外部系统的商品数据
    """
    __tablename__ = "external_products"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    external_system_id = Column(Integer, ForeignKey("external_systems.id"), nullable=False, index=True)
    
    # 外部系统商品标识
    external_product_id = Column(String(100), nullable=False, index=True)  # 外部系统商品ID
    external_variant_id = Column(String(100), nullable=True, index=True)  # 外部系统变体ID
    
    # 商品基本信息
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    handle = Column(String(255), nullable=True)
    
    # 商品状态
    status = Column(String(50), nullable=True)  # 外部系统状态
    is_active = Column(Boolean, default=True, nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)
    
    # 价格信息
    price = Column(Numeric(10, 2), nullable=True)
    compare_at_price = Column(Numeric(10, 2), nullable=True)
    cost_price = Column(Numeric(10, 2), nullable=True)
    
    # 库存信息
    inventory_quantity = Column(Integer, nullable=True)
    inventory_policy = Column(String(20), nullable=True)
    
    # 商品属性
    product_type = Column(String(100), nullable=True)
    vendor = Column(String(100), nullable=True)
    tags = Column(JSON, nullable=True)  # 标签列表
    images = Column(JSON, nullable=True)  # 图片列表
    variants = Column(JSON, nullable=True)  # 变体信息
    
    # 外部系统特定数据
    external_data = Column(JSON, nullable=True)  # 外部系统原始数据
    
    # 同步信息
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    sync_status = Column(String(20), nullable=False, default="pending")
    sync_error = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    tenant = relationship("Tenant")
    external_system = relationship("ExternalSystem")
    
    # 索引
    __table_args__ = (
        Index('idx_external_products_tenant_system', 'tenant_id', 'external_system_id'),
        Index('idx_external_products_tenant_product', 'tenant_id', 'external_product_id'),
        Index('idx_external_products_tenant_variant', 'tenant_id', 'external_variant_id'),
        Index('idx_external_products_tenant_status', 'tenant_id', 'status'),
        Index('idx_external_products_tenant_sync', 'tenant_id', 'sync_status'),
        UniqueConstraint('tenant_id', 'external_system_id', 'external_product_id', 'external_variant_id', name='uq_external_products_tenant_system_product_variant'),
    )
