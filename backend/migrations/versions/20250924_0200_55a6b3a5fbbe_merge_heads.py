"""merge heads

Revision ID: 55a6b3a5fbbe
Revises: 7beb7b99f65f, a0714620406e
Create Date: 2025-09-24 02:00:18.232462

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "55a6b3a5fbbe"
down_revision = ("7beb7b99f65f", "a0714620406e")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
