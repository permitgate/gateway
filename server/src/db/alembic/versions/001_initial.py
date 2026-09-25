# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

"""Initial migration

Revision ID: 001
Revises:
Create Date: 2026-09-11 00:00:00.000000

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.UUID(), nullable=False, default=uuid.uuid4),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False, default=uuid.uuid4),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.String(50),
            nullable=False,
            server_default="reviewer",
        ),
        sa.Column("slack_user_id", sa.String(100), nullable=True),
        sa.Column("teams_user_id", sa.String(100), nullable=True),
        sa.Column("telegram_user_id", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_tenant_user_id"),
        sa.UniqueConstraint("tenant_id", "email", name="uq_tenant_user_email"),
        sa.UniqueConstraint("tenant_id", "slack_user_id", name="uq_tenant_slack_id"),
        sa.UniqueConstraint("tenant_id", "teams_user_id", name="uq_tenant_teams_id"),
        sa.UniqueConstraint(
            "tenant_id", "telegram_user_id", name="uq_tenant_telegram_id"
        ),
        sa.CheckConstraint(
            "role IN ('administrator', 'reviewer')", name="chk_user_role"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "reviewer_groups",
        sa.Column("id", sa.UUID(), nullable=False, default=uuid.uuid4),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_tenant_group_name"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_tenant_group_id"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "group_memberships",
        sa.Column("id", sa.UUID(), nullable=False, default=uuid.uuid4),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("group_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, default=0),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["group_id", "tenant_id"],
            ["reviewer_groups.id", "reviewer_groups.tenant_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id", "tenant_id"],
            ["users.id", "users.tenant_id"],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("priority >= 0", name="chk_positive_priority"),
        sa.UniqueConstraint("group_id", "user_id", name="uq_group_user"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "approval_flows",
        sa.Column("id", sa.UUID(), nullable=False, default=uuid.uuid4),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("active_version_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_tenant_flow_id"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "flow_versions",
        sa.Column("id", sa.UUID(), nullable=False, default=uuid.uuid4),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("flow_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("json_schema", JSONB(), nullable=False),
        sa.Column(
            "preview_schema",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{\"fields\":[]}'::jsonb"),
        ),
        sa.Column(
            "schema_validation_enabled", sa.Boolean(), nullable=False, default=True
        ),
        sa.Column("amount_path", sa.String(255), nullable=True),
        sa.Column("currency_path", sa.String(255), nullable=True),
        sa.Column("high_risk", sa.Boolean(), nullable=False, default=False),
        sa.Column(
            "currency_exchange_rates",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("sla_seconds", sa.Integer(), nullable=False),
        sa.Column("reset_on_edit", sa.Boolean(), nullable=False, default=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["flow_id", "tenant_id"],
            ["approval_flows.id", "approval_flows.tenant_id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("flow_id", "version", name="uq_flow_version"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_tenant_flow_version_id"),
        sa.UniqueConstraint(
            "id", "flow_id", "tenant_id", name="uq_tenant_flow_version_composite"
        ),
        sa.CheckConstraint("sla_seconds > 0", name="chk_positive_sla"),
        sa.CheckConstraint(
            "(amount_path IS NULL AND currency_path IS NULL) OR (amount_path IS NOT NULL AND currency_path IS NOT NULL)",
            name="chk_flow_amount_paths_bound",
        ),
        sa.CheckConstraint(
            "amount_path IS NULL OR amount_path = '' OR amount_path ~ '^(/([^/~]|~[01])*)+$'",
            name="chk_flow_amount_path_pointer",
        ),
        sa.CheckConstraint(
            "currency_path IS NULL OR currency_path ~ '^(/([^/~]|~[01])*)+$'",
            name="chk_flow_currency_path_pointer",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "approval_steps",
        sa.Column("id", sa.UUID(), nullable=False, default=uuid.uuid4),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("flow_version_id", sa.UUID(), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("target_group_id", sa.UUID(), nullable=True),
        sa.Column("target_user_id", sa.UUID(), nullable=True),
        sa.Column(
            "editable_paths",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("amount_limit_minor_units", sa.BigInteger(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("required_role", sa.String(50), nullable=True),
        sa.Column("action_type", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
            name="fk_approval_steps_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["flow_version_id", "tenant_id"],
            ["flow_versions.id", "flow_versions.tenant_id"],
            ondelete="CASCADE",
            name="fk_approval_steps_flow_version",
        ),
        sa.ForeignKeyConstraint(
            ["target_group_id", "tenant_id"],
            ["reviewer_groups.id", "reviewer_groups.tenant_id"],
            ondelete="RESTRICT",
            name="fk_approval_steps_target_group",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id", "tenant_id"],
            ["users.id", "users.tenant_id"],
            ondelete="RESTRICT",
            name="fk_approval_steps_target_user",
        ),
        sa.UniqueConstraint(
            "flow_version_id", "step_order", name="uq_flow_version_step"
        ),
        sa.UniqueConstraint("id", "tenant_id", name="uq_tenant_step_id"),
        sa.CheckConstraint("step_order > 0", name="chk_positive_step"),
        sa.CheckConstraint(
            "(target_group_id IS NOT NULL AND target_user_id IS NULL) OR "
            "(target_group_id IS NULL AND target_user_id IS NOT NULL)",
            name="chk_exactly_one_approval_target",
        ),
        sa.CheckConstraint(
            "amount_limit_minor_units > 0", name="chk_step_positive_amount"
        ),
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name="chk_step_currency_format"),
        sa.CheckConstraint(
            "required_role IN ('administrator', 'reviewer')",
            name="chk_step_required_role",
        ),
        sa.CheckConstraint(
            "(amount_limit_minor_units IS NULL AND currency IS NULL) OR "
            "(amount_limit_minor_units IS NOT NULL AND currency IS NOT NULL)",
            name="chk_step_amount_currency_bound",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_users_id_tenant_id", "users", ["id", "tenant_id"], unique=True)
    op.create_index(
        "ix_reviewer_groups_id_tenant_id",
        "reviewer_groups",
        ["id", "tenant_id"],
        unique=True,
    )
    op.create_index(
        "idx_approval_steps_group",
        "approval_steps",
        ["target_group_id"],
        postgresql_where=sa.text("target_group_id IS NOT NULL"),
    )
    op.create_index(
        "idx_approval_steps_user",
        "approval_steps",
        ["target_user_id"],
        postgresql_where=sa.text("target_user_id IS NOT NULL"),
    )
    op.create_index(
        "idx_approval_steps_editable_paths",
        "approval_steps",
        ["editable_paths"],
        postgresql_using="gin",
    )

    op.create_foreign_key(
        "fk_approval_flows_active_version_id",
        "approval_flows",
        "flow_versions",
        ["active_version_id"],
        ["id"],
    )

    op.create_check_constraint(
        "chk_flow_version_json_schema_shape",
        "flow_versions",
        "jsonb_typeof(json_schema) = 'object' "
        "AND octet_length(json_schema::text) <= 65536 "
        "AND (json_schema = '{}'::jsonb "
        "OR COALESCE(json_schema->>'$schema' = 'https://json-schema.org/draft/2020-12/schema', false))",
    )
    op.create_check_constraint(
        "chk_flow_version_schema_toggle_coherence",
        "flow_versions",
        "(json_schema = '{}'::jsonb) = (NOT schema_validation_enabled)",
    )


def downgrade() -> None:
    op.drop_index("idx_approval_steps_editable_paths", table_name="approval_steps")
    op.drop_index("idx_approval_steps_user", table_name="approval_steps")
    op.drop_index("idx_approval_steps_group", table_name="approval_steps")
    op.drop_table("approval_steps")
    op.drop_constraint(
        "chk_flow_version_schema_toggle_coherence",
        "flow_versions",
        type_="check",
    )
    op.drop_constraint(
        "chk_flow_version_json_schema_shape",
        "flow_versions",
        type_="check",
    )
    op.drop_constraint(
        "fk_approval_flows_active_version_id",
        "approval_flows",
        type_="foreignkey",
    )
    op.drop_index("ix_reviewer_groups_id_tenant_id")
    op.drop_index("ix_users_id_tenant_id")
    op.drop_table("flow_versions")
    op.drop_table("approval_flows")
    op.drop_table("group_memberships")
    op.drop_table("reviewer_groups")
    op.drop_table("users")
    op.drop_table("tenants")
