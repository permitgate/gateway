# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api.users import group_router, router
from db import get_session
from db.models import GroupMembership, ReviewerGroup, User
from service.exceptions import (
    ReviewerGroupExistsError,
    ReviewerGroupNotFoundError,
    UserAlreadyInGroupError,
    UserExistsError,
    UserNotFoundError,
)


@pytest.fixture
def client(mock_session):
    """Create a test client for the users router."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    app.include_router(group_router)

    # Mock the get_session dependency
    app.dependency_overrides[get_session] = lambda: mock_session

    return TestClient(app)


@pytest.fixture
def sample_tenant_id():
    """Create a sample tenant ID."""
    return uuid.uuid4()


@pytest.fixture
def sample_user_id():
    """Create a sample user ID."""
    return uuid.uuid4()


@pytest.fixture
def sample_user(sample_tenant_id, sample_user_id):
    """Create a sample User object."""
    return User(
        id=sample_user_id,
        tenant_id=sample_tenant_id,
        email="test@example.com",
        role="reviewer",
        slack_user_id="U123456",
        teams_user_id="T123456",
        telegram_user_id="TG123456",
        is_active=True,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )


@patch("api.users.service")
def test_create_user(mock_service, client, sample_user, sample_tenant_id):
    """Test creating a new user."""
    mock_service.create_user = AsyncMock(return_value=sample_user)

    payload = {
        "email": "test@example.com",
        "role": "reviewer",
        "slack_user_id": "U123456",
        "teams_user_id": "T123456",
        "telegram_user_id": "TG123456",
    }

    response = client.post(f"/tenants/{sample_tenant_id}/users/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == str(sample_user.id)
    assert data["email"] == "test@example.com"
    mock_service.create_user.assert_called_once()


@patch("api.users.service")
def test_create_user_minimal(mock_service, client, sample_user, sample_tenant_id):
    """Test creating a user with minimal fields."""
    minimal_user = User(
        id=uuid.uuid4(),
        tenant_id=sample_tenant_id,
        email="minimal@example.com",
        role="reviewer",
        is_active=True,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )
    mock_service.create_user = AsyncMock(return_value=minimal_user)

    payload = {"email": "minimal@example.com"}

    response = client.post(f"/tenants/{sample_tenant_id}/users/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "minimal@example.com"


@patch("api.users.service")
def test_create_user_already_exists(mock_service, client, sample_tenant_id):
    """Test creating a user that already exists."""
    mock_service.create_user = AsyncMock(
        side_effect=UserExistsError("User with email test@example.com already exists")
    )

    payload = {
        "email": "test@example.com",
        "role": "reviewer",
    }

    response = client.post(f"/tenants/{sample_tenant_id}/users/", json=payload)

    assert response.status_code == 409
    data = response.json()
    assert "already exists" in data["detail"]


@patch("api.users.service")
def test_create_user_duplicate_slack_id(mock_service, client, sample_tenant_id):
    """Test creating a user with duplicate Slack ID."""
    mock_service.create_user = AsyncMock(
        side_effect=UserExistsError("User with Slack ID U123456 already exists")
    )

    payload = {
        "email": "new@example.com",
        "slack_user_id": "U123456",
    }

    response = client.post(f"/tenants/{sample_tenant_id}/users/", json=payload)

    assert response.status_code == 409
    data = response.json()
    assert "Slack ID" in data["detail"]


@patch("api.users.service")
def test_list_users(mock_service, client, sample_user, sample_tenant_id):
    """Test listing all users for a tenant."""
    mock_service.list_users = AsyncMock(return_value=[sample_user])

    response = client.get(f"/tenants/{sample_tenant_id}/users/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(sample_user.id)
    assert data[0]["email"] == "test@example.com"
    mock_service.list_users.assert_called_once()


@patch("api.users.service")
def test_list_users_empty(mock_service, client, sample_tenant_id):
    """Test listing users when none exist."""
    mock_service.list_users = AsyncMock(return_value=[])

    response = client.get(f"/tenants/{sample_tenant_id}/users/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0


@patch("api.users.service")
def test_get_user(mock_service, client, sample_user, sample_tenant_id):
    """Test getting a specific user."""
    mock_service.get_user = AsyncMock(return_value=sample_user)

    response = client.get(f"/tenants/{sample_tenant_id}/users/{sample_user.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_user.id)
    assert data["email"] == "test@example.com"
    mock_service.get_user.assert_called_once()


@patch("api.users.service")
def test_get_user_not_found(mock_service, client, sample_tenant_id):
    """Test getting a non-existent user."""
    user_id = uuid.uuid4()
    mock_service.get_user = AsyncMock(side_effect=UserNotFoundError(user_id))

    response = client.get(f"/tenants/{sample_tenant_id}/users/{user_id}")

    assert response.status_code == 404
    data = response.json()
    assert "User not found" in data["detail"]


@patch("api.users.service")
def test_update_user(mock_service, client, sample_user, sample_tenant_id):
    """Test updating a user."""
    updated_user = User(
        id=sample_user.id,
        tenant_id=sample_tenant_id,
        email="updated@example.com",
        role="administrator",
        slack_user_id=sample_user.slack_user_id,
        teams_user_id=sample_user.teams_user_id,
        telegram_user_id=sample_user.telegram_user_id,
        is_active=True,
        created_at=sample_user.created_at,
        updated_at=datetime.now(tz=UTC),
    )
    mock_service.update_user = AsyncMock(return_value=updated_user)

    payload = {
        "email": "updated@example.com",
        "role": "administrator",
    }

    response = client.put(
        f"/tenants/{sample_tenant_id}/users/{sample_user.id}", json=payload
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_user.id)
    assert data["email"] == "updated@example.com"
    assert data["role"] == "administrator"
    mock_service.update_user.assert_called_once()


@patch("api.users.service")
def test_update_user_partial(mock_service, client, sample_user, sample_tenant_id):
    """Test updating only specific user fields."""
    updated_user = User(
        id=sample_user.id,
        tenant_id=sample_tenant_id,
        email=sample_user.email,
        role="administrator",
        slack_user_id=sample_user.slack_user_id,
        teams_user_id=sample_user.teams_user_id,
        telegram_user_id=sample_user.telegram_user_id,
        is_active=True,
        created_at=sample_user.created_at,
        updated_at=datetime.now(tz=UTC),
    )
    mock_service.update_user = AsyncMock(return_value=updated_user)

    payload = {"role": "administrator"}

    response = client.put(
        f"/tenants/{sample_tenant_id}/users/{sample_user.id}", json=payload
    )

    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "administrator"


@patch("api.users.service")
def test_update_user_rejects_null_email(
    mock_service, client, sample_user, sample_tenant_id
):
    """Test updating a user rejects an explicit null email."""
    payload = {"email": None}

    response = client.put(
        f"/tenants/{sample_tenant_id}/users/{sample_user.id}", json=payload
    )

    assert response.status_code == 422
    assert any(
        "email may be omitted, but cannot be null" in error["msg"]
        for error in response.json()["detail"]
    )
    mock_service.update_user.assert_not_called()


@patch("api.users.service")
def test_update_user_not_found(mock_service, client, sample_tenant_id):
    """Test updating a non-existent user."""
    user_id = uuid.uuid4()
    mock_service.update_user = AsyncMock(side_effect=UserNotFoundError(user_id))

    payload = {"role": "administrator"}

    response = client.put(f"/tenants/{sample_tenant_id}/users/{user_id}", json=payload)

    assert response.status_code == 404
    data = response.json()
    assert "User not found" in data["detail"]


@patch("api.users.service")
def test_update_user_duplicate_email(
    mock_service, client, sample_user, sample_tenant_id
):
    """Test updating a user with a duplicate email."""
    mock_service.update_user = AsyncMock(
        side_effect=UserExistsError(
            "User with email existing@example.com already exists"
        )
    )

    payload = {"email": "existing@example.com"}

    response = client.put(
        f"/tenants/{sample_tenant_id}/users/{sample_user.id}", json=payload
    )

    assert response.status_code == 409
    data = response.json()
    assert "already exists" in data["detail"]


@patch("api.users.service")
def test_update_user_duplicate_teams_id(
    mock_service, client, sample_user, sample_tenant_id
):
    """Test updating a user with a duplicate Teams ID."""
    mock_service.update_user = AsyncMock(
        side_effect=UserExistsError("User with Teams ID T123456 already exists")
    )

    payload = {"teams_user_id": "T123456"}

    response = client.put(
        f"/tenants/{sample_tenant_id}/users/{sample_user.id}", json=payload
    )

    assert response.status_code == 409
    data = response.json()
    assert "Teams ID" in data["detail"]


@patch("api.users.service")
def test_delete_user(mock_service, client, sample_user, sample_tenant_id):
    """Test deleting a user."""
    mock_service.delete_user = AsyncMock(return_value=True)

    response = client.delete(f"/tenants/{sample_tenant_id}/users/{sample_user.id}")

    assert response.status_code == 204
    mock_service.delete_user.assert_called_once()


@patch("api.users.service")
def test_delete_user_not_found(mock_service, client, sample_tenant_id):
    """Test deleting a non-existent user."""
    user_id = uuid.uuid4()
    mock_service.delete_user = AsyncMock(side_effect=UserNotFoundError(user_id))

    response = client.delete(f"/tenants/{sample_tenant_id}/users/{user_id}")

    assert response.status_code == 404
    data = response.json()
    assert "User not found" in data["detail"]


@patch("api.users.service")
def test_list_multiple_users(mock_service, client, sample_tenant_id):
    """Test listing multiple users."""
    users = [
        User(
            id=uuid.uuid4(),
            tenant_id=sample_tenant_id,
            email="user1@example.com",
            role="reviewer",
            is_active=True,
            created_at=datetime.now(tz=UTC),
            updated_at=datetime.now(tz=UTC),
        ),
        User(
            id=uuid.uuid4(),
            tenant_id=sample_tenant_id,
            email="user2@example.com",
            role="administrator",
            is_active=True,
            created_at=datetime.now(tz=UTC),
            updated_at=datetime.now(tz=UTC),
        ),
    ]
    mock_service.list_users = AsyncMock(return_value=users)

    response = client.get(f"/tenants/{sample_tenant_id}/users/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["email"] == "user1@example.com"
    assert data[1]["email"] == "user2@example.com"
    assert data[0]["role"] == "reviewer"
    assert data[1]["role"] == "administrator"


@patch("api.users.service")
def test_deactivate_user(mock_service, client, sample_user, sample_tenant_id):
    """Test deactivating a user."""
    deactivated_user = User(
        id=sample_user.id,
        tenant_id=sample_tenant_id,
        email=sample_user.email,
        role=sample_user.role,
        slack_user_id=sample_user.slack_user_id,
        teams_user_id=sample_user.teams_user_id,
        telegram_user_id=sample_user.telegram_user_id,
        is_active=False,
        created_at=sample_user.created_at,
        updated_at=datetime.now(tz=UTC),
    )
    mock_service.update_user = AsyncMock(return_value=deactivated_user)

    payload = {"is_active": False}

    response = client.put(
        f"/tenants/{sample_tenant_id}/users/{sample_user.id}", json=payload
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False


# Group Management Tests


@pytest.fixture
def sample_group_id():
    """Create a sample group ID."""
    return uuid.uuid4()


@pytest.fixture
def sample_group(sample_tenant_id, sample_group_id):
    """Create a sample ReviewerGroup object."""
    return ReviewerGroup(
        id=sample_group_id,
        tenant_id=sample_tenant_id,
        name="Test Group",
        created_at=datetime.now(tz=UTC),
    )


@pytest.fixture
def sample_membership(sample_tenant_id, sample_group_id, sample_user_id):
    """Create a sample GroupMembership object."""
    return GroupMembership(
        id=uuid.uuid4(),
        tenant_id=sample_tenant_id,
        group_id=sample_group_id,
        user_id=sample_user_id,
        priority=0,
        is_active=True,
        created_at=datetime.now(tz=UTC),
    )


@patch("api.users.service")
def test_create_group(mock_service, client, sample_group, sample_tenant_id):
    """Test creating a new group without users."""
    mock_service.create_group_with_users = AsyncMock(return_value=sample_group)

    payload = {
        "name": "Test Group",
        "user_ids": [],
    }

    response = client.post(f"/tenants/{sample_tenant_id}/groups/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == str(sample_group.id)
    assert data["name"] == "Test Group"
    mock_service.create_group_with_users.assert_called_once()


@patch("api.users.service")
def test_create_group_with_users(
    mock_service, client, sample_group, sample_tenant_id, sample_user_id, sample_user
):
    """Test creating a group with initial users."""
    mock_service.get_user = AsyncMock(return_value=sample_user)
    mock_service.create_group_with_users = AsyncMock(return_value=sample_group)

    payload = {
        "name": "Test Group",
        "user_ids": [str(sample_user_id)],
    }

    response = client.post(f"/tenants/{sample_tenant_id}/groups/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Group"
    mock_service.get_user.assert_called_once()


@patch("api.users.service")
def test_create_group_user_not_found(
    mock_service, client, sample_tenant_id, sample_user_id
):
    """Test creating a group with a non-existent user."""
    mock_service.get_user = AsyncMock(side_effect=UserNotFoundError(sample_user_id))

    payload = {
        "name": "Test Group",
        "user_ids": [str(sample_user_id)],
    }

    response = client.post(f"/tenants/{sample_tenant_id}/groups/", json=payload)

    assert response.status_code == 404
    data = response.json()
    assert "User" in data["detail"] and "not found" in data["detail"]


@patch("api.users.service")
def test_create_group_already_exists(mock_service, client, sample_tenant_id):
    """Test creating a group that already exists."""
    mock_service.create_group_with_users = AsyncMock(
        side_effect=ReviewerGroupExistsError(
            "Group with name Test Group already exists"
        )
    )

    payload = {
        "name": "Test Group",
        "user_ids": [],
    }

    response = client.post(f"/tenants/{sample_tenant_id}/groups/", json=payload)

    assert response.status_code == 409
    data = response.json()
    assert "already exists" in data["detail"]


@patch("api.users.service")
def test_list_groups(mock_service, client, sample_group, sample_tenant_id):
    """Test listing all groups for a tenant."""
    mock_service.list_tenant_groups = AsyncMock(return_value=[sample_group])

    response = client.get(f"/tenants/{sample_tenant_id}/groups/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(sample_group.id)
    assert data[0]["name"] == "Test Group"


@patch("api.users.service")
def test_list_groups_empty(mock_service, client, sample_tenant_id):
    """Test listing groups when none exist."""
    mock_service.list_tenant_groups = AsyncMock(return_value=[])

    response = client.get(f"/tenants/{sample_tenant_id}/groups/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0


@patch("api.users.service")
def test_get_group(mock_service, client, sample_group, sample_tenant_id):
    """Test getting a specific group."""
    mock_service.get_group_by_id = AsyncMock(return_value=sample_group)

    response = client.get(f"/tenants/{sample_tenant_id}/groups/{sample_group.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_group.id)
    assert data["name"] == "Test Group"


@patch("api.users.service")
def test_get_group_not_found(mock_service, client, sample_tenant_id):
    """Test getting a non-existent group."""
    group_id = uuid.uuid4()
    mock_service.get_group_by_id = AsyncMock(
        side_effect=ReviewerGroupNotFoundError(group_id)
    )

    response = client.get(f"/tenants/{sample_tenant_id}/groups/{group_id}")

    assert response.status_code == 404
    data = response.json()
    assert "Group not found" in data["detail"]


@patch("api.users.service")
def test_delete_group(mock_service, client, sample_group, sample_tenant_id):
    """Test deleting a group."""
    mock_service.delete_group = AsyncMock(return_value=True)

    response = client.delete(f"/tenants/{sample_tenant_id}/groups/{sample_group.id}")

    assert response.status_code == 204
    mock_service.delete_group.assert_called_once()


@patch("api.users.service")
def test_delete_group_not_found(mock_service, client, sample_tenant_id):
    """Test deleting a non-existent group."""
    group_id = uuid.uuid4()
    mock_service.delete_group = AsyncMock(
        side_effect=ReviewerGroupNotFoundError(group_id)
    )

    response = client.delete(f"/tenants/{sample_tenant_id}/groups/{group_id}")

    assert response.status_code == 404
    data = response.json()
    assert "Group not found" in data["detail"]


@patch("api.users.service")
def test_add_user_to_group(
    mock_service, client, sample_group, sample_tenant_id, sample_membership, sample_user
):
    """Test adding a user to a group."""
    mock_service.get_group_by_id = AsyncMock(return_value=sample_group)
    mock_service.get_user = AsyncMock(return_value=sample_user)
    mock_service.add_user_to_group = AsyncMock(return_value=sample_membership)

    payload = {
        "user_id": str(sample_membership.user_id),
        "priority": 0,
    }

    response = client.post(
        f"/tenants/{sample_tenant_id}/groups/{sample_group.id}/members",
        json=payload,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["group_id"] == str(sample_group.id)
    assert data["user_id"] == str(sample_membership.user_id)
    mock_service.get_user.assert_called_once()


@patch("api.users.service")
def test_add_user_to_group_group_not_found(mock_service, client, sample_tenant_id):
    """Test adding a user to a non-existent group."""
    group_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_service.get_group_by_id = AsyncMock(
        side_effect=ReviewerGroupNotFoundError(group_id)
    )

    payload = {
        "user_id": str(user_id),
        "priority": 0,
    }

    response = client.post(
        f"/tenants/{sample_tenant_id}/groups/{group_id}/members",
        json=payload,
    )

    assert response.status_code == 404
    data = response.json()
    assert "Group not found" in data["detail"]


@patch("api.users.service")
def test_add_user_to_group_user_not_found(
    mock_service, client, sample_group, sample_tenant_id, sample_user_id
):
    """Test adding a non-existent user to a group."""
    mock_service.get_group_by_id = AsyncMock(return_value=sample_group)
    mock_service.get_user = AsyncMock(side_effect=UserNotFoundError(sample_user_id))

    payload = {
        "user_id": str(sample_user_id),
        "priority": 0,
    }

    response = client.post(
        f"/tenants/{sample_tenant_id}/groups/{sample_group.id}/members",
        json=payload,
    )

    assert response.status_code == 404
    data = response.json()
    assert "User" in data["detail"] and "not found" in data["detail"]


@patch("api.users.service")
def test_add_user_to_group_already_member(
    mock_service, client, sample_group, sample_tenant_id, sample_user_id, sample_user
):
    """Test adding a user to a group when they're already a member."""
    mock_service.get_group_by_id = AsyncMock(return_value=sample_group)
    mock_service.get_user = AsyncMock(return_value=sample_user)
    mock_service.add_user_to_group = AsyncMock(
        side_effect=UserAlreadyInGroupError(
            f"User {sample_user_id} is already a member of {sample_group.id} group"
        )
    )

    payload = {
        "user_id": str(sample_user_id),
        "priority": 0,
    }

    response = client.post(
        f"/tenants/{sample_tenant_id}/groups/{sample_group.id}/members",
        json=payload,
    )

    assert response.status_code == 409
    data = response.json()
    assert "already a member" in data["detail"]


