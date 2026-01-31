"""restructure orders with order_items table (destructive)

Revision ID: 8d4f2e9a1b5c
Revises: 5f35e92d5723
Create Date: 2025-10-06 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "8d4f2e9a1b5c"
down_revision = "9c2f1a7b8cde"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create order_items table
    op.create_table(
        'order_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('core_product_id', sa.Integer(), nullable=True),
        sa.Column('core_variant_id', sa.Integer(), nullable=True),
        sa.Column('external_product_id', sa.String(length=100), nullable=True),
        sa.Column('external_variant_id', sa.String(length=100), nullable=True),
        sa.Column('sku', sa.String(length=100), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('variant_title', sa.String(length=255), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('total_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('discount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('tax', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('fulfillment_status', sa.String(length=50), nullable=True),
        sa.Column('item_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['core_product_id'], ['products.id'], ),
        sa.ForeignKeyConstraint(['core_variant_id'], ['product_variants.id'], ),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for order_items
    op.create_index('ix_order_items_id', 'order_items', ['id'], unique=False)
    op.create_index('ix_order_items_tenant_id', 'order_items', ['tenant_id'], unique=False)
    op.create_index('ix_order_items_order_id', 'order_items', ['order_id'], unique=False)
    op.create_index('ix_order_items_core_product_id', 'order_items', ['core_product_id'], unique=False)
    op.create_index('ix_order_items_core_variant_id', 'order_items', ['core_variant_id'], unique=False)
    op.create_index('ix_order_items_external_product_id', 'order_items', ['external_product_id'], unique=False)
    op.create_index('ix_order_items_external_variant_id', 'order_items', ['external_variant_id'], unique=False)
    op.create_index('ix_order_items_sku', 'order_items', ['sku'], unique=False)
    
    # Drop the line_items column from orders table (destructive)
    op.drop_column('orders', 'line_items')


def downgrade() -> None:
    # Add back line_items column to orders table
    op.add_column('orders', sa.Column('line_items', sa.JSON(), nullable=False, server_default='[]'))
    op.execute("ALTER TABLE orders ALTER COLUMN line_items DROP DEFAULT;")
    
    # Drop order_items table and indexes
    op.drop_index('ix_order_items_sku', table_name='order_items')
    op.drop_index('ix_order_items_external_variant_id', table_name='order_items')
    op.drop_index('ix_order_items_external_product_id', table_name='order_items')
    op.drop_index('ix_order_items_core_variant_id', table_name='order_items')
    op.drop_index('ix_order_items_core_product_id', table_name='order_items')
    op.drop_index('ix_order_items_order_id', table_name='order_items')
    op.drop_index('ix_order_items_tenant_id', table_name='order_items')
    op.drop_index('ix_order_items_id', table_name='order_items')
    op.drop_table('order_items')