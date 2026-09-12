# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

"""Create tenants table

Revision ID: 001
Revises:
Create Date: 2026-09-11 00:00:00.000000

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

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
        sa.Column("json_schema", sa.JSON(), nullable=False),
        sa.Column(
            "preview_schema",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{\"fields\":[]}'::jsonb"),
        ),
        sa.Column(
            "schema_validation_enabled", sa.Boolean(), nullable=False, default=True
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
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_foreign_key(
        "fk_approval_flows_active_version_id",
        "approval_flows",
        "flow_versions",
        ["active_version_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_approval_flows_active_version_id",
        "approval_flows",
        type_="foreignkey",
    )
    op.drop_table("flow_versions")
    op.drop_table("approval_flows")
    op.drop_table("tenants")
