"""add_address_validation_fields_to_orders

Revision ID: b7c8d9e0f123
Revises: a1b2c3d4e5f6
Create Date: 2025-11-29 00:01:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b7c8d9e0f123"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add address validation fields to orders table."""
    op.add_column(
        "orders",
        sa.Column("address_validation_status", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("address_validation_reason_code", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("address_validation_message", sa.Text(), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("address_last_validated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Remove address validation fields from orders table."""
    op.drop_column("orders", "address_last_validated_at")
    op.drop_column("orders", "address_validation_message")
    op.drop_column("orders", "address_validation_reason_code")
    op.drop_column("orders", "address_validation_status")







