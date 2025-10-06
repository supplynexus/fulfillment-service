"""add unique indexes on product_mappings (core-side and external-side)

Revision ID: 9c2f1a7b8cde
Revises: 5f35e92d5723
Create Date: 2025-10-06 13:50:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "9c2f1a7b8cde"
down_revision = "5f35e92d5723"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Core-side uniqueness
    # Variant-level: one mapping per core variant within an external system
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_pm_core_variant
        ON product_mappings (tenant_id, external_system_id, core_product_id, core_variant_id)
        WHERE core_variant_id IS NOT NULL;
        """
    )

    # Product-level (no variants): one product-level mapping per external system
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_pm_core_product
        ON product_mappings (tenant_id, external_system_id, core_product_id)
        WHERE core_variant_id IS NULL;
        """
    )

    # External-side uniqueness
    # Variant-level: one mapping per external variant within tenant+external system
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_pm_ext_variant
        ON product_mappings (tenant_id, external_system_id, external_product_id, external_variant_id)
        WHERE external_variant_id IS NOT NULL;
        """
    )

    # Product-level (no variants): one mapping per external product within tenant+external system
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_pm_ext_product
        ON product_mappings (tenant_id, external_system_id, external_product_id)
        WHERE external_variant_id IS NULL;
        """
    )


def downgrade() -> None:
    # Drop the created indexes if they exist
    op.execute("DROP INDEX IF EXISTS uq_pm_ext_product;")
    op.execute("DROP INDEX IF EXISTS uq_pm_ext_variant;")
    op.execute("DROP INDEX IF EXISTS uq_pm_core_product;")
    op.execute("DROP INDEX IF EXISTS uq_pm_core_variant;")
