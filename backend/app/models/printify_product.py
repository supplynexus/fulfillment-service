"""
Printify Product Model
专门存储 Printify 商品数据，贴近 Printify API 结构
参考: https://developers.printify.com/#products
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, Numeric, DateTime, ForeignKey, JSON, Index, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class PrintifyProduct(Base):
    """
    Printify 商品表
    专门存储 Printify 商品数据，贴近 Printify API 结构
    参考: https://developers.printify.com/#products
    """
    __tablename__ = "printify_products"

    # 主键和租户
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    external_system_id = Column(Integer, ForeignKey("external_systems.id"), nullable=False, index=True)
    
    # Printify 商品标识
    printify_product_id = Column(String(100), nullable=False, index=True)  # Printify 商品 ID
    printify_shop_id = Column(String(100), nullable=True, index=True)  # Printify 店铺 ID
    
    # 基本信息
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)  # 标签数组
    
    # 商品状态
    visible = Column(Boolean, nullable=False, default=True)  # 是否可见
    is_locked = Column(Boolean, nullable=False, default=False)  # 是否锁定
    is_published = Column(Boolean, nullable=False, default=True)  # 是否已发布到销售渠道（sales_channel_properties 非空），用于列表筛选
    
    # 外部系统信息
    external = Column(JSON, nullable=True)  # 外部系统信息 {id, handle, sku}
    user_id = Column(Integer, nullable=True)  # Printify 用户 ID
    print_provider_id = Column(Integer, nullable=True)  # 打印提供商 ID
    
    # 商品选项 (Printify 特有的选项系统)
    options = Column(JSON, nullable=True)  # 商品选项数组
    
    # 变体信息 (JSON 存储，因为 Printify 变体结构复杂)
    variants = Column(JSON, nullable=True)  # 变体数组
    
    # 图片信息
    images = Column(JSON, nullable=True)  # 图片数组
    
    # 打印区域信息
    print_areas = Column(JSON, nullable=True)  # 打印区域数组
    
    # 原始数据
    raw_data = Column(JSON, nullable=True)  # 完整的 Printify 原始数据
    
    # 同步信息
    last_synced_at = Column(DateTime(timezone=True), nullable=True)  # 最后同步时间
    sync_status = Column(String(20), nullable=False, default="pending")  # 同步状态
    sync_error = Column(Text, nullable=True)  # 同步错误信息
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # 关系
    tenant = relationship("Tenant")
    external_system = relationship("ExternalSystem")
    
    # 索引和约束
    __table_args__ = (
        # 唯一约束：租户 + 外部系统 + Printify 商品 ID
        UniqueConstraint('tenant_id', 'external_system_id', 'printify_product_id', name='uq_printify_products_tenant_system_product'),
        
        # 索引
        Index('idx_printify_products_tenant_id', 'tenant_id'),
        Index('idx_printify_products_external_system_id', 'external_system_id'),
        Index('idx_printify_products_printify_product_id', 'printify_product_id'),
        Index('idx_printify_products_printify_shop_id', 'printify_shop_id'),
        Index('idx_printify_products_visible', 'visible'),
        Index('idx_printify_products_is_published', 'is_published'),
        Index('idx_printify_products_sync_status', 'sync_status'),
        Index('idx_printify_products_created_at', 'created_at'),
        Index('idx_printify_products_tenant_system_product', 'tenant_id', 'external_system_id', 'printify_product_id'),
    )
    
    def __repr__(self):
        return f"<PrintifyProduct(id={self.id}, printify_product_id='{self.printify_product_id}', title='{self.title}')>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'external_system_id': self.external_system_id,
            'printify_product_id': self.printify_product_id,
            'printify_shop_id': self.printify_shop_id,
            'title': self.title,
            'description': self.description,
            'tags': self.tags,
            'visible': self.visible,
            'is_locked': self.is_locked,
            'is_published': self.is_published,
            'external': self.external,
            'user_id': self.user_id,
            'print_provider_id': self.print_provider_id,
            'options': self.options,
            'variants': self.variants,
            'images': self.images,
            'print_areas': self.print_areas,
            'raw_data': self.raw_data,
            'last_synced_at': self.last_synced_at.isoformat() if self.last_synced_at else None,
            'sync_status': self.sync_status,
            'sync_error': self.sync_error,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class PrintifyVariant(Base):
    """
    Printify 变体表
    存储 Printify 商品的变体信息
    """
    __tablename__ = "printify_variants"

    # 主键和租户
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    printify_product_id = Column(Integer, ForeignKey("printify_products.id"), nullable=False, index=True)
    
    # Printify 变体标识
    printify_variant_id = Column(Integer, nullable=False, index=True)  # Printify 变体 ID
    
    # 变体基本信息
    sku = Column(String(100), nullable=True, index=True)
    title = Column(String(255), nullable=True)
    
    # 价格信息
    cost = Column(Numeric(10, 2), nullable=True)  # 成本价
    price = Column(Numeric(10, 2), nullable=True)  # 售价
    
    # 物理属性
    grams = Column(Integer, nullable=True)  # 重量（克）
    
    # 变体状态
    is_enabled = Column(Boolean, nullable=False, default=True)
    is_default = Column(Boolean, nullable=False, default=False)
    is_available = Column(Boolean, nullable=False, default=True)
    
    # 选项关联
    options = Column(JSON, nullable=True)  # 关联的选项 ID 数组
    
    # 原始数据
    raw_data = Column(JSON, nullable=True)  # 变体原始数据
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # 关系
    tenant = relationship("Tenant")
    printify_product = relationship("PrintifyProduct")
    
    # 索引和约束
    __table_args__ = (
        # 唯一约束：租户 + Printify 商品 + Printify 变体 ID
        UniqueConstraint('tenant_id', 'printify_product_id', 'printify_variant_id', name='uq_printify_variants_tenant_product_variant'),
        
        # 索引
        Index('idx_printify_variants_tenant_id', 'tenant_id'),
        Index('idx_printify_variants_printify_product_id', 'printify_product_id'),
        Index('idx_printify_variants_printify_variant_id', 'printify_variant_id'),
        Index('idx_printify_variants_sku', 'sku'),
        Index('idx_printify_variants_is_enabled', 'is_enabled'),
        Index('idx_printify_variants_is_default', 'is_default'),
        Index('idx_printify_variants_tenant_product_variant', 'tenant_id', 'printify_product_id', 'printify_variant_id'),
    )
    
    def __repr__(self):
        return f"<PrintifyVariant(id={self.id}, printify_variant_id={self.printify_variant_id}, sku='{self.sku}')>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'printify_product_id': self.printify_product_id,
            'printify_variant_id': self.printify_variant_id,
            'sku': self.sku,
            'title': self.title,
            'cost': float(self.cost) if self.cost else None,
            'price': float(self.price) if self.price else None,
            'grams': self.grams,
            'is_enabled': self.is_enabled,
            'is_default': self.is_default,
            'is_available': self.is_available,
            'options': self.options,
            'raw_data': self.raw_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }



