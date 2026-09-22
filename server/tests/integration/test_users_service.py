# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from db.models import Tenant
from model import UserRole
from service.exceptions import (
    GroupMembershipNotFoundError,
    ReviewerGroupExistsError,
    ReviewerGroupNotFoundError,
    UserAlreadyInGroupError,
    UserExistsError,
    UserNotFoundError,
)
from service.users_service import UsersService


@pytest.fixture
def users_service():
    """Create a UsersService instance."""
    return UsersService()


@pytest.fixture
async def sample_tenant(test_session):
    """Create a sample tenant."""
    tenant = Tenant(id=uuid.uuid4(), name="Test Tenant")
    test_session.add(tenant)
    await test_session.commit()
    return tenant


class TestUsersServiceCreate:
    """Tests for creating users."""

    async def test_create_user_minimal(
        self, users_service, test_session, sample_tenant
    ):
        """Test creating a user with only required fields."""
        user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user@example.com",
        )

        assert user.id is not None
        assert user.tenant_id == sample_tenant.id
        assert user.email == "user@example.com"
        assert user.role == UserRole.REVIEWER
        assert user.slack_user_id is None
        assert user.teams_user_id is None
        assert user.telegram_user_id is None
        assert user.is_active is True

    async def test_create_user_with_all_fields(
        self, users_service, test_session, sample_tenant
    ):
        """Test creating a user with all optional fields."""
        user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="full@example.com",
            role=UserRole.ADMINISTRATOR,
            slack_user_id="U123456",
            teams_user_id="T123456",
            telegram_user_id="TG123456",
        )

        assert user.id is not None
        assert user.email == "full@example.com"
        assert user.role == UserRole.ADMINISTRATOR
        assert user.slack_user_id == "U123456"
        assert user.teams_user_id == "T123456"
        assert user.telegram_user_id == "TG123456"

    async def test_create_user_default_role(
        self, users_service, test_session, sample_tenant
    ):
        """Test creating a user defaults to reviewer role."""
        user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="reviewer@example.com",
        )

        assert user.role == UserRole.REVIEWER

    async def test_create_user_custom_role(
        self, users_service, test_session, sample_tenant
    ):
        """Test creating a user with a custom role."""
        user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="admin@example.com",
            role=UserRole.ADMINISTRATOR,
        )

        assert user.role == UserRole.ADMINISTRATOR

    async def test_create_user_persisted(
        self, users_service, test_session, sample_tenant
    ):
        """Test that created user is persisted in the database."""
        created_user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="persist@example.com",
        )

        retrieved_user = await users_service.get_user(
            test_session, sample_tenant.id, created_user.id
        )

        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == "persist@example.com"


class TestUsersServiceGet:
    """Tests for getting users."""

    async def test_get_user_found(self, users_service, test_session, sample_tenant):
        """Test retrieving an existing user."""
        created_user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="get@example.com",
        )

        retrieved_user = await users_service.get_user(
            test_session, sample_tenant.id, created_user.id
        )

        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == "get@example.com"
        assert retrieved_user.tenant_id == sample_tenant.id

    async def test_get_user_not_found(self, users_service, test_session, sample_tenant):
        """Test retrieving a non-existent user raises exception."""
        user_id = uuid.uuid4()

        with pytest.raises(UserNotFoundError):
            await users_service.get_user(test_session, sample_tenant.id, user_id)

    async def test_get_user_wrong_tenant(self, users_service, test_session):
        """Test that users cannot be accessed by wrong tenant."""
        tenant1 = Tenant(id=uuid.uuid4(), name="Tenant 1")
        tenant2_id = uuid.uuid4()
        test_session.add(tenant1)
        await test_session.commit()

        created_user = await users_service.create_user(
            session=test_session,
            tenant_id=tenant1.id,
            email="isolated@example.com",
        )

        with pytest.raises(UserNotFoundError):
            await users_service.get_user(test_session, tenant2_id, created_user.id)

    async def test_get_user_by_email_found(
        self, users_service, test_session, sample_tenant
    ):
        """Test retrieving a user by email."""
        created_user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="email@example.com",
        )

        retrieved_user = await users_service.get_user_by_email(
            test_session, sample_tenant.id, "email@example.com"
        )

        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == "email@example.com"

    async def test_get_user_by_email_not_found(
        self, users_service, test_session, sample_tenant
    ):
        """Test retrieving a non-existent user by email returns None."""
        result = await users_service.get_user_by_email(
            test_session, sample_tenant.id, "nonexistent@example.com"
        )

        assert result is None

    async def test_get_user_by_email_wrong_tenant(self, users_service, test_session):
        """Test that users by email are isolated per tenant."""
        tenant1 = Tenant(id=uuid.uuid4(), name="Tenant 1")
        tenant2_id = uuid.uuid4()
        test_session.add(tenant1)
        await test_session.commit()

        await users_service.create_user(
            session=test_session,
            tenant_id=tenant1.id,
            email="shared@example.com",
        )

        result = await users_service.get_user_by_email(
            test_session, tenant2_id, "shared@example.com"
        )

        assert result is None


class TestUsersServiceList:
    """Tests for listing users."""

    async def test_list_users_empty(self, users_service, test_session, sample_tenant):
        """Test listing users when none exist."""
        users = await users_service.list_users(test_session, sample_tenant.id)

        assert users == []

    async def test_list_users_single(self, users_service, test_session, sample_tenant):
        """Test listing users with one user."""
        created_user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="single@example.com",
        )

        users = await users_service.list_users(test_session, sample_tenant.id)

        assert len(users) == 1
        assert users[0].id == created_user.id
        assert users[0].email == "single@example.com"

    async def test_list_users_multiple(
        self, users_service, test_session, sample_tenant
    ):
        """Test listing multiple users."""
        user1 = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="alice@example.com",
        )

        user2 = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="bob@example.com",
            role=UserRole.ADMINISTRATOR,
        )

        users = await users_service.list_users(test_session, sample_tenant.id)

        assert len(users) == 2
        user_ids = [u.id for u in users]
        assert user1.id in user_ids
        assert user2.id in user_ids

    async def test_list_users_ordered_by_email(
        self, users_service, test_session, sample_tenant
    ):
        """Test that users are returned ordered by email."""
        await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="zebra@example.com",
        )

        await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="alice@example.com",
        )

        await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="bob@example.com",
        )

        users = await users_service.list_users(test_session, sample_tenant.id)

        assert len(users) == 3
        assert users[0].email == "alice@example.com"
        assert users[1].email == "bob@example.com"
        assert users[2].email == "zebra@example.com"

    async def test_list_users_tenant_isolation(self, users_service, test_session):
        """Test that users are isolated per tenant."""
        tenant1 = Tenant(id=uuid.uuid4(), name="Tenant 1")
        tenant2 = Tenant(id=uuid.uuid4(), name="Tenant 2")
        test_session.add(tenant1)
        test_session.add(tenant2)
        await test_session.commit()

        await users_service.create_user(
            session=test_session,
            tenant_id=tenant1.id,
            email="tenant1@example.com",
        )

        await users_service.create_user(
            session=test_session,
            tenant_id=tenant2.id,
            email="tenant2@example.com",
        )

        users_tenant1 = await users_service.list_users(test_session, tenant1.id)
        users_tenant2 = await users_service.list_users(test_session, tenant2.id)

        assert len(users_tenant1) == 1
        assert len(users_tenant2) == 1
        assert users_tenant1[0].email == "tenant1@example.com"
        assert users_tenant2[0].email == "tenant2@example.com"


