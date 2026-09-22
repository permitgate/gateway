# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db.repo.group_memberships_repo import GroupMembershipsRepository
from db.repo.reviewer_groups_repo import ReviewerGroupsRepository
from db.repo.users_repo import UsersRepository
from model import GroupMembership, ReviewerGroup, User, UserRole
from service.exceptions import (
    ReviewerGroupExistsError,
    UserAlreadyInGroupError,
    UserExistsError,
    UserNotFoundError,
)


class UsersService:
    """Service for managing users."""

    def __init__(self):
        self._repo = UsersRepository()
        self._group_repo = ReviewerGroupsRepository()
        self._membership_repo = GroupMembershipsRepository()

    async def create_user(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        email: str,
        role: UserRole = UserRole.REVIEWER,
        slack_user_id: str | None = None,
        teams_user_id: str | None = None,
        telegram_user_id: str | None = None,
    ) -> User:
        """Create a new user for a tenant and commit the transaction.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            email: User email address
            role: User role (administrator or reviewer)
            slack_user_id: Slack user ID
            teams_user_id: Teams user ID
            telegram_user_id: Telegram user ID

        Returns:
            The created User object
        """
        try:
            user = await self._repo.create_user(
                session=session,
                tenant_id=tenant_id,
                email=email,
                role=role,
                slack_user_id=slack_user_id,
                teams_user_id=teams_user_id,
                telegram_user_id=telegram_user_id,
            )
            await session.commit()
            return User.model_validate(user, from_attributes=True)
        except IntegrityError as e:
            await session.rollback()
            if "uq_tenant_user_email" in str(e):
                raise UserExistsError(f"User with email {email} already exists")
            if "uq_tenant_slack_id" in str(e):
                raise UserExistsError(
                    f"User with Slack ID {slack_user_id} already exists"
                )
            if "uq_tenant_teams_id" in str(e):
                raise UserExistsError(
                    f"User with Teams ID {teams_user_id} already exists"
                )
            if "uq_tenant_telegram_id" in str(e):
                raise UserExistsError(
                    f"User with Telegram ID {telegram_user_id} already exists"
                )
            raise UserExistsError("User already exists")

    async def get_user(
        self, session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> User:
        """Get a user by ID for a tenant.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            user_id: ID of the user

        Returns:
            User object

        Raises:
            UserNotFoundError: If the user is not found
        """
        user = await self._repo.get_user_by_id(session, tenant_id, user_id)
        if not user:
            raise UserNotFoundError(user_id)
        return User.model_validate(user, from_attributes=True)

    async def get_user_by_email(
        self, session: AsyncSession, tenant_id: uuid.UUID, email: str
    ) -> User | None:
        """Get a user by email for a tenant.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            email: User email address

        Returns:
            User object or None if not found
        """
        user = await self._repo.get_user_by_email(session, tenant_id, email)
        if not user:
            return None
        return User.model_validate(user, from_attributes=True)

    async def list_users(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> list[User]:
        """List all users for a tenant.

        Args:
            session: Database session
            tenant_id: ID of the tenant

        Returns:
            List of User objects for the tenant
        """
        return [
            User.model_validate(user, from_attributes=True)
            for user in await self._repo.list_users(session, tenant_id)
        ]

    async def update_user(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        **kwargs,
    ) -> User:
        """Update a user for a tenant and commit the transaction.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            user_id: ID of the user
            **kwargs: Fields to update

        Returns:
            Updated User object

        Raises:
            UserNotFoundError: If the user is not found
        """
        try:
            user = await self._repo.update_user(session, tenant_id, user_id, **kwargs)
            if not user:
                raise UserNotFoundError(user_id)
            await session.commit()
            await session.refresh(user)
            return User.model_validate(user, from_attributes=True)
        except IntegrityError as e:
            await session.rollback()
            if "uq_tenant_user_email" in str(e):
                raise UserExistsError(
                    f"User with email {kwargs['email']} already exists"
                )
            if "uq_tenant_slack_id" in str(e):
                raise UserExistsError(
                    f"User with Slack ID {kwargs['slack_user_id']} already exists"
                )
            if "uq_tenant_teams_id" in str(e):
                raise UserExistsError(
                    f"User with Teams ID {kwargs['teams_user_id']} already exists"
                )
            if "uq_tenant_telegram_id" in str(e):
                raise UserExistsError(
                    f"User with Telegram ID {kwargs['telegram_user_id']} already exists"
                )
            raise UserExistsError("User already exists")

    async def delete_user(
        self, session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Delete a user for a tenant and commit the transaction.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            user_id: ID of the user

        Returns:
            True if user was deleted

        Raises:
            UserNotFoundError: If the user is not found
        """
        deleted = await self._repo.delete_user(session, tenant_id, user_id)
        if not deleted:
            raise UserNotFoundError(user_id)
        await session.commit()
        return deleted

    async def create_group_with_users(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        name: str,
        user_ids: list[uuid.UUID],
    ) -> ReviewerGroup:
        """Create a new reviewer group with initial list of users and commit.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            name: Name of the reviewer group
            user_ids: List of user IDs to add to the group

        Returns:
            The created ReviewerGroup object
        """
        try:
            group = await self._group_repo.create_reviewer_group(
                session=session, tenant_id=tenant_id, name=name
            )
            await session.flush()
        except IntegrityError:
            await session.rollback()
            raise ReviewerGroupExistsError(f"Group with name {name} already exists")
        for user_id in user_ids:
            await self._membership_repo.create_group_membership(
                session=session,
                tenant_id=tenant_id,
                group_id=group.id,
                user_id=user_id,
            )
        await session.commit()
        return ReviewerGroup.model_validate(group, from_attributes=True)

    async def add_user_to_group(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        group_id: uuid.UUID,
        user_id: uuid.UUID,
        priority: int = 0,
    ) -> GroupMembership:
        """Add a user to a group and commit the transaction.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            group_id: ID of the reviewer group
            user_id: ID of the user
            priority: Priority of the user in the group (default: 0)

        Returns:
            The created GroupMembership object
        """
        try:
            membership = await self._membership_repo.create_group_membership(
                session=session,
                tenant_id=tenant_id,
                group_id=group_id,
                user_id=user_id,
                priority=priority,
            )
            await session.commit()
            return GroupMembership.model_validate(membership, from_attributes=True)
        except IntegrityError:
            await session.rollback()
            raise UserAlreadyInGroupError(
                f"User {user_id} is already a member of {group_id} group"
            )

    async def remove_user_from_group(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        group_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Remove a user from a group and commit the transaction.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            group_id: ID of the reviewer group
            user_id: ID of the user

        Returns:
            True if membership was deleted, False if not found
        """
        deleted = await self._membership_repo.delete_group_membership_by_group_and_user(
            session=session,
            tenant_id=tenant_id,
            group_id=group_id,
            user_id=user_id,
        )
        if deleted:
            await session.commit()
        return deleted

    async def list_group_members(
        self, session: AsyncSession, tenant_id: uuid.UUID, group_id: uuid.UUID
    ) -> list[GroupMembership]:
        """List all users in a group for a tenant.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            group_id: ID of the reviewer group

        Returns:
            List of GroupMembership objects for the group
        """
        memberships = await self._membership_repo.list_group_memberships_by_group(
            session=session, tenant_id=tenant_id, group_id=group_id
        )
        return [
            GroupMembership.model_validate(m, from_attributes=True) for m in memberships
        ]

    async def get_user_groups(
        self, session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[ReviewerGroup]:
        """Get all groups a user is a member of for a tenant.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            user_id: ID of the user

        Returns:
            List of ReviewerGroup objects the user belongs to
        """
        membership_group_pairs = (
            await self._membership_repo.list_group_memberships_by_user(
                session=session, tenant_id=tenant_id, user_id=user_id
            )
        )
        return [
            ReviewerGroup.model_validate(group, from_attributes=True)
            for _, group in membership_group_pairs
        ]

    async def list_tenant_groups(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> list[ReviewerGroup]:
        """List all reviewer groups for a tenant.

        Args:
            session: Database session
            tenant_id: ID of the tenant

        Returns:
            List of ReviewerGroup objects for the tenant
        """
        groups = await self._group_repo.list_reviewer_groups(
            session=session, tenant_id=tenant_id
        )
        return [ReviewerGroup.model_validate(g, from_attributes=True) for g in groups]

    async def get_group_by_id(
        self, session: AsyncSession, tenant_id: uuid.UUID, group_id: uuid.UUID
    ) -> ReviewerGroup:
        """Get a reviewer group by ID for a tenant.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            group_id: ID of the reviewer group

        Returns:
            ReviewerGroup object

        Raises:
            ReviewerGroupNotFoundError: If the group is not found
        """
        from service.exceptions import ReviewerGroupNotFoundError

        group = await self._group_repo.get_reviewer_group_by_id(
            session=session, tenant_id=tenant_id, reviewer_group_id=group_id
        )
        if not group:
            raise ReviewerGroupNotFoundError(group_id)
        return ReviewerGroup.model_validate(group, from_attributes=True)

    async def get_membership_by_id(
        self, session: AsyncSession, tenant_id: uuid.UUID, membership_id: uuid.UUID
    ) -> GroupMembership:
        """Get a group membership by ID for a tenant.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            membership_id: ID of the group membership

        Returns:
            GroupMembership object

        Raises:
            GroupMembershipNotFoundError: If the membership is not found
        """
        from service.exceptions import GroupMembershipNotFoundError

        membership = await self._membership_repo.get_group_membership_by_id(
            session=session, tenant_id=tenant_id, membership_id=membership_id
        )
        if not membership:
            raise GroupMembershipNotFoundError(membership_id)
        return GroupMembership.model_validate(membership, from_attributes=True)

    async def delete_group(
        self, session: AsyncSession, tenant_id: uuid.UUID, group_id: uuid.UUID
    ) -> bool:
        """Delete a group for a tenant and commit the transaction.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            group_id: ID of the group

        Returns:
            True if group was deleted

        Raises:
            ReviewerGroupNotFoundError: If the group is not found
        """
        from service.exceptions import ReviewerGroupNotFoundError

        deleted = await self._group_repo.delete_reviewer_group(
            session=session, tenant_id=tenant_id, reviewer_group_id=group_id
        )
        if not deleted:
            raise ReviewerGroupNotFoundError(group_id)
        await session.commit()
        return deleted
