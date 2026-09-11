# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ApprovalFlow


class ApprovalFlowsRepository:
    """Repository for managing approval_flows table operations."""

    async def create_flow(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        name: str,
        id: uuid.UUID | None = None,
        active_version_id: uuid.UUID | None = None,
    ) -> ApprovalFlow:
        """Create a new approval flow.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            name: Name of the flow
            id: Optional ID for the flow
            active_version_id: Optional ID of the active version

        Returns:
            The created ApprovalFlow object
        """
        flow = ApprovalFlow(
            id=id if id is not None else uuid.uuid4(),
            tenant_id=tenant_id,
            name=name,
            active_version_id=active_version_id,
        )
        session.add(flow)
        return flow

    async def get_flow_by_id(
        self, session: AsyncSession, tenant_id: uuid.UUID, flow_id: uuid.UUID
    ) -> ApprovalFlow | None:
        """Get an approval flow by its ID for a specific tenant.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            flow_id: ID of the approval flow

        Returns:
            ApprovalFlow object or None if not found
        """
        result = await session.execute(
            select(ApprovalFlow).where(
                (ApprovalFlow.id == flow_id) & (ApprovalFlow.tenant_id == tenant_id)
            )
        )
        return result.scalar_one_or_none()

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
        result = await session.execute(
            select(ApprovalFlow).where(ApprovalFlow.tenant_id == tenant_id)
        )
        return result.scalars().all()

    async def set_active_version_id(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        flow_id: uuid.UUID,
        active_version_id: uuid.UUID,
    ) -> ApprovalFlow:
        """Update an approval flow's active version for a specific tenant.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            flow_id: ID of the flow to update
            active_version_id: ID of the new active version

        Returns:
            The updated ApprovalFlow object
        """
        result = await session.execute(
            select(ApprovalFlow).where(
                (ApprovalFlow.id == flow_id) & (ApprovalFlow.tenant_id == tenant_id)
            )
        )
        flow = result.scalar_one()
        flow.active_version_id = active_version_id
        return flow