class TestUsersServiceUpdate:
    """Tests for updating users."""

    async def test_update_user_email(self, users_service, test_session, sample_tenant):
        """Test updating a user's email."""
        created_user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="original@example.com",
        )

        updated_user = await users_service.update_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            user_id=created_user.id,
            email="updated@example.com",
        )

        assert updated_user.id == created_user.id
        assert updated_user.email == "updated@example.com"

    async def test_update_user_role(self, users_service, test_session, sample_tenant):
        """Test updating a user's role."""
        created_user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user@example.com",
            role=UserRole.REVIEWER,
        )

        updated_user = await users_service.update_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            user_id=created_user.id,
            role=UserRole.ADMINISTRATOR,
        )

        assert updated_user.role == UserRole.ADMINISTRATOR

    async def test_update_user_slack_id(
        self, users_service, test_session, sample_tenant
    ):
        """Test updating a user's Slack ID."""
        created_user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user@example.com",
        )

        updated_user = await users_service.update_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            user_id=created_user.id,
            slack_user_id="U789012",
        )

        assert updated_user.slack_user_id == "U789012"

    async def test_update_user_multiple_fields(
        self, users_service, test_session, sample_tenant
    ):
        """Test updating multiple fields at once."""
        created_user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user@example.com",
            role=UserRole.REVIEWER,
        )

        updated_user = await users_service.update_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            user_id=created_user.id,
            email="new@example.com",
            role=UserRole.ADMINISTRATOR,
            slack_user_id="U111111",
            teams_user_id="T222222",
        )

        assert updated_user.email == "new@example.com"
        assert updated_user.role == UserRole.ADMINISTRATOR
        assert updated_user.slack_user_id == "U111111"
        assert updated_user.teams_user_id == "T222222"

    async def test_update_user_is_active(
        self, users_service, test_session, sample_tenant
    ):
        """Test updating a user's active status."""
        created_user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user@example.com",
        )

        updated_user = await users_service.update_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            user_id=created_user.id,
            is_active=False,
        )

        assert updated_user.is_active is False

    async def test_update_user_not_found(
        self, users_service, test_session, sample_tenant
    ):
        """Test updating a non-existent user raises exception."""
        user_id = uuid.uuid4()

        with pytest.raises(UserNotFoundError):
            await users_service.update_user(
                session=test_session,
                tenant_id=sample_tenant.id,
                user_id=user_id,
                email="updated@example.com",
            )

    async def test_update_user_wrong_tenant(self, users_service, test_session):
        """Test that users cannot be updated by wrong tenant."""
        tenant1 = Tenant(id=uuid.uuid4(), name="Tenant 1")
        tenant2_id = uuid.uuid4()
        test_session.add(tenant1)
        await test_session.commit()

        created_user = await users_service.create_user(
            session=test_session,
            tenant_id=tenant1.id,
            email="user@example.com",
        )

        with pytest.raises(UserNotFoundError):
            await users_service.update_user(
                session=test_session,
                tenant_id=tenant2_id,
                user_id=created_user.id,
                email="updated@example.com",
            )

    async def test_update_user_persisted(
        self, users_service, test_session, sample_tenant
    ):
        """Test that user updates are persisted in the database."""
        created_user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="original@example.com",
        )

        await users_service.update_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            user_id=created_user.id,
            email="persisted@example.com",
        )

        retrieved_user = await users_service.get_user(
            test_session, sample_tenant.id, created_user.id
        )

        assert retrieved_user.email == "persisted@example.com"


class TestUsersServiceDelete:
    """Tests for deleting users."""

    async def test_delete_user(self, users_service, test_session, sample_tenant):
        """Test deleting a user."""
        created_user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="delete@example.com",
        )

        result = await users_service.delete_user(
            test_session, sample_tenant.id, created_user.id
        )

        assert result is True

    async def test_delete_user_not_found(
        self, users_service, test_session, sample_tenant
    ):
        """Test deleting a non-existent user raises exception."""
        user_id = uuid.uuid4()

        with pytest.raises(UserNotFoundError):
            await users_service.delete_user(test_session, sample_tenant.id, user_id)

    async def test_delete_user_wrong_tenant(self, users_service, test_session):
        """Test that users cannot be deleted by wrong tenant."""
        tenant1 = Tenant(id=uuid.uuid4(), name="Tenant 1")
        tenant2_id = uuid.uuid4()
        test_session.add(tenant1)
        await test_session.commit()

        created_user = await users_service.create_user(
            session=test_session,
            tenant_id=tenant1.id,
            email="user@example.com",
        )

        with pytest.raises(UserNotFoundError):
            await users_service.delete_user(test_session, tenant2_id, created_user.id)

    async def test_delete_user_persisted(
        self, users_service, test_session, sample_tenant
    ):
        """Test that user deletion is persisted in the database."""
        created_user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="deleted@example.com",
        )

        await users_service.delete_user(test_session, sample_tenant.id, created_user.id)

        with pytest.raises(UserNotFoundError):
            await users_service.get_user(
                test_session, sample_tenant.id, created_user.id
            )

    async def test_delete_one_user_does_not_affect_others(
        self, users_service, test_session, sample_tenant
    ):
        """Test that deleting one user doesn't affect others."""
        user1 = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user1@example.com",
        )

        user2 = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user2@example.com",
        )

        await users_service.delete_user(test_session, sample_tenant.id, user1.id)

        users = await users_service.list_users(test_session, sample_tenant.id)

        assert len(users) == 1
        assert users[0].id == user2.id


