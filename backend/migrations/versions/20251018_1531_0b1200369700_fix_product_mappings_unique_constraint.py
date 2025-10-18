"""fix_product_mappings_unique_constraint

Revision ID: 0b1200369700
Revises: 6f98c9a0f611
Create Date: 2025-10-18 15:31:23.587520

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0b1200369700'
down_revision = '6f98c9a0f611'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_product_mappings_tenant_core_variant_external",
        "product_mappings",
        ["tenant_id", "core_product_id", "core_variant_id", "external_system_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_product_mappings_tenant_core_variant_external", "product_mappings", type_="unique")
