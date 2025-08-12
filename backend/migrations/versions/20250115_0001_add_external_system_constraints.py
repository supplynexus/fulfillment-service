"""Add external system constraints and indexes

Revision ID: 20250115_0001
Revises: 20250810_1200_1d071ed2a34e_initial_migration
Create Date: 2025-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250115_0001'
down_revision = '20250810_1200_1d071ed2a34e_initial_migration'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add unique constraint for tenant + name combination
    # This ensures each external system has a unique name within a tenant
    # but allows multiple systems of the same type
    op.create_unique_constraint(
        'uq_external_systems_tenant_name',
        'external_systems',
        ['tenant_id', 'name']
    )
    
    # Add index for better query performance
    op.create_index(
        'ix_external_systems_tenant_type',
        'external_systems',
        ['tenant_id', 'system_type']
    )
    
    # Add index for external data queries
    op.create_index(
        'ix_external_data_tenant_type',
        'external_data',
        ['tenant_id', 'data_type']
    )
    
    # Add unique constraint for external data
    # This ensures no duplicate data from the same external system
    op.create_unique_constraint(
        'uq_external_data_system_type_id',
        'external_data',
        ['external_system_id', 'data_type', 'external_id']
    )


def downgrade() -> None:
    # Remove constraints and indexes
    op.drop_constraint('uq_external_systems_tenant_name', 'external_systems', type_='unique')
    op.drop_index('ix_external_systems_tenant_type', table_name='external_systems')
    op.drop_index('ix_external_data_tenant_type', table_name='external_data')
    op.drop_constraint('uq_external_data_system_type_id', 'external_data', type_='unique')
