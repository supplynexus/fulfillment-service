"""Add is_published to printify_products

Revision ID: a1b2c3d4e5f6
Revises: 4f3b1b2a9c10
Create Date: 2026-02-08

"""
from alembic import op
import sqlalchemy as sa


revision = "f6e5d4c3b2a1"
down_revision = "4f3b1b2a9c10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "printify_products",
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index(
        "idx_printify_products_is_published",
        "printify_products",
        ["is_published"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_printify_products_is_published", table_name="printify_products")
    op.drop_column("printify_products", "is_published")
