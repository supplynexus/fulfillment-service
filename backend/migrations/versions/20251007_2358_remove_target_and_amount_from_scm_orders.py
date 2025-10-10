"""remove target columns and total_amount from scm_orders

Revision ID: 2e9bd7c4a6f1
Revises: 8f284a9794d6
Create Date: 2025-10-07 23:58:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2e9bd7c4a6f1"
down_revision = "8f284a9794d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Columns were already removed in previous migration 8f284a9794d6
    # No additional changes needed
    pass


def downgrade() -> None:
    # No-op: columns are deprecated permanently
    pass


