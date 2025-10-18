"""
Product Category Models
支持 DAG 分类体系的数据库模型
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint, Index, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.base import AuditMixin, TenantMixin


class ProductCategory(Base, AuditMixin, TenantMixin):
    """产品分类表（DAG 节点）"""
    __tablename__ = "product_categories"

    id = Column(Integer, primary_key=True, index=True)
    category_code = Column(String(50), nullable=False)
    category_name = Column(String(200), nullable=False)
    description = Column(Text)
    is_root = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    # 审计字段由 AuditMixin 和 TenantMixin 提供

    # 关系
    parent_relations = relationship("ProductCategoryRelation", foreign_keys="ProductCategoryRelation.child_category_id", back_populates="child_category")
    child_relations = relationship("ProductCategoryRelation", foreign_keys="ProductCategoryRelation.parent_category_id", back_populates="parent_category")
    category_dimensions = relationship("ProductCategoryDimension", foreign_keys="ProductCategoryDimension.category_id", back_populates="category")
    category_assignments = relationship("ProductCategoryAssignment", back_populates="category")

    # 约束
    __table_args__ = (
        UniqueConstraint("tenant_id", "category_code", name="uq_category_tenant_code"),
        Index("ix_categories_tenant_active", "tenant_id", "is_active"),
    )


class ProductCategoryRelation(Base, AuditMixin):
    """分类关系表（DAG 边）"""
    __tablename__ = "product_category_relations"

    id = Column(Integer, primary_key=True, index=True)
    parent_category_id = Column(Integer, ForeignKey("product_categories.id"), nullable=False, index=True)
    child_category_id = Column(Integer, ForeignKey("product_categories.id"), nullable=False, index=True)
    relation_type = Column(String(20), default="parent_child")
    sort_order = Column(Integer, default=0)
    # 审计字段由 AuditMixin 提供

    # 关系
    parent_category = relationship("ProductCategory", foreign_keys=[parent_category_id], back_populates="child_relations")
    child_category = relationship("ProductCategory", foreign_keys=[child_category_id], back_populates="parent_relations")

    # 约束
    __table_args__ = (
        UniqueConstraint("parent_category_id", "child_category_id", name="uq_category_relation_parent_child"),
        CheckConstraint("parent_category_id != child_category_id", name="ck_category_relation_no_self"),
        Index("ix_category_relations_parent", "parent_category_id"),
        Index("ix_category_relations_child", "child_category_id"),
    )


class ProductCategoryDimension(Base, AuditMixin):
    """分类维度关联表"""
    __tablename__ = "product_category_dimensions"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("product_categories.id"), nullable=False, index=True)
    dimension_template_id = Column(Integer, ForeignKey("product_dimension_templates.id"), nullable=False, index=True)
    source_type = Column(String(20), nullable=False)  # own, inherited, overridden
    source_category_id = Column(Integer, ForeignKey("product_categories.id"))
    is_required = Column(Boolean, default=True)
    is_overridable = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    # 审计字段由 AuditMixin 提供

    # 关系
    category = relationship("ProductCategory", foreign_keys=[category_id], back_populates="category_dimensions")
    dimension_template = relationship("ProductDimensionTemplate", back_populates="category_dimensions")
    source_category = relationship("ProductCategory", foreign_keys=[source_category_id], overlaps="category_dimensions")
    dimension_values = relationship("ProductDimensionValue", back_populates="category_dimension")

    # 约束
    __table_args__ = (
        UniqueConstraint("category_id", "dimension_template_id", name="uq_category_dimension_category_template"),
        Index("ix_category_dimensions_category", "category_id"),
        Index("ix_category_dimensions_template", "dimension_template_id"),
    )


class ProductCategoryAssignment(Base, AuditMixin):
    """产品分类归属表"""
    __tablename__ = "product_category_assignments"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("product_categories.id"), nullable=False, index=True)
    is_primary = Column(Boolean, default=False)
    # 审计字段由 AuditMixin 提供

    # 关系
    product = relationship("Product", back_populates="category_assignments")
    category = relationship("ProductCategory", back_populates="category_assignments")

    # 约束
    __table_args__ = (
        UniqueConstraint("product_id", "category_id", name="uq_category_assignment_product_category"),
        Index("ix_category_assignments_product", "product_id"),
        Index("ix_category_assignments_category", "category_id"),
        Index("ix_category_assignments_primary", "is_primary"),
    )
