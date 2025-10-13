"""
Product Dimension Models
支持产品维度管理的数据库模型
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class ProductDimensionTemplate(Base):
    """产品维度模板表"""
    __tablename__ = "product_dimension_templates"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    dimension_code = Column(String(50), nullable=False)
    dimension_name = Column(String(200), nullable=False)
    dimension_type = Column(String(20), default="select")
    description = Column(Text)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    category_dimensions = relationship("ProductCategoryDimension", back_populates="dimension_template")
    variant_dimensions = relationship("ProductVariantDimension", back_populates="dimension_template")

    # 约束
    __table_args__ = (
        UniqueConstraint("tenant_id", "dimension_code", name="uq_dimension_template_tenant_code"),
        Index("ix_dimension_templates_tenant_active", "tenant_id", "is_active"),
    )


class ProductDimensionValue(Base):
    """产品维度值表"""
    __tablename__ = "product_dimension_values"

    id = Column(Integer, primary_key=True, index=True)
    category_dimension_id = Column(Integer, ForeignKey("product_category_dimensions.id"), nullable=False, index=True)
    value_code = Column(String(50), nullable=False)
    value_name = Column(String(200), nullable=False)
    value_type = Column(String(20), default="normal")  # normal, default, not_applicable
    is_default = Column(Boolean, default=False)
    review_status = Column(String(20), default="approved")  # approved, pending, rejected
    merged_to_value_id = Column(Integer, ForeignKey("product_dimension_values.id"))
    created_by = Column(Integer, ForeignKey("users.id"))
    approved_by = Column(Integer, ForeignKey("users.id"))
    approved_at = Column(DateTime(timezone=True))
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    category_dimension = relationship("ProductCategoryDimension", back_populates="dimension_values")
    merged_to_value = relationship("ProductDimensionValue", remote_side=[id])
    variant_dimensions = relationship("ProductVariantDimension", back_populates="dimension_value")

    # 约束
    __table_args__ = (
        UniqueConstraint("category_dimension_id", "value_code", name="uq_dimension_value_category_code"),
        Index("ix_dimension_values_category", "category_dimension_id"),
        Index("ix_dimension_values_status", "review_status"),
    )


class ProductVariantDimension(Base):
    """SKU 维度值关联表"""
    __tablename__ = "product_variant_dimensions"

    id = Column(Integer, primary_key=True, index=True)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False, index=True)
    dimension_template_id = Column(Integer, ForeignKey("product_dimension_templates.id"), nullable=False, index=True)
    dimension_value_id = Column(Integer, ForeignKey("product_dimension_values.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    variant = relationship("ProductVariant", back_populates="variant_dimensions")
    dimension_template = relationship("ProductDimensionTemplate", back_populates="variant_dimensions")
    dimension_value = relationship("ProductDimensionValue", back_populates="variant_dimensions")

    # 约束
    __table_args__ = (
        UniqueConstraint("variant_id", "dimension_template_id", name="uq_variant_dimension_variant_template"),
        Index("ix_variant_dimensions_variant", "variant_id"),
        Index("ix_variant_dimensions_template", "dimension_template_id"),
        Index("ix_variant_dimensions_value", "dimension_value_id"),
    )
