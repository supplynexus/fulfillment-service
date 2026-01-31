"""create_shopify_orders_table

Revision ID: 7b65121bc355
Revises: f154935d6d1f
Create Date: 2025-09-27 23:43:42.476774

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7b65121bc355"
down_revision = "f154935d6d1f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create shopify_orders table
    op.create_table(
        'shopify_orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('shopify_order_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(50), nullable=True),
        sa.Column('confirmation_number', sa.String(50), nullable=True),
        sa.Column('financial_status', sa.String(50), nullable=True),
        sa.Column('fulfillment_status', sa.String(50), nullable=True),
        sa.Column('confirmed', sa.Boolean(), nullable=False, default=False),
        sa.Column('closed', sa.Boolean(), nullable=False, default=False),
        sa.Column('cancelled', sa.Boolean(), nullable=False, default=False),
        sa.Column('currency_code', sa.String(10), nullable=True),
        sa.Column('total_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('subtotal_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('total_tax', sa.Numeric(10, 2), nullable=True),
        sa.Column('total_shipping', sa.Numeric(10, 2), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('customer_data', sa.JSON(), nullable=True),
        sa.Column('billing_address', sa.JSON(), nullable=True),
        sa.Column('shipping_address', sa.JSON(), nullable=True),
        sa.Column('line_items', sa.JSON(), nullable=True),
        sa.Column('fulfillments', sa.JSON(), nullable=True),
        sa.Column('refunds', sa.JSON(), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    )
    
    # Create indexes
    op.create_index('idx_shopify_orders_tenant_id', 'shopify_orders', ['tenant_id'])
    op.create_index('idx_shopify_orders_shopify_order_id', 'shopify_orders', ['shopify_order_id'])
    op.create_index('idx_shopify_orders_financial_status', 'shopify_orders', ['financial_status'])
    op.create_index('idx_shopify_orders_fulfillment_status', 'shopify_orders', ['fulfillment_status'])
    op.create_index('idx_shopify_orders_created_at', 'shopify_orders', ['created_at'])
    op.create_index('idx_shopify_orders_tenant_shopify_id', 'shopify_orders', ['tenant_id', 'shopify_order_id'])
    
    # Create unique constraint for tenant_id + shopify_order_id
    op.create_unique_constraint('uq_shopify_orders_tenant_shopify_id', 'shopify_orders', ['tenant_id', 'shopify_order_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_shopify_orders_tenant_shopify_id', table_name='shopify_orders')
    op.drop_index('idx_shopify_orders_created_at', table_name='shopify_orders')
    op.drop_index('idx_shopify_orders_fulfillment_status', table_name='shopify_orders')
    op.drop_index('idx_shopify_orders_financial_status', table_name='shopify_orders')
    op.drop_index('idx_shopify_orders_shopify_order_id', table_name='shopify_orders')
    op.drop_index('idx_shopify_orders_tenant_id', table_name='shopify_orders')
    
    # Drop table
    op.drop_table('shopify_orders')
