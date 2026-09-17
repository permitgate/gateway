# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import GroupMembership


class GroupMembershipsRepository:
    """Repository for managing group_memberships table operations."""

    async def create_group_membership(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        group_id: uuid.UUID,
        user_id: uuid.UUID,
        priority: int = 0,
        is_active: bool = True,
    ) -> GroupMembership:
        """Create a new group membership.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            group_id: ID of the reviewer group
            user_id: ID of the user
            priority: Priority of the user in the group (default: 0)
            is_active: Whether the membership is active (default: True)

        Returns:
            The created GroupMembership object
        """
        group_membership = GroupMembership(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            group_id=group_id,
            user_id=user_id,
            priority=priority,
            is_active=is_active,
        )
        session.add(group_membership)
        return group_membership

    async def get_group_membership_by_id(
        self, session: AsyncSession, tenant_id: uuid.UUID, membership_id: uuid.UUID
    ) -> GroupMembership | None:
        """Get a group membership by ID for a tenant.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            membership_id: ID of the group membership

        Returns:
            GroupMembership object or None if not found
        """
        result = await session.execute(
            select(GroupMembership).where(
                (GroupMembership.id == membership_id)
                & (GroupMembership.tenant_id == tenant_id)
            )
        )
        return result.scalar_one_or_none()

    async def list_group_memberships_by_group(
        self, session: AsyncSession, tenant_id: uuid.UUID, group_id: uuid.UUID
    ) -> list[GroupMembership]:
        """List all memberships in a group for a tenant.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            group_id: ID of the reviewer group

        Returns:
            List of GroupMembership objects for the group
        """
        result = await session.execute(
            select(GroupMembership).where(
                (GroupMembership.tenant_id == tenant_id)
                & (GroupMembership.group_id == group_id)
            )
        )
        return result.scalars().all()

    async def list_group_memberships_by_user(
        self, session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[GroupMembership]:
        """List all groups a user is a member of for a tenant.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            user_id: ID of the user

        Returns:
            List of GroupMembership objects for the user
        """
        result = await session.execute(
            select(GroupMembership).where(
                (GroupMembership.tenant_id == tenant_id)
                & (GroupMembership.user_id == user_id)
            )
        )
        return result.scalars().all()

    async def delete_group_membership(
        self, session: AsyncSession, tenant_id: uuid.UUID, membership_id: uuid.UUID
    ) -> bool:
        """Delete a group membership for a tenant.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            membership_id: ID of the group membership

        Returns:
            True if membership was deleted, False if not found
        """
        result = await session.execute(
            select(GroupMembership).where(
                (GroupMembership.id == membership_id)
                & (GroupMembership.tenant_id == tenant_id)
            )
        )
        group_membership = result.scalar_one_or_none()
        if group_membership:
            await session.delete(group_membership)
            return True
        return False

    async def delete_group_membership_by_group_and_user(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        group_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete a group membership by group and user.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            group_id: ID of the reviewer group
            user_id: ID of the user

        Returns:
            True if membership was deleted, False if not found
        """
        result = await session.execute(
            select(GroupMembership).where(
                (GroupMembership.tenant_id == tenant_id)
                & (GroupMembership.group_id == group_id)
                & (GroupMembership.user_id == user_id)
            )
        )
        group_membership = result.scalar_one_or_none()
        if group_membership:
            await session.delete(group_membership)
            return True
        return False
