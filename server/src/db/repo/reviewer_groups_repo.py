# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ReviewerGroup


class ReviewerGroupsRepository:
    """Repository for managing reviewer_groups table operations."""

    async def create_reviewer_group(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        name: str,
    ) -> ReviewerGroup:
        """Create a new reviewer group for a tenant.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            name: Reviewer group name

        Returns:
            The created ReviewerGroup object
        """
        reviewer_group = ReviewerGroup(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=name,
        )
        session.add(reviewer_group)
        return reviewer_group

    async def get_reviewer_group_by_id(
        self, session: AsyncSession, tenant_id: uuid.UUID, reviewer_group_id: uuid.UUID
    ) -> ReviewerGroup | None:
        """Get a reviewer group by ID for a tenant.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            reviewer_group_id: ID of the reviewer group

        Returns:
            ReviewerGroup object or None if not found
        """
        result = await session.execute(
            select(ReviewerGroup).where(
                (ReviewerGroup.id == reviewer_group_id)
                & (ReviewerGroup.tenant_id == tenant_id)
            )
        )
        return result.scalar_one_or_none()

    async def list_reviewer_groups(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> list[ReviewerGroup]:
        """List all reviewer groups for a tenant.

        Args:
            session: Database session
            tenant_id: ID of the tenant

        Returns:
            List of ReviewerGroup objects for the tenant
        """
        result = await session.execute(
            select(ReviewerGroup).where(ReviewerGroup.tenant_id == tenant_id)
        )
        return result.scalars().all()

    async def delete_reviewer_group(
        self, session: AsyncSession, tenant_id: uuid.UUID, reviewer_group_id: uuid.UUID
    ) -> bool:
        """Delete a reviewer group for a tenant.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            reviewer_group_id: ID of the reviewer group

        Returns:
            True if reviewer group was deleted, False if not found
        """
        result = await session.execute(
            select(ReviewerGroup).where(
                (ReviewerGroup.id == reviewer_group_id)
                & (ReviewerGroup.tenant_id == tenant_id)
            )
        )
        reviewer_group = result.scalar_one_or_none()
        if reviewer_group:
            await session.delete(reviewer_group)
            return True
        return False
