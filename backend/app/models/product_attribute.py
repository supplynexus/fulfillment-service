"""
Product Attribute Models
支持结构化属性管理的数据库模型
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class ProductAttribute(Base):
    """产品属性表"""
    __tablename__ = "product_attributes"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    attribute_key = Column(String(100), nullable=False)
    attribute_value = Column(Text)
    attribute_type = Column(String(20), default="string")  # string, number, boolean, date, json
    display_name = Column(String(200))
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    product = relationship("Product", back_populates="product_attributes")

    # 约束
    __table_args__ = (
        UniqueConstraint("product_id", "attribute_key", name="uq_product_attribute_product_key"),
        Index("ix_product_attributes_product", "product_id"),
        Index("ix_product_attributes_key", "attribute_key"),
    )


class ProductVariantAttribute(Base):
    """SKU 属性表"""
    __tablename__ = "product_variant_attributes"

    id = Column(Integer, primary_key=True, index=True)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False, index=True)
    attribute_key = Column(String(100), nullable=False)
    attribute_value = Column(Text)
    attribute_type = Column(String(20), default="string")  # string, number, boolean, date, json
    display_name = Column(String(200))
    migrated_from_dimension = Column(Boolean, default=False)  # 是否从维度迁移而来
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    variant = relationship("ProductVariant", back_populates="variant_attributes")

    # 约束
    __table_args__ = (
        UniqueConstraint("variant_id", "attribute_key", name="uq_variant_attribute_variant_key"),
        Index("ix_variant_attributes_variant", "variant_id"),
        Index("ix_variant_attributes_key", "attribute_key"),
        Index("ix_variant_attributes_migrated", "migrated_from_dimension"),
    )
