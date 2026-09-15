# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import FlowVersion


class FlowVersionsRepository:
    """Repository for managing flow_versions table operations."""

    async def create_flow_version(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        flow_id: uuid.UUID,
        version: int,
        json_schema: dict,
        preview_schema: dict,
        schema_validation_enabled: bool,
        sla_seconds: int,
        reset_on_edit: bool,
    ) -> FlowVersion:
        """Create a new flow version.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            flow_id: ID of the approval flow
            version: Flow version number
            json_schema: JSON schema for validating flow payloads
            preview_schema: JSON schema for previewing and rendering the flow in the UI
            schema_validation_enabled: Whether to enforce JSON schema validation on incoming tasks
            sla_seconds: Service level agreement timeout in seconds for approval decisions
            reset_on_edit: Whether to reset the flow state when the artifact is edited

        Returns:
            The created FlowVersion object
        """
        flow_version = FlowVersion(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            flow_id=flow_id,
            version=version,
            json_schema=json_schema,
            preview_schema=preview_schema,
            schema_validation_enabled=schema_validation_enabled,
            sla_seconds=sla_seconds,
            reset_on_edit=reset_on_edit,
        )
        session.add(flow_version)
        return flow_version

    async def list_versions_by_flow_id(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        flow_id: uuid.UUID,
    ) -> list[FlowVersion]:
        """Get all versions of a flow for a tenant, ordered by version number.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            flow_id: ID of the approval flow

        Returns:
            List of FlowVersion objects ordered by version number
        """
        result = await session.execute(
            select(FlowVersion)
            .where(
                (FlowVersion.flow_id == flow_id) & (FlowVersion.tenant_id == tenant_id)
            )
            .order_by(FlowVersion.version)
        )
        return result.scalars().all()

    async def get_version_by_id(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> FlowVersion | None:
        """Get a specific flow version by its ID for a tenant.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            version_id: ID of the flow version

        Returns:
            FlowVersion object or None if not found
        """
        result = await session.execute(
            select(FlowVersion).where(
                (FlowVersion.id == version_id) & (FlowVersion.tenant_id == tenant_id)
            )
        )
        return result.scalar_one_or_none()