class TestUsersServiceTenantIsolation:
    """Tests for tenant isolation."""

    async def test_create_users_different_tenants(self, users_service, test_session):
        """Test creating users for different tenants."""
        tenant1 = Tenant(id=uuid.uuid4(), name="Tenant 1")
        tenant2 = Tenant(id=uuid.uuid4(), name="Tenant 2")
        test_session.add(tenant1)
        test_session.add(tenant2)
        await test_session.commit()

        user1 = await users_service.create_user(
            session=test_session,
            tenant_id=tenant1.id,
            email="user@example.com",
        )

        user2 = await users_service.create_user(
            session=test_session,
            tenant_id=tenant2.id,
            email="user@example.com",
        )

        assert user1.id != user2.id
        assert user1.tenant_id != user2.tenant_id

    async def test_same_email_different_tenants(self, users_service, test_session):
        """Test that same email can exist in different tenants."""
        tenant1 = Tenant(id=uuid.uuid4(), name="Tenant 1")
        tenant2 = Tenant(id=uuid.uuid4(), name="Tenant 2")
        test_session.add(tenant1)
        test_session.add(tenant2)
        await test_session.commit()

        user1 = await users_service.create_user(
            session=test_session,
            tenant_id=tenant1.id,
            email="same@example.com",
        )

        user2 = await users_service.create_user(
            session=test_session,
            tenant_id=tenant2.id,
            email="same@example.com",
        )

        # Both users should exist
        retrieved_user1 = await users_service.get_user_by_email(
            test_session, tenant1.id, "same@example.com"
        )
        retrieved_user2 = await users_service.get_user_by_email(
            test_session, tenant2.id, "same@example.com"
        )

        assert retrieved_user1 is not None
        assert retrieved_user2 is not None
        assert retrieved_user1.id == user1.id
        assert retrieved_user2.id == user2.id


class TestUsersServiceRoles:
    """Tests for user roles."""

    @pytest.mark.parametrize("role", [UserRole.REVIEWER, UserRole.ADMINISTRATOR])
    async def test_create_user_with_role(
        self, users_service, test_session, sample_tenant, role
    ):
        """Test creating users with different roles."""
        user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email=f"user_{role}@example.com",
            role=role,
        )

        assert user.role == role

    async def test_update_user_between_roles(
        self, users_service, test_session, sample_tenant
    ):
        """Test updating user role from reviewer to administrator and back."""
        user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="role@example.com",
            role=UserRole.REVIEWER,
        )

        admin_user = await users_service.update_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            user_id=user.id,
            role=UserRole.ADMINISTRATOR,
        )

        assert admin_user.role == UserRole.ADMINISTRATOR

        reviewer_user = await users_service.update_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            user_id=user.id,
            role=UserRole.REVIEWER,
        )

        assert reviewer_user.role == UserRole.REVIEWER


class TestUsersServiceGroupManagement:
    """Tests for reviewer group management."""

    async def test_create_group_with_users_empty(
        self, users_service, test_session, sample_tenant
    ):
        """Test creating a group without initial users."""
        group = await users_service.create_group_with_users(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Test Group",
            user_ids=[],
        )

        assert group.id is not None
        assert group.tenant_id == sample_tenant.id
        assert group.name == "Test Group"

    async def test_create_group_with_single_user(
        self, users_service, test_session, sample_tenant
    ):
        """Test creating a group with a single user."""
        user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user1@example.com",
        )

        group = await users_service.create_group_with_users(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Group 1",
            user_ids=[user.id],
        )

        members = await users_service.list_group_members(
            test_session, sample_tenant.id, group.id
        )

        assert len(members) == 1
        assert members[0].user_id == user.id

    async def test_create_group_with_multiple_users(
        self, users_service, test_session, sample_tenant
    ):
        """Test creating a group with multiple users."""
        user1 = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user1@example.com",
        )

        user2 = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user2@example.com",
        )

        user3 = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user3@example.com",
        )

        group = await users_service.create_group_with_users(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Group 1",
            user_ids=[user1.id, user2.id, user3.id],
        )

        members = await users_service.list_group_members(
            test_session, sample_tenant.id, group.id
        )

        assert len(members) == 3
        member_ids = [m.user_id for m in members]
        assert user1.id in member_ids
        assert user2.id in member_ids
        assert user3.id in member_ids


