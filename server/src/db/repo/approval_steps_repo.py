# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ApprovalStep


class ApprovalStepsRepository:
    """Repository for managing approval_steps table operations."""

    async def create_step(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        flow_version_id: uuid.UUID,
        step_order: int,
        name: str,
        target_group_id: uuid.UUID | None,
        target_user_id: uuid.UUID | None,
        editable_paths: list,
        amount_limit_minor_units: int | None,
        currency: str | None,
        required_role: str | None,
        action_type: str | None,
    ) -> ApprovalStep:
        """Create a new approval step.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            flow_version_id: ID of the flow version
            step_order: Sequential order of the step in the approval chain
            name: Name of the approval step
            target_group_id: ID of the reviewer group to route this step to (mutually exclusive with target_user_id)
            target_user_id: ID of the user to route this step to (mutually exclusive with target_group_id)
            editable_paths: List of JSON Pointer paths the approver can edit
            amount_limit_minor_units: Maximum amount (in minor units) the approver can approve, or None for unlimited
            currency: Currency code for the amount limit (must be paired with amount_limit_minor_units)
            required_role: Required user role to approve this step
            action_type: Action type associated with this step

        Returns:
            The created ApprovalStep object
        """
        step = ApprovalStep(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            flow_version_id=flow_version_id,
            step_order=step_order,
            name=name,
            target_group_id=target_group_id,
            target_user_id=target_user_id,
            editable_paths=editable_paths,
            amount_limit_minor_units=amount_limit_minor_units,
            currency=currency,
            required_role=required_role,
            action_type=action_type,
        )
        session.add(step)
        return step

    async def list_steps_by_flow_version_id(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        flow_version_id: uuid.UUID,
    ) -> list[ApprovalStep]:
        """Get all steps for a flow version, ordered by step order.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            flow_version_id: ID of the flow version

        Returns:
            List of ApprovalStep objects ordered by step_order
        """
        result = await session.execute(
            select(ApprovalStep)
            .where(
                (ApprovalStep.flow_version_id == flow_version_id)
                & (ApprovalStep.tenant_id == tenant_id)
            )
            .order_by(ApprovalStep.step_order)
        )
        return result.scalars().all()

    async def get_step_by_id(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        step_id: uuid.UUID,
    ) -> ApprovalStep | None:
        """Get a specific approval step by its ID.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            step_id: ID of the approval step

        Returns:
            ApprovalStep object or None if not found
        """
        result = await session.execute(
            select(ApprovalStep).where(
                (ApprovalStep.id == step_id) & (ApprovalStep.tenant_id == tenant_id)
            )
        )
        return result.scalar_one_or_none()