@patch("api.users.service")
def test_remove_user_from_group(
    mock_service, client, sample_group, sample_tenant_id, sample_membership, sample_user
):
    """Test removing a user from a group."""
    mock_service.get_group_by_id = AsyncMock(return_value=sample_group)
    mock_service.get_user = AsyncMock(return_value=sample_user)
    mock_service.remove_user_from_group = AsyncMock(return_value=True)

    response = client.delete(
        f"/tenants/{sample_tenant_id}/groups/{sample_group.id}/members/{sample_membership.user_id}"
    )

    assert response.status_code == 204
    mock_service.get_user.assert_called_once()


@patch("api.users.service")
def test_remove_user_from_group_group_not_found(mock_service, client, sample_tenant_id):
    """Test removing a user from a non-existent group."""
    group_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_service.get_group_by_id = AsyncMock(
        side_effect=ReviewerGroupNotFoundError(group_id)
    )

    response = client.delete(
        f"/tenants/{sample_tenant_id}/groups/{group_id}/members/{user_id}"
    )

    assert response.status_code == 404
    data = response.json()
    assert "Group not found" in data["detail"]


@patch("api.users.service")
def test_remove_user_from_group_user_not_found(
    mock_service, client, sample_group, sample_tenant_id, sample_user_id
):
    """Test removing a non-existent user from a group."""
    mock_service.get_group_by_id = AsyncMock(return_value=sample_group)
    mock_service.get_user = AsyncMock(side_effect=UserNotFoundError(sample_user_id))

    response = client.delete(
        f"/tenants/{sample_tenant_id}/groups/{sample_group.id}/members/{sample_user_id}"
    )

    assert response.status_code == 404
    data = response.json()
    assert "User" in data["detail"] and "not found" in data["detail"]