class TestUsersServiceAddRemoveUser:
    """Tests for adding and removing users from groups."""

    async def test_add_user_to_group(self, users_service, test_session, sample_tenant):
        """Test adding a user to a group."""
        user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user@example.com",
        )

        group = await users_service.create_group_with_users(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Group 1",
            user_ids=[],
        )

        membership = await users_service.add_user_to_group(
            session=test_session,
            tenant_id=sample_tenant.id,
            group_id=group.id,
            user_id=user.id,
        )

        assert membership.group_id == group.id
        assert membership.user_id == user.id
        assert membership.priority == 0

    async def test_add_user_to_group_with_priority(
        self, users_service, test_session, sample_tenant
    ):
        """Test adding a user to a group with custom priority."""
        user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user@example.com",
        )

        group = await users_service.create_group_with_users(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Group 1",
            user_ids=[],
        )

        membership = await users_service.add_user_to_group(
            session=test_session,
            tenant_id=sample_tenant.id,
            group_id=group.id,
            user_id=user.id,
            priority=5,
        )

        assert membership.priority == 5

    async def test_remove_user_from_group(
        self, users_service, test_session, sample_tenant
    ):
        """Test removing a user from a group."""
        user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user@example.com",
        )

        group = await users_service.create_group_with_users(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Group 1",
            user_ids=[user.id],
        )

        result = await users_service.remove_user_from_group(
            session=test_session,
            tenant_id=sample_tenant.id,
            group_id=group.id,
            user_id=user.id,
        )

        assert result is True

        members = await users_service.list_group_members(
            test_session, sample_tenant.id, group.id
        )
        assert len(members) == 0

    async def test_remove_user_not_in_group(
        self, users_service, test_session, sample_tenant
    ):
        """Test removing a user that is not in the group returns False."""
        user1 = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user1@example.com",
        )

        user2 = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user2@example.com",
        )

        group = await users_service.create_group_with_users(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Group 1",
            user_ids=[user1.id],
        )

        result = await users_service.remove_user_from_group(
            session=test_session,
            tenant_id=sample_tenant.id,
            group_id=group.id,
            user_id=user2.id,
        )

        assert result is False


class TestUsersServiceListGroupMembers:
    """Tests for listing group members."""

    async def test_list_group_members_empty(
        self, users_service, test_session, sample_tenant
    ):
        """Test listing members when group has no members."""
        group = await users_service.create_group_with_users(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Empty Group",
            user_ids=[],
        )

        members = await users_service.list_group_members(
            test_session, sample_tenant.id, group.id
        )

        assert members == []

    async def test_list_group_members_multiple(
        self, users_service, test_session, sample_tenant
    ):
        """Test listing multiple group members."""
        user1 = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user1@example.com",
        )

        user2 = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user2@example.com",
        )

        group = await users_service.create_group_with_users(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Group 1",
            user_ids=[user1.id, user2.id],
        )

        members = await users_service.list_group_members(
            test_session, sample_tenant.id, group.id
        )

        assert len(members) == 2
        user_ids = [m.user_id for m in members]
        assert user1.id in user_ids
        assert user2.id in user_ids

    async def test_list_group_members_tenant_isolation(
        self, users_service, test_session
    ):
        """Test that group members are isolated per tenant."""
        tenant1 = Tenant(id=uuid.uuid4(), name="Tenant 1")
        tenant2 = Tenant(id=uuid.uuid4(), name="Tenant 2")
        test_session.add(tenant1)
        test_session.add(tenant2)
        await test_session.commit()

        user1_t1 = await users_service.create_user(
            session=test_session,
            tenant_id=tenant1.id,
            email="user1@example.com",
        )

        user1_t2 = await users_service.create_user(
            session=test_session,
            tenant_id=tenant2.id,
            email="user1@example.com",
        )

        group_t1 = await users_service.create_group_with_users(
            session=test_session,
            tenant_id=tenant1.id,
            name="Group 1",
            user_ids=[user1_t1.id],
        )

        group_t2 = await users_service.create_group_with_users(
            session=test_session,
            tenant_id=tenant2.id,
            name="Group 1",
            user_ids=[user1_t2.id],
        )

        members_t1 = await users_service.list_group_members(
            test_session, tenant1.id, group_t1.id
        )
        members_t2 = await users_service.list_group_members(
            test_session, tenant2.id, group_t2.id
        )

        assert len(members_t1) == 1
        assert len(members_t2) == 1
        assert members_t1[0].user_id == user1_t1.id
        assert members_t2[0].user_id == user1_t2.id


