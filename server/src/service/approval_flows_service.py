# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ApprovalFlow, FlowVersion
from db.repo.approval_flows_repo import ApprovalFlowsRepository
from db.repo.flow_versions_repo import FlowVersionsRepository
from service.exceptions import (
    ApprovalFlowNotFoundError,
    FlowVersionNotFoundError,
    NoActiveVersionError,
)


class ApprovalFlowsService:
    """Service for managing approval flows with transaction handling."""

    def __init__(self):
        self._repo = ApprovalFlowsRepository()
        self._version_repo = FlowVersionsRepository()

    async def create_flow(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        name: str,
        json_schema: dict,
        preview_schema: dict,
        schema_validation_enabled: bool,
        sla_seconds: int,
        reset_on_edit: bool,
    ) -> ApprovalFlow:
        """Create a new approval flow and commit the transaction.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            name: Name of the flow
            json_schema: JSON schema for validating flow payloads
            preview_schema: JSON schema for previewing and rendering the flow in the UI
            schema_validation_enabled: Whether to enforce JSON schema validation on incoming tasks
            sla_seconds: Service level agreement timeout in seconds for approval decisions
            reset_on_edit: Whether to reset the flow state when the artifact is edited

        Returns:
            The created ApprovalFlow object
        """
        flow_id = uuid.uuid4()
        flow = await self._repo.create_flow(
            session=session, tenant_id=tenant_id, id=flow_id, name=name
        )
        await session.flush()
        flow_version = await self._version_repo.create_flow_version(
            session=session,
            tenant_id=tenant_id,
            flow_id=flow_id,
            version=1,
            json_schema=json_schema,
            preview_schema=preview_schema,
            schema_validation_enabled=schema_validation_enabled,
            sla_seconds=sla_seconds,
            reset_on_edit=reset_on_edit,
        )
        await session.flush()
        await self._repo.set_active_version_id(
            session=session,
            tenant_id=tenant_id,
            flow_id=flow_id,
            active_version_id=flow_version.id,
        )
        await session.commit()
        return flow

    async def update_flow(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        flow_id: uuid.UUID,
        json_schema: dict,
        preview_schema: dict,
        schema_validation_enabled: bool,
        sla_seconds: int,
        reset_on_edit: bool,
    ) -> ApprovalFlow:
        """Create new approval flow version and commit the transaction.

        Acquires a row-level lock on the flow to prevent concurrent version number collisions.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            flow_id: ID of the approval flow
            json_schema: JSON schema for validating flow payloads
            preview_schema: JSON schema for previewing and rendering the flow in the UI
            schema_validation_enabled: Whether to enforce JSON schema validation on incoming tasks
            sla_seconds: Service level agreement timeout in seconds for approval decisions
            reset_on_edit: Whether to reset the flow state when the artifact is edited

        Returns:
            The created ApprovalFlow object
        """
        flow = await self._repo.get_flow_by_id_for_update(session, tenant_id, flow_id)
        if not flow:
            raise ApprovalFlowNotFoundError(flow_id)
        if not flow.active_version_id:
            raise NoActiveVersionError(flow_id)

        active_version = await self._version_repo.get_version_by_id(
            session, tenant_id, flow.active_version_id
        )
        if not active_version:
            raise FlowVersionNotFoundError(flow.active_version_id)

        new_flow_version = await self._version_repo.create_flow_version(
            session=session,
            tenant_id=tenant_id,
            flow_id=flow_id,
            version=active_version.version + 1,
            json_schema=json_schema,
            preview_schema=preview_schema,
            schema_validation_enabled=schema_validation_enabled,
            sla_seconds=sla_seconds,
            reset_on_edit=reset_on_edit,
        )
        await session.flush()
        await self._repo.set_active_version_id(
            session=session,
            tenant_id=tenant_id,
            flow_id=flow_id,
            active_version_id=new_flow_version.id,
        )
        await session.commit()
        return flow

    async def list_flows(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> list[ApprovalFlow]:
        """List all approval flows for a specific tenant.

        Args:
            session: Database session
            tenant_id: ID of the tenant

        Returns:
            List of ApprovalFlow objects for the tenant
        """
        return await self._repo.list_flows(session, tenant_id)

    async def get_flow(
        self, session: AsyncSession, tenant_id: uuid.UUID, flow_id: uuid.UUID
    ) -> ApprovalFlow:
        """Get a specific approval flow by its ID for a tenant.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            flow_id: ID of the approval flow

        Returns:
            ApprovalFlow object

        Raises:
            ApprovalFlowNotFoundError: If the flow is not found
        """
        flow = await self._repo.get_flow_by_id(session, tenant_id, flow_id)
        if not flow:
            raise ApprovalFlowNotFoundError(flow_id)
        return flow

    async def list_flow_versions(
        self, session: AsyncSession, tenant_id: uuid.UUID, flow_id: uuid.UUID
    ) -> list[FlowVersion]:
        """List all versions of an approval flow for a tenant.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            flow_id: ID of the approval flow

        Returns:
            List of FlowVersion objects ordered by version number
        """
        return await self._version_repo.list_versions_by_flow_id(
            session, tenant_id, flow_id
        )

    async def get_flow_version(
        self, session: AsyncSession, tenant_id: uuid.UUID, version_id: uuid.UUID
    ) -> FlowVersion:
        """Get a specific flow version by its ID for a tenant.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            version_id: ID of the flow version

        Returns:
            FlowVersion object

        Raises:
            FlowVersionNotFoundError: If the version is not found
        """
        version = await self._version_repo.get_version_by_id(
            session, tenant_id, version_id
        )
        if not version:
            raise FlowVersionNotFoundError(version_id)
        return version
