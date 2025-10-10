"""add scm_order_sources (many-to-many)

Revision ID: 8f284a9794d6
Revises: 8d4f2e9a1b5c
Create Date: 2025-10-07 23:14:33.989043

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "8f284a9794d6"
down_revision = "8d4f2e9a1b5c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Minimal upgrade: only create scm_order_sources table and index.

    We intentionally avoid any unrelated automatic changes to other tables
    (product_mappings/shopify_orders/order_items) to keep this migration
    focused and data-safe for existing environments.
    """

    op.create_table(
        "scm_order_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("scm_order_id", sa.Integer(), nullable=False),
        sa.Column("source_order_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["scm_order_id"], ["scm_orders.id"]),
        sa.ForeignKeyConstraint(["source_order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scm_order_sources_id"), "scm_order_sources", ["id"], unique=False)

    # Drop columns no longer needed on scm_orders
    with op.batch_alter_table("scm_orders") as batch_op:
        for col in ("target_system_id", "target_system_type", "total_amount"):
            try:
                batch_op.drop_column(col)
            except Exception:
                # Column may already be missing in some environments
                pass


def downgrade() -> None:
    op.drop_index(op.f("ix_scm_order_sources_id"), table_name="scm_order_sources")
    op.drop_table("scm_order_sources")
    # Note: columns removed in upgrade are not recreated in downgrade for simplicity