class TestUsersServiceUserGroups:
    """Tests for getting user groups."""

    async def test_get_user_groups_empty(
        self, users_service, test_session, sample_tenant
    ):
        """Test getting groups for user with no groups."""
        user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user@example.com",
        )

        groups = await users_service.get_user_groups(
            test_session, sample_tenant.id, user.id
        )

        assert groups == []

    async def test_get_user_groups_single(
        self, users_service, test_session, sample_tenant
    ):
        """Test getting groups for user in a single group."""
        user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user@example.com",
        )

        group = await users_service.create_group_with_users(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Group 1",
            user_ids=[user.id],
        )

        groups = await users_service.get_user_groups(
            test_session, sample_tenant.id, user.id
        )

        assert len(groups) == 1
        assert groups[0].id == group.id
        assert groups[0].name == "Group 1"

    async def test_get_user_groups_multiple(
        self, users_service, test_session, sample_tenant
    ):
        """Test getting multiple groups for a user."""
        user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user@example.com",
        )

        group1 = await users_service.create_group_with_users(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Group 1",
            user_ids=[user.id],
        )

        group2 = await users_service.create_group_with_users(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Group 2",
            user_ids=[user.id],
        )

        groups = await users_service.get_user_groups(
            test_session, sample_tenant.id, user.id
        )

        assert len(groups) == 2
        group_ids = [g.id for g in groups]
        assert group1.id in group_ids
        assert group2.id in group_ids


class TestUsersServiceListTenantGroups:
    """Tests for listing tenant groups."""

    async def test_list_tenant_groups_empty(
        self, users_service, test_session, sample_tenant
    ):
        """Test listing groups when none exist."""
        groups = await users_service.list_tenant_groups(test_session, sample_tenant.id)

        assert groups == []

    async def test_list_tenant_groups_single(
        self, users_service, test_session, sample_tenant
    ):
        """Test listing groups with a single group."""
        group = await users_service.create_group_with_users(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Group 1",
            user_ids=[],
        )

        groups = await users_service.list_tenant_groups(test_session, sample_tenant.id)

        assert len(groups) == 1
        assert groups[0].id == group.id
        assert groups[0].name == "Group 1"

    async def test_list_tenant_groups_multiple(
        self, users_service, test_session, sample_tenant
    ):
        """Test listing multiple groups."""
        group1 = await users_service.create_group_with_users(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Group A",
            user_ids=[],
        )

        group2 = await users_service.create_group_with_users(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Group B",
            user_ids=[],
        )

        groups = await users_service.list_tenant_groups(test_session, sample_tenant.id)

        assert len(groups) == 2
        group_ids = [g.id for g in groups]
        assert group1.id in group_ids
        assert group2.id in group_ids

    async def test_list_tenant_groups_isolation(self, users_service, test_session):
        """Test that groups are isolated per tenant."""
        tenant1 = Tenant(id=uuid.uuid4(), name="Tenant 1")
        tenant2 = Tenant(id=uuid.uuid4(), name="Tenant 2")
        test_session.add(tenant1)
        test_session.add(tenant2)
        await test_session.commit()

        group1 = await users_service.create_group_with_users(
            session=test_session,
            tenant_id=tenant1.id,
            name="Group 1",
            user_ids=[],
        )

        group2 = await users_service.create_group_with_users(
            session=test_session,
            tenant_id=tenant2.id,
            name="Group 1",
            user_ids=[],
        )

        groups_t1 = await users_service.list_tenant_groups(test_session, tenant1.id)
        groups_t2 = await users_service.list_tenant_groups(test_session, tenant2.id)

        assert len(groups_t1) == 1
        assert len(groups_t2) == 1
        assert groups_t1[0].id == group1.id
        assert groups_t2[0].id == group2.id


