"""Add order integration fields for Shopify and Printify

Revision ID: f154935d6d1f
Revises: 7beb7b99f65f
Create Date: 2025-09-27 11:21:58.060254

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f154935d6d1f"
down_revision = "7beb7b99f65f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """添加订单集成字段"""

    # 检查并添加 orders 表的 Shopify 集成字段
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    # 检查 orders 表是否存在这些字段
    orders_columns = [col["name"] for col in inspector.get_columns("orders")]

    if "shopify_order_id" not in orders_columns:
        op.add_column(
            "orders", sa.Column("shopify_order_id", sa.String(), nullable=True)
        )

    if "shopify_fulfillment_order_id" not in orders_columns:
        op.add_column(
            "orders",
            sa.Column("shopify_fulfillment_order_id", sa.String(), nullable=True),
        )

    if "shopify_fulfillment_id" not in orders_columns:
        op.add_column(
            "orders", sa.Column("shopify_fulfillment_id", sa.String(), nullable=True)
        )

    # 检查并添加 scm_orders 表的集成字段
    scm_orders_columns = [col["name"] for col in inspector.get_columns("scm_orders")]

    if "shopify_order_id" not in scm_orders_columns:
        op.add_column(
            "scm_orders", sa.Column("shopify_order_id", sa.String(), nullable=True)
        )

    if "printify_order_id" not in scm_orders_columns:
        op.add_column(
            "scm_orders", sa.Column("printify_order_id", sa.String(), nullable=True)
        )

    if "printify_shop_id" not in scm_orders_columns:
        op.add_column(
            "scm_orders", sa.Column("printify_shop_id", sa.String(), nullable=True)
        )

    # 检查并添加索引
    existing_indexes = [idx["name"] for idx in inspector.get_indexes("orders")]
    if "ix_orders_shopify_order_id" not in existing_indexes:
        op.create_index("ix_orders_shopify_order_id", "orders", ["shopify_order_id"])

    existing_scm_indexes = [idx["name"] for idx in inspector.get_indexes("scm_orders")]
    if "ix_scm_orders_shopify_order_id" not in existing_scm_indexes:
        op.create_index(
            "ix_scm_orders_shopify_order_id", "scm_orders", ["shopify_order_id"]
        )

    if "ix_scm_orders_printify_order_id" not in existing_scm_indexes:
        op.create_index(
            "ix_scm_orders_printify_order_id", "scm_orders", ["printify_order_id"]
        )


def downgrade() -> None:
    """回滚订单集成字段"""

    # 删除索引
    op.drop_index("ix_scm_orders_printify_order_id", table_name="scm_orders")
    op.drop_index("ix_scm_orders_shopify_order_id", table_name="scm_orders")
    op.drop_index("ix_orders_shopify_order_id", table_name="orders")

    # 删除 scm_orders 表的字段
    op.drop_column("scm_orders", "printify_shop_id")
    op.drop_column("scm_orders", "printify_order_id")
    op.drop_column("scm_orders", "shopify_order_id")

    # 删除 orders 表的字段
    op.drop_column("orders", "shopify_fulfillment_id")
    op.drop_column("orders", "shopify_fulfillment_order_id")
    op.drop_column("orders", "shopify_order_id")