@patch("api.users.service")
def test_list_group_members(
    mock_service, client, sample_group, sample_tenant_id, sample_membership
):
    """Test listing members of a group."""
    mock_service.get_group_by_id = AsyncMock(return_value=sample_group)
    mock_service.list_group_members = AsyncMock(return_value=[sample_membership])

    response = client.get(
        f"/tenants/{sample_tenant_id}/groups/{sample_group.id}/members"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["group_id"] == str(sample_group.id)
    assert data[0]["user_id"] == str(sample_membership.user_id)


@patch("api.users.service")
def test_list_group_members_empty(mock_service, client, sample_group, sample_tenant_id):
    """Test listing members when group has no members."""
    mock_service.get_group_by_id = AsyncMock(return_value=sample_group)
    mock_service.list_group_members = AsyncMock(return_value=[])

    response = client.get(
        f"/tenants/{sample_tenant_id}/groups/{sample_group.id}/members"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0


@patch("api.users.service")
def test_list_group_members_not_found(mock_service, client, sample_tenant_id):
    """Test listing members of a non-existent group."""
    group_id = uuid.uuid4()
    mock_service.get_group_by_id = AsyncMock(
        side_effect=ReviewerGroupNotFoundError(group_id)
    )

    response = client.get(f"/tenants/{sample_tenant_id}/groups/{group_id}/members")

    assert response.status_code == 404
    data = response.json()
    assert "Group not found" in data["detail"]


@patch("api.users.service")
def test_get_user_groups(
    mock_service, client, sample_user, sample_tenant_id, sample_group
):
    """Test getting all groups a user belongs to."""
    mock_service.get_user = AsyncMock(return_value=sample_user)
    mock_service.get_user_groups = AsyncMock(return_value=[sample_group])

    response = client.get(f"/tenants/{sample_tenant_id}/users/{sample_user.id}/groups")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(sample_group.id)
    assert data[0]["name"] == "Test Group"


@patch("api.users.service")
def test_get_user_groups_empty(mock_service, client, sample_user, sample_tenant_id):
    """Test getting groups when user is not in any groups."""
    mock_service.get_user = AsyncMock(return_value=sample_user)
    mock_service.get_user_groups = AsyncMock(return_value=[])

    response = client.get(f"/tenants/{sample_tenant_id}/users/{sample_user.id}/groups")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0


@patch("api.users.service")
def test_get_user_groups_not_found(mock_service, client, sample_tenant_id):
    """Test getting groups for a non-existent user."""
    user_id = uuid.uuid4()
    mock_service.get_user = AsyncMock(side_effect=UserNotFoundError(user_id))

    response = client.get(f"/tenants/{sample_tenant_id}/users/{user_id}/groups")

    assert response.status_code == 404
    data = response.json()
    assert "User not found" in data["detail"]