class TestUsersServiceGetGroupById:
    """Tests for getting a group by ID."""

    async def test_get_group_by_id_found(
        self, users_service, test_session, sample_tenant
    ):
        """Test getting an existing group by ID."""
        group = await users_service.create_group_with_users(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Test Group",
            user_ids=[],
        )

        retrieved_group = await users_service.get_group_by_id(
            test_session, sample_tenant.id, group.id
        )

        assert retrieved_group.id == group.id
        assert retrieved_group.name == "Test Group"
        assert retrieved_group.tenant_id == sample_tenant.id

    async def test_get_group_by_id_not_found(
        self, users_service, test_session, sample_tenant
    ):
        """Test getting a non-existent group raises exception."""
        group_id = uuid.uuid4()

        with pytest.raises(ReviewerGroupNotFoundError):
            await users_service.get_group_by_id(
                test_session, sample_tenant.id, group_id
            )

    async def test_get_group_by_id_wrong_tenant(self, users_service, test_session):
        """Test that groups cannot be accessed by wrong tenant."""
        tenant1 = Tenant(id=uuid.uuid4(), name="Tenant 1")
        tenant2_id = uuid.uuid4()
        test_session.add(tenant1)
        await test_session.commit()

        group = await users_service.create_group_with_users(
            session=test_session,
            tenant_id=tenant1.id,
            name="Group 1",
            user_ids=[],
        )

        with pytest.raises(ReviewerGroupNotFoundError):
            await users_service.get_group_by_id(test_session, tenant2_id, group.id)


class TestUsersServiceGetMembershipById:
    """Tests for getting a membership by ID."""

    async def test_get_membership_by_id_found(
        self, users_service, test_session, sample_tenant
    ):
        """Test getting an existing membership by ID."""
        user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user@example.com",
        )

        group = await users_service.create_group_with_users(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Group 1",
            user_ids=[user.id],
        )

        members = await users_service.list_group_members(
            test_session, sample_tenant.id, group.id
        )
        membership_id = members[0].id

        retrieved_membership = await users_service.get_membership_by_id(
            test_session, sample_tenant.id, membership_id
        )

        assert retrieved_membership.id == membership_id
        assert retrieved_membership.user_id == user.id
        assert retrieved_membership.group_id == group.id

    async def test_get_membership_by_id_not_found(
        self, users_service, test_session, sample_tenant
    ):
        """Test getting a non-existent membership raises exception."""
        membership_id = uuid.uuid4()

        with pytest.raises(GroupMembershipNotFoundError):
            await users_service.get_membership_by_id(
                test_session, sample_tenant.id, membership_id
            )

    async def test_get_membership_by_id_wrong_tenant(self, users_service, test_session):
        """Test that memberships cannot be accessed by wrong tenant."""
        tenant1 = Tenant(id=uuid.uuid4(), name="Tenant 1")
        tenant2_id = uuid.uuid4()
        test_session.add(tenant1)
        await test_session.commit()

        user = await users_service.create_user(
            session=test_session,
            tenant_id=tenant1.id,
            email="user@example.com",
        )

        group = await users_service.create_group_with_users(
            session=test_session,
            tenant_id=tenant1.id,
            name="Group 1",
            user_ids=[user.id],
        )

        members = await users_service.list_group_members(
            test_session, tenant1.id, group.id
        )
        membership_id = members[0].id

        with pytest.raises(GroupMembershipNotFoundError):
            await users_service.get_membership_by_id(
                test_session, tenant2_id, membership_id
            )


