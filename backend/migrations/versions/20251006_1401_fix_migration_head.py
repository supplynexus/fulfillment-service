"""fix migration head

Revision ID: 9c2f1a7b8cde
Revises: 5f35e92d5723
Create Date: 2025-10-06 14:01:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "9c2f1a7b8cde"
down_revision = "5f35e92d5723"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This is a placeholder migration to fix the head issue
    pass


def downgrade() -> None:
    # This is a placeholder migration to fix the head issue
    pass