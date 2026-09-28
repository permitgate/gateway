# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db.repo.approval_steps_repo import ApprovalStepsRepository
from model import ApprovalStep, ApprovalStepInput
from service.exceptions import ApprovalStepNotFoundError, InvalidApprovalStepError


class ApprovalStepsService:
    """Service for managing approval steps with transaction handling."""

    def __init__(self):
        self._repo = ApprovalStepsRepository()

    async def create_steps_for_flow_version(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        flow_version_id: uuid.UUID,
        steps: list[ApprovalStepInput],
    ) -> list[ApprovalStep]:
        """Create approval steps for a flow version.

        Assigns step_order sequentially based on list position (1..N).
        All steps are created atomically; on integrity error, the session is rolled back.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            flow_version_id: ID of the flow version
            steps: List of ApprovalStepInput objects to create

        Returns:
            List of created ApprovalStep pydantic entities

        Raises:
            InvalidApprovalStepError: If a step violates database constraints
        """
        created_steps = []
        try:
            for step_order, step_input in enumerate(steps, start=1):
                step = await self._repo.create_step(
                    session=session,
                    tenant_id=tenant_id,
                    flow_version_id=flow_version_id,
                    step_order=step_order,
                    name=step_input.name,
                    target_group_id=step_input.target_group_id,
                    target_user_id=step_input.target_user_id,
                    editable_paths=step_input.editable_paths,
                    amount_limit_minor_units=step_input.amount_limit_minor_units,
                    currency=step_input.currency,
                    required_role=step_input.required_role.value
                    if step_input.required_role
                    else None,
                    action_type=step_input.action_type,
                )
                created_steps.append(step)
            await session.flush()
        except IntegrityError as exc:
            await session.rollback()
            exc_str = str(exc)
            if "chk_exactly_one_approval_target" in exc_str:
                raise InvalidApprovalStepError(
                    "Exactly one of target_group_id or target_user_id must be set"
                ) from exc
            if "chk_step_amount_currency_bound" in exc_str:
                raise InvalidApprovalStepError(
                    "amount_limit_minor_units and currency must both be set or both be None"
                ) from exc
            if "chk_step_currency_format" in exc_str:
                raise InvalidApprovalStepError(
                    "currency must be a valid 3-letter ISO code"
                ) from exc
            if "fk_approval_steps_target_group" in exc_str:
                raise InvalidApprovalStepError(
                    "target_group_id references a non-existent reviewer group"
                ) from exc
            if "fk_approval_steps_target_user" in exc_str:
                raise InvalidApprovalStepError(
                    "target_user_id references a non-existent user"
                ) from exc
            raise
        return [
            ApprovalStep.model_validate(step, from_attributes=True)
            for step in created_steps
        ]

    async def list_steps_for_flow_version(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        flow_version_id: uuid.UUID,
    ) -> list[ApprovalStep]:
        """Get all approval steps for a flow version.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            flow_version_id: ID of the flow version

        Returns:
            List of ApprovalStep pydantic entities ordered by step_order
        """
        steps = await self._repo.list_steps_by_flow_version_id(
            session, tenant_id, flow_version_id
        )
        return [
            ApprovalStep.model_validate(step, from_attributes=True) for step in steps
        ]

    async def get_step(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        step_id: uuid.UUID,
    ) -> ApprovalStep:
        """Get a specific approval step by ID.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            step_id: ID of the approval step

        Returns:
            The ApprovalStep pydantic entity

        Raises:
            ApprovalStepNotFoundError: If the step is not found
        """
        step = await self._repo.get_step_by_id(session, tenant_id, step_id)
        if not step:
            raise ApprovalStepNotFoundError(step_id)
        return ApprovalStep.model_validate(step, from_attributes=True)
