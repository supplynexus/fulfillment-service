"""Add carrier/shipped_at/delivered_at to scm_orders

Revision ID: 4f3b1b2a9c10
Revises: d2e3f4a5b6c7
Create Date: 2026-02-04 15:30:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "4f3b1b2a9c10"
down_revision = "d2e3f4a5b6c7"
branch_labels = None
depends_on = None


def _column_exists(conn, table: str, column: str) -> bool:
    insp = inspect(conn)
    cols = [c["name"] for c in insp.get_columns(table)]
    return column in cols


def upgrade() -> None:
    conn = op.get_bind()
    if not _column_exists(conn, "scm_orders", "carrier"):
        op.add_column("scm_orders", sa.Column("carrier", sa.String(length=100), nullable=True))
    if not _column_exists(conn, "scm_orders", "shipped_at"):
        op.add_column("scm_orders", sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True))
    if not _column_exists(conn, "scm_orders", "delivered_at"):
        op.add_column("scm_orders", sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    if _column_exists(conn, "scm_orders", "delivered_at"):
        op.drop_column("scm_orders", "delivered_at")
    if _column_exists(conn, "scm_orders", "shipped_at"):
        op.drop_column("scm_orders", "shipped_at")
    if _column_exists(conn, "scm_orders", "carrier"):
        op.drop_column("scm_orders", "carrier")
