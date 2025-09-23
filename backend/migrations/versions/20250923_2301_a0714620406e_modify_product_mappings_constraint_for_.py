"""modify_product_mappings_constraint_for_variant_level_mappings

Revision ID: a0714620406e
Revises: 61f7bbff7894
Create Date: 2025-09-23 23:01:35.640655

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a0714620406e"
down_revision = "61f7bbff7894"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    修改 product_mappings 表的唯一约束，从商品级别映射改为变体级别映射
    """
    # 1. 删除现有的唯一约束
    op.drop_constraint(
        'uq_product_mappings_tenant_core_external',
        'product_mappings',
        type_='unique'
    )
    
    # 2. 创建新的唯一约束，允许每个变体有自己的映射
    op.create_unique_constraint(
        'uq_product_mappings_tenant_variant_external',
        'product_mappings',
        ['tenant_id', 'core_variant_id', 'external_system_id']
    )


def downgrade() -> None:
    """
    回滚约束修改
    """
    # 1. 删除新的唯一约束
    op.drop_constraint(
        'uq_product_mappings_tenant_variant_external',
        'product_mappings',
        type_='unique'
    )
    
    # 2. 恢复原来的唯一约束
    op.create_unique_constraint(
        'uq_product_mappings_tenant_core_external',
        'product_mappings',
        ['tenant_id', 'core_product_id', 'external_system_id']
    )
