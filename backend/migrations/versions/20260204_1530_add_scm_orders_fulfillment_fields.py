"""Add carrier/shipped_at/delivered_at to scm_orders

Revision ID: 4f3b1b2a9c10
Revises: d2e3f4a5b6c7
Create Date: 2026-02-04 15:30:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4f3b1b2a9c10"
down_revision = "d2e3f4a5b6c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scm_orders", sa.Column("carrier", sa.String(length=100), nullable=True))
    op.add_column("scm_orders", sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("scm_orders", sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("scm_orders", "delivered_at")
    op.drop_column("scm_orders", "shipped_at")
    op.drop_column("scm_orders", "carrier")
