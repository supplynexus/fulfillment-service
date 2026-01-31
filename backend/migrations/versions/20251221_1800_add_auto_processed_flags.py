"""add_auto_processed_flags

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2025-12-21 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d2e3f4a5b6c7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add auto processed flags to prevent duplicate processing."""
    # Add flags to shopify_orders table
    op.add_column(
        "shopify_orders",
        sa.Column("auto_synced_to_core", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index(
        "idx_shopify_orders_auto_synced_to_core",
        "shopify_orders",
        ["auto_synced_to_core"],
        unique=False,
    )
    
    op.add_column(
        "shopify_orders",
        sa.Column("auto_synced_fulfillment_from_api", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index(
        "idx_shopify_orders_auto_synced_fulfillment_from_api",
        "shopify_orders",
        ["auto_synced_fulfillment_from_api"],
        unique=False,
    )
    
    op.add_column(
        "shopify_orders",
        sa.Column("auto_synced_fulfillment_to_core", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index(
        "idx_shopify_orders_auto_synced_fulfillment_to_core",
        "shopify_orders",
        ["auto_synced_fulfillment_to_core"],
        unique=False,
    )
    
    # Add flags to orders table
    op.add_column(
        "orders",
        sa.Column("auto_routed_to_scm", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index(
        "idx_orders_auto_routed_to_scm",
        "orders",
        ["auto_routed_to_scm"],
        unique=False,
    )
    
    # Add flags to scm_orders table
    op.add_column(
        "scm_orders",
        sa.Column("auto_created_printify_order", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index(
        "idx_scm_orders_auto_created_printify_order",
        "scm_orders",
        ["auto_created_printify_order"],
        unique=False,
    )
    
    op.add_column(
        "scm_orders",
        sa.Column("auto_synced_fulfillment_from_printify", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index(
        "idx_scm_orders_auto_synced_fulfillment_from_printify",
        "scm_orders",
        ["auto_synced_fulfillment_from_printify"],
        unique=False,
    )
    
    op.add_column(
        "scm_orders",
        sa.Column("auto_synced_fulfillment_to_shopify", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index(
        "idx_scm_orders_auto_synced_fulfillment_to_shopify",
        "scm_orders",
        ["auto_synced_fulfillment_to_shopify"],
        unique=False,
    )
    
    # Add flags to printify_orders table
    op.add_column(
        "printify_orders",
        sa.Column("auto_synced_from_api", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index(
        "idx_printify_orders_auto_synced_from_api",
        "printify_orders",
        ["auto_synced_from_api"],
        unique=False,
    )
    
    op.add_column(
        "printify_orders",
        sa.Column("auto_synced_fulfillment_to_scm", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index(
        "idx_printify_orders_auto_synced_fulfillment_to_scm",
        "printify_orders",
        ["auto_synced_fulfillment_to_scm"],
        unique=False,
    )


def downgrade() -> None:
    """Remove auto processed flags."""
    # Remove indexes and columns from printify_orders
    op.drop_index("idx_printify_orders_auto_synced_fulfillment_to_scm", table_name="printify_orders")
    op.drop_column("printify_orders", "auto_synced_fulfillment_to_scm")
    op.drop_index("idx_printify_orders_auto_synced_from_api", table_name="printify_orders")
    op.drop_column("printify_orders", "auto_synced_from_api")
    
    # Remove indexes and columns from scm_orders
    op.drop_index("idx_scm_orders_auto_synced_fulfillment_to_shopify", table_name="scm_orders")
    op.drop_column("scm_orders", "auto_synced_fulfillment_to_shopify")
    op.drop_index("idx_scm_orders_auto_synced_fulfillment_from_printify", table_name="scm_orders")
    op.drop_column("scm_orders", "auto_synced_fulfillment_from_printify")
    op.drop_index("idx_scm_orders_auto_created_printify_order", table_name="scm_orders")
    op.drop_column("scm_orders", "auto_created_printify_order")
    
    # Remove indexes and columns from orders
    op.drop_index("idx_orders_auto_routed_to_scm", table_name="orders")
    op.drop_column("orders", "auto_routed_to_scm")
    
    # Remove indexes and columns from shopify_orders
    op.drop_index("idx_shopify_orders_auto_synced_fulfillment_to_core", table_name="shopify_orders")
    op.drop_column("shopify_orders", "auto_synced_fulfillment_to_core")
    op.drop_index("idx_shopify_orders_auto_synced_fulfillment_from_api", table_name="shopify_orders")
    op.drop_column("shopify_orders", "auto_synced_fulfillment_from_api")
    op.drop_index("idx_shopify_orders_auto_synced_to_core", table_name="shopify_orders")
    op.drop_column("shopify_orders", "auto_synced_to_core")
