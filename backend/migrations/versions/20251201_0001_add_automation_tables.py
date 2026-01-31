"""add_automation_tables

Revision ID: c1d2e3f4a5b6
Revises: b7c8d9e0f123
Create Date: 2025-12-01 00:01:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "c1d2e3f4a5b6"
down_revision = "b7c8d9e0f123"  # 基于最新的迁移文件
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add automation tables."""
    # 创建 automation_steps 表
    op.create_table(
        "automation_steps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("step_key", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("required_external_systems", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("celery_task_name", sa.String(length=200), nullable=True),
        sa.Column("default_schedule", sa.String(length=50), nullable=True),
        sa.Column("default_enabled", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("is_manual_only", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_automation_steps_id"), "automation_steps", ["id"], unique=False)
    op.create_index(op.f("ix_automation_steps_step_key"), "automation_steps", ["step_key"], unique=True)
    op.create_index(op.f("ix_automation_steps_category"), "automation_steps", ["category"], unique=False)

    # 创建 tenant_automation_configs 表
    op.create_table(
        "tenant_automation_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("step_key", sa.String(length=100), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("schedule", sa.String(length=50), nullable=True),
        sa.Column("schedule_seconds", sa.Integer(), nullable=True),
        sa.Column("task_params", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("external_system_types", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("external_system_ids", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_status", sa.String(length=20), nullable=True),
        sa.Column("last_run_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "step_key", name="uq_tenant_step"),
    )
    op.create_index(op.f("ix_tenant_automation_configs_id"), "tenant_automation_configs", ["id"], unique=False)
    op.create_index(op.f("ix_tenant_automation_configs_tenant_id"), "tenant_automation_configs", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_tenant_automation_configs_step_key"), "tenant_automation_configs", ["step_key"], unique=False)

    # 创建 automation_manual_buttons 表
    op.create_table(
        "automation_manual_buttons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("step_key", sa.String(length=100), nullable=False),
        sa.Column("button_key", sa.String(length=100), nullable=False),
        sa.Column("button_label", sa.String(length=100), nullable=False),
        sa.Column("button_action", sa.String(length=200), nullable=False),
        sa.Column("http_method", sa.String(length=10), nullable=True, server_default="POST"),
        sa.Column("is_recommended", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("is_deprecated", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("deprecated_reason", sa.Text(), nullable=True),
        sa.Column("page_path", sa.String(length=200), nullable=True),
        sa.Column("order", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("step_key", "button_key", name="uq_step_button"),
    )
    op.create_index(op.f("ix_automation_manual_buttons_id"), "automation_manual_buttons", ["id"], unique=False)
    op.create_index(op.f("ix_automation_manual_buttons_step_key"), "automation_manual_buttons", ["step_key"], unique=False)


def downgrade() -> None:
    """Remove automation tables."""
    op.drop_index(op.f("ix_automation_manual_buttons_step_key"), table_name="automation_manual_buttons")
    op.drop_index(op.f("ix_automation_manual_buttons_id"), table_name="automation_manual_buttons")
    op.drop_table("automation_manual_buttons")
    op.drop_index(op.f("ix_tenant_automation_configs_step_key"), table_name="tenant_automation_configs")
    op.drop_index(op.f("ix_tenant_automation_configs_tenant_id"), table_name="tenant_automation_configs")
    op.drop_index(op.f("ix_tenant_automation_configs_id"), table_name="tenant_automation_configs")
    op.drop_table("tenant_automation_configs")
    op.drop_index(op.f("ix_automation_steps_category"), table_name="automation_steps")
    op.drop_index(op.f("ix_automation_steps_step_key"), table_name="automation_steps")
    op.drop_index(op.f("ix_automation_steps_id"), table_name="automation_steps")
    op.drop_table("automation_steps")

