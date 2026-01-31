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
    # No-op upgrade: Constraint changes have already been applied
    pass


def downgrade() -> None:
    """
    回滚约束修改
    """
    # No-op downgrade: Constraint changes are not reversible due to database state
    pass
