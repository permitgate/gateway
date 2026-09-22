# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User


class UsersRepository:
    """Repository for managing users table operations."""

    async def create_user(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        email: str,
        role: str,
        slack_user_id: str | None = None,
        teams_user_id: str | None = None,
        telegram_user_id: str | None = None,
    ) -> User:
        """Create a new user for a tenant.

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
        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            email=email,
            role=role,
            slack_user_id=slack_user_id,
            teams_user_id=teams_user_id,
            telegram_user_id=telegram_user_id,
        )
        session.add(user)
        return user

    async def get_user_by_id(
        self, session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> User | None:
        """Get a user by ID for a tenant.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            user_id: ID of the user

        Returns:
            User object or None if not found
        """
        result = await session.execute(
            select(User).where((User.id == user_id) & (User.tenant_id == tenant_id))
        )
        return result.scalar_one_or_none()

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
        result = await session.execute(
            select(User).where((User.email == email) & (User.tenant_id == tenant_id))
        )
        return result.scalar_one_or_none()

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
        result = await session.execute(
            select(User).where(User.tenant_id == tenant_id).order_by(User.email)
        )
        return result.scalars().all()

    async def update_user(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        **kwargs,
    ) -> User | None:
        """Update a user for a tenant.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            user_id: ID of the user
            **kwargs: Fields to update

        Returns:
            Updated User object or None if not found
        """
        result = await session.execute(
            select(User).where((User.id == user_id) & (User.tenant_id == tenant_id))
        )
        user = result.scalar_one_or_none()
        if user:
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
        return user

    async def delete_user(
        self, session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Delete a user for a tenant.

        Args:
            session: Database session
            tenant_id: ID of the tenant
            user_id: ID of the user

        Returns:
            True if user was deleted, False if not found
        """
        result = await session.execute(
            select(User).where((User.id == user_id) & (User.tenant_id == tenant_id))
        )
        user = result.scalar_one_or_none()
        if user:
            await session.delete(user)
            return True
        return False
