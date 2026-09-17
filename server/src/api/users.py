# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.schema.schemas import (
    GroupCreate,
    GroupMembershipCreate,
    GroupMembershipResponse,
    GroupResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from db import get_session
from service.exceptions import (
    ReviewerGroupNotFoundError,
    UserNotFoundError,
)
from service.users_service import UsersService

_ERROR_RESPONSE = {
    "description": "Error response",
    "content": {
        "application/json": {
            "schema": {"type": "object", "properties": {"detail": {"type": "string"}}}
        }
    },
}

router = APIRouter(prefix="/tenants/{tenant_id}/users", tags=["Users"])
service = UsersService()


@router.post(
    "/",
    response_model=UserResponse,
    responses={
        201: {"description": "User created successfully"},
    },
    status_code=201,
)
async def create_user(
    tenant_id: uuid.UUID,
    user: UserCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> UserResponse:
    """Create a new user for a tenant.

    Returns 201 with the created User object."""
    created_user = await service.create_user(
        session=session,
        tenant_id=tenant_id,
        email=user.email,
        role=user.role,
        slack_user_id=user.slack_user_id,
        teams_user_id=user.teams_user_id,
        telegram_user_id=user.telegram_user_id,
    )
    return UserResponse.model_validate(created_user, from_attributes=True)


@router.get(
    "/",
    response_model=list[UserResponse],
    responses={
        200: {"description": "List of all users for a tenant"},
    },
)
async def list_users(
    tenant_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> list[UserResponse]:
    """List all users for a specific tenant.

    Returns 200 with a list of User objects for the tenant."""
    users = await service.list_users(session, tenant_id)
    return [UserResponse.model_validate(u, from_attributes=True) for u in users]


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    responses={
        200: {"description": "User retrieved successfully"},
        404: _ERROR_RESPONSE,
    },
)
async def get_user(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> UserResponse:
    """Get a specific user by ID for a tenant.

    Returns 200 with the User object or 404 if not found."""
    try:
        user = await service.get_user(session, tenant_id, user_id)
        return UserResponse.model_validate(user, from_attributes=True)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    responses={
        200: {"description": "User updated successfully"},
        404: _ERROR_RESPONSE,
    },
)
async def update_user(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    user_update: UserUpdate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> UserResponse:
    """Update a user for a tenant.

    Returns 200 with the updated User object or 404 if not found."""
    try:
        update_data = user_update.model_dump(exclude_unset=True)
        updated_user = await service.update_user(
            session, tenant_id, user_id, **update_data
        )
        return UserResponse.model_validate(updated_user, from_attributes=True)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")


@router.delete(
    "/{user_id}",
    status_code=204,
    responses={
        204: {"description": "User deleted successfully"},
        404: _ERROR_RESPONSE,
    },
)
async def delete_user(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> None:
    """Delete a user for a tenant.

    Returns 204 if deleted or 404 if not found."""
    try:
        await service.delete_user(session, tenant_id, user_id)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")


# Group management endpoints
group_router = APIRouter(prefix="/tenants/{tenant_id}/groups", tags=["Groups"])


@group_router.post(
    "/",
    response_model=GroupResponse,
    responses={
        201: {"description": "Group created successfully"},
        404: _ERROR_RESPONSE,
    },
    status_code=201,
)
async def create_group(
    tenant_id: uuid.UUID,
    group: GroupCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> GroupResponse:
    """Create a new reviewer group with initial list of users.

    Returns 201 with the created Group object or 404 if any user is not found."""
    # Validate all users exist in the tenant
    for user_id in group.user_ids:
        try:
            await service.get_user(session, tenant_id, user_id)
        except UserNotFoundError:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    created_group = await service.create_group_with_users(
        session=session,
        tenant_id=tenant_id,
        name=group.name,
        user_ids=group.user_ids,
    )
    return GroupResponse.model_validate(created_group, from_attributes=True)


@group_router.get(
    "/",
    response_model=list[GroupResponse],
    responses={
        200: {"description": "List of all groups for a tenant"},
    },
)
async def list_groups(
    tenant_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> list[GroupResponse]:
    """List all reviewer groups for a tenant.

    Returns 200 with a list of Group objects for the tenant."""
    groups = await service.list_tenant_groups(session, tenant_id)
    return [GroupResponse.model_validate(g, from_attributes=True) for g in groups]


@group_router.get(
    "/{group_id}",
    response_model=GroupResponse,
    responses={
        200: {"description": "Group retrieved successfully"},
        404: _ERROR_RESPONSE,
    },
)
async def get_group(
    tenant_id: uuid.UUID,
    group_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> GroupResponse:
    """Get a specific group by ID for a tenant.

    Returns 200 with the Group object or 404 if not found."""
    try:
        group = await service.get_group_by_id(session, tenant_id, group_id)
        return GroupResponse.model_validate(group, from_attributes=True)
    except ReviewerGroupNotFoundError:
        raise HTTPException(status_code=404, detail="Group not found")


@group_router.delete(
    "/{group_id}",
    status_code=204,
    responses={
        204: {"description": "Group deleted successfully"},
        404: _ERROR_RESPONSE,
    },
)
async def delete_group(
    tenant_id: uuid.UUID,
    group_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> None:
    """Delete a group for a tenant.

    Returns 204 if deleted or 404 if not found."""
    try:
        await service.delete_group(session, tenant_id, group_id)
    except ReviewerGroupNotFoundError:
        raise HTTPException(status_code=404, detail="Group not found")


@group_router.post(
    "/{group_id}/members",
    response_model=GroupMembershipResponse,
    responses={
        201: {"description": "User added to group successfully"},
        404: _ERROR_RESPONSE,
    },
    status_code=201,
)
async def add_user_to_group(
    tenant_id: uuid.UUID,
    group_id: uuid.UUID,
    membership: GroupMembershipCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> GroupMembershipResponse:
    """Add a user to a group.

    Returns 201 with the GroupMembership object or 404 if group or user not found."""
    try:
        await service.get_group_by_id(session, tenant_id, group_id)
        await service.get_user(session, tenant_id, membership.user_id)
        created_membership = await service.add_user_to_group(
            session=session,
            tenant_id=tenant_id,
            group_id=group_id,
            user_id=membership.user_id,
            priority=membership.priority,
        )
        return GroupMembershipResponse.model_validate(
            created_membership, from_attributes=True
        )
    except ReviewerGroupNotFoundError:
        raise HTTPException(status_code=404, detail="Group not found")
    except UserNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"User {membership.user_id} not found"
        )


@group_router.delete(
    "/{group_id}/members/{user_id}",
    status_code=204,
    responses={
        204: {"description": "User removed from group successfully"},
        404: _ERROR_RESPONSE,
    },
)
async def remove_user_from_group(
    tenant_id: uuid.UUID,
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> None:
    """Remove a user from a group.

    Returns 204 if removed or 404 if group or user not found."""
    try:
        await service.get_group_by_id(session, tenant_id, group_id)
        await service.get_user(session, tenant_id, user_id)
        await service.remove_user_from_group(
            session=session,
            tenant_id=tenant_id,
            group_id=group_id,
            user_id=user_id,
        )
    except ReviewerGroupNotFoundError:
        raise HTTPException(status_code=404, detail="Group not found")
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")


@group_router.get(
    "/{group_id}/members",
    response_model=list[GroupMembershipResponse],
    responses={
        200: {"description": "List of all members in the group"},
        404: _ERROR_RESPONSE,
    },
)
async def list_group_members(
    tenant_id: uuid.UUID,
    group_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> list[GroupMembershipResponse]:
    """List all users in a group.

    Returns 200 with a list of GroupMembership objects or 404 if group not found."""
    try:
        await service.get_group_by_id(session, tenant_id, group_id)
        members = await service.list_group_members(session, tenant_id, group_id)
        return [
            GroupMembershipResponse.model_validate(m, from_attributes=True)
            for m in members
        ]
    except ReviewerGroupNotFoundError:
        raise HTTPException(status_code=404, detail="Group not found")


@router.get(
    "/{user_id}/groups",
    response_model=list[GroupResponse],
    responses={
        200: {"description": "List of all groups the user belongs to"},
        404: _ERROR_RESPONSE,
    },
)
async def get_user_groups(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> list[GroupResponse]:
    """Get all groups a user is a member of.

    Returns 200 with a list of Group objects or 404 if user not found."""
    try:
        await service.get_user(session, tenant_id, user_id)
        groups = await service.get_user_groups(session, tenant_id, user_id)
        return [GroupResponse.model_validate(g, from_attributes=True) for g in groups]
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