class TestUsersServiceIntegrityErrors:
    """Tests for IntegrityError handling in the users service."""

    async def test_create_user_duplicate_email(
        self, users_service, test_session, sample_tenant
    ):
        """Test creating a user with a duplicate email raises UserExistsError."""
        await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="duplicate@example.com",
        )

        with pytest.raises(UserExistsError) as exc_info:
            await users_service.create_user(
                session=test_session,
                tenant_id=sample_tenant.id,
                email="duplicate@example.com",
            )

        assert "already exists" in str(exc_info.value)

    async def test_create_user_duplicate_slack_id(
        self, users_service, test_session, sample_tenant
    ):
        """Test creating a user with a duplicate Slack ID raises UserExistsError."""
        await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user1@example.com",
            slack_user_id="U123456",
        )

        with pytest.raises(UserExistsError) as exc_info:
            await users_service.create_user(
                session=test_session,
                tenant_id=sample_tenant.id,
                email="user2@example.com",
                slack_user_id="U123456",
            )

        assert "Slack ID" in str(exc_info.value)

    async def test_create_user_duplicate_teams_id(
        self, users_service, test_session, sample_tenant
    ):
        """Test creating a user with a duplicate Teams ID raises UserExistsError."""
        await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user1@example.com",
            teams_user_id="T123456",
        )

        with pytest.raises(UserExistsError) as exc_info:
            await users_service.create_user(
                session=test_session,
                tenant_id=sample_tenant.id,
                email="user2@example.com",
                teams_user_id="T123456",
            )

        assert "Teams ID" in str(exc_info.value)

    async def test_create_user_duplicate_telegram_id(
        self, users_service, test_session, sample_tenant
    ):
        """Test creating a user with a duplicate Telegram ID raises UserExistsError."""
        await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user1@example.com",
            telegram_user_id="TG123456",
        )

        with pytest.raises(UserExistsError) as exc_info:
            await users_service.create_user(
                session=test_session,
                tenant_id=sample_tenant.id,
                email="user2@example.com",
                telegram_user_id="TG123456",
            )

        assert "Telegram ID" in str(exc_info.value)

    async def test_update_user_duplicate_email(
        self, users_service, test_session, sample_tenant
    ):
        """Test updating a user to a duplicate email raises UserExistsError."""
        user1 = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user1@example.com",
        )

        await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user2@example.com",
        )

        with pytest.raises(UserExistsError) as exc_info:
            await users_service.update_user(
                session=test_session,
                tenant_id=sample_tenant.id,
                user_id=user1.id,
                email="user2@example.com",
            )

        assert "already exists" in str(exc_info.value)

    async def test_update_user_duplicate_slack_id(
        self, users_service, test_session, sample_tenant
    ):
        """Test updating a user to a duplicate Slack ID raises UserExistsError."""
        user1 = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user1@example.com",
        )

        await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user2@example.com",
            slack_user_id="U123456",
        )

        with pytest.raises(UserExistsError) as exc_info:
            await users_service.update_user(
                session=test_session,
                tenant_id=sample_tenant.id,
                user_id=user1.id,
                slack_user_id="U123456",
            )

        assert "Slack ID" in str(exc_info.value)

    async def test_create_group_duplicate_name(
        self, users_service, test_session, sample_tenant
    ):
        """Test creating a group with a duplicate name raises ReviewerGroupExistsError."""
        await users_service.create_group_with_users(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Duplicate Group",
            user_ids=[],
        )

        with pytest.raises(ReviewerGroupExistsError) as exc_info:
            await users_service.create_group_with_users(
                session=test_session,
                tenant_id=sample_tenant.id,
                name="Duplicate Group",
                user_ids=[],
            )

        assert "already exists" in str(exc_info.value)

    async def test_add_user_to_group_duplicate_membership(
        self, users_service, test_session, sample_tenant
    ):
        """Test adding a user to a group twice raises UserAlreadyInGroupError."""
        user = await users_service.create_user(
            session=test_session,
            tenant_id=sample_tenant.id,
            email="user@example.com",
        )

        group = await users_service.create_group_with_users(
            session=test_session,
            tenant_id=sample_tenant.id,
            name="Group 1",
            user_ids=[user.id],
        )

        with pytest.raises(UserAlreadyInGroupError) as exc_info:
            await users_service.add_user_to_group(
                session=test_session,
                tenant_id=sample_tenant.id,
                group_id=group.id,
                user_id=user.id,
            )

        assert "already a member" in str(exc_info.value)
